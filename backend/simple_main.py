#!/usr/bin/env python3
"""
Simplified YouTube Video Summarizer API
"""
import os
import tempfile
import shutil
from typing import Dict, List, Any, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv
import yt_dlp
import google.generativeai as genai

try:
    import openai
except Exception:
    openai = None

try:
    from faster_whisper import WhisperModel
except Exception:
    WhisperModel = None

# Load environment variables
backend_dir = Path(__file__).resolve().parent
load_dotenv(backend_dir / ".env")
load_dotenv(backend_dir.parent / ".env")

# Initialize FastAPI app
app = FastAPI(title="YouTube Video Summarizer API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
whisper_model = None

# Initialize API clients
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

if OPENAI_API_KEY and openai:
    openai.api_key = OPENAI_API_KEY

def setup_ffmpeg():
    """Ensure ffmpeg is available in the path"""
    ffmpeg_dir = Path(__file__).parent.parent / "ffmpeg"
    ffmpeg_exe = ffmpeg_dir / "ffmpeg.exe"

    if ffmpeg_exe.exists():
        print("Found ffmpeg.exe, adding to PATH.")
        os.environ["PATH"] = str(ffmpeg_dir) + os.pathsep + os.environ["PATH"]
    else:
        print("ffmpeg.exe not found in the ffmpeg directory.")
        # Check if it's in the system path already
        if not shutil.which("ffmpeg"):
            print("⚠️ ffmpeg is not in the system PATH. Audio conversion may fail.")

# Pydantic models
class YouTubeRequest(BaseModel):
    url: HttpUrl
    gemini_api_key: Optional[str] = None

class ProcessingResponse(BaseModel):
    message: str
    status: str

class TranscriptResponse(BaseModel):
    transcript: str
    summary: str
    metadata: Dict[str, Any]

# Load dependencies on startup
@app.on_event("startup")
async def startup_event():
    """Setup dependencies on startup"""
    global whisper_model
    setup_ffmpeg()

    # Gemini-only mode: use local faster-whisper for transcription if no OpenAI key.
    if not OPENAI_API_KEY:
        if WhisperModel is not None:
            try:
                whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
                print("Loaded local faster-whisper model (base).")
            except Exception as e:
                whisper_model = None
                print(f"Could not load local faster-whisper model: {e}")
        else:
            print("faster-whisper is not installed; transcription requires OPENAI_API_KEY.")

    print("Simple backend server started!")

def download_audio(youtube_url: str) -> str:
    """Download audio from YouTube using yt-dlp"""
    temp_dir = tempfile.mkdtemp()
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        print(f"Downloading audio from: {youtube_url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            if not info:
                raise RuntimeError("Could not extract video info")
                
            ydl.download([youtube_url])
            
            files = os.listdir(temp_dir)
            audio_files = [f for f in files if f.endswith(('.mp3', '.m4a', '.webm', '.opus', '.aac'))]
            
            if audio_files:
                downloaded_file = os.path.join(temp_dir, audio_files[0])
                if os.path.exists(downloaded_file) and os.path.getsize(downloaded_file) > 0:
                    print(f"Successfully downloaded: {downloaded_file}")
                    return downloaded_file
                    
        raise RuntimeError("No valid audio file downloaded")
                        
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError(f"Download failed: {str(e)}")

def transcribe_audio(audio_file: str):
    """Transcribe audio using OpenAI Whisper API or local faster-whisper fallback."""
    if OPENAI_API_KEY and openai:
        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)

            with open(audio_file, "rb") as audio:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio,
                    response_format="text"
                )

            file_size = os.path.getsize(audio_file)
            estimated_duration = file_size / (32 * 1024)

            return transcript, {
                "language": "auto-detected",
                "language_probability": 0.95,
                "duration": estimated_duration,
            }

        except Exception as e:
            print(f"OpenAI transcription error: {e}")

    if whisper_model is not None:
        try:
            segments, info = whisper_model.transcribe(audio_file)
            transcript = " ".join(seg.text for seg in segments).strip()
            return transcript, {
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
            }
        except Exception as e:
            print(f"Local transcription error: {e}")

    return "⚠️ No transcription engine available. Install faster-whisper or set OPENAI_API_KEY.", {
        "language": "unknown",
        "language_probability": 0.0,
        "duration": 0,
    }

def split_text_into_chunks(text: str, max_chars: int = 9000, overlap: int = 400) -> List[str]:
    """Split text into overlapping chunks to keep context while avoiding model limits."""
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return [normalized]

    chunks: List[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + max_chars, len(normalized))
        chunk = normalized[start:end]
        chunks.append(chunk)
        if end >= len(normalized):
            break
        start = max(end - overlap, 0)
    return chunks

def generate_with_gemini(
    prompt: str,
    models_to_try: List[str],
    max_output_tokens: int = 500,
    temperature: float = 0.5,
) -> tuple[Optional[str], Optional[Exception]]:
    """Try prompt generation across multiple Gemini models and return first success."""
    last_error = None
    for model_name in models_to_try:
        try:
            print(f"Trying Gemini model: {model_name}")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_output_tokens,
                    temperature=temperature,
                )
            )
            if response and getattr(response, "text", None):
                result_text = response.text.strip()
                if result_text:
                    return result_text, None
            last_error = Exception("Gemini returned an empty response")
        except Exception as e:
            last_error = e
            print(f"Gemini model failed: {model_name} -> {e}")
            continue

    return None, last_error

def _is_valid_chunk_summary(summary: str, chunk_index: int) -> bool:
    """Check if a chunk summary contains meaningful content (not just prompt echoes)."""
    if not summary or len(summary.strip()) < 30:
        return False
    lower = summary.lower()
    # Detect responses that just echo the prompt instructions back
    bad_patterns = [
        f"summary of the transcript chunk: {chunk_index}",
        f"summary of the transcript chunk:{chunk_index}",
        "here's a concise summary of the transcript chunk",
        "i need the actual content",
        "please provide the",
        "the transcript chunk is missing",
        "no content was provided",
        "the partial summaries themselves are missing",
    ]
    return not any(pattern in lower for pattern in bad_patterns)

def summarize_text(text: str, api_key: Optional[str] = None) -> str:
    """Summarize text using Google Gemini"""
    if not text.strip():
        return "⚠️ No transcript text available to summarize."
    
    # Use provided API key or fallback to environment variable
    effective_key = api_key or GEMINI_API_KEY
    if not effective_key:
        return "⚠️ Gemini API key not configured for summarization. Please add GEMINI_API_KEY to your environment variables or provide it in the request."
    
    try:
        # Configure with the provided API key.
        genai.configure(api_key=effective_key)

        # Try multiple current Gemini model names and attempt generation on each.
        models_to_try = [
            "gemini-2.0-flash",
            "gemini-2.5-flash",
            "gemini-2.0-flash-lite",
            "gemini-2.5-flash-lite",
            "gemini-flash-latest",
        ]

        chunks = split_text_into_chunks(text)
        print(f"📊 Transcript split into {len(chunks)} chunk(s), total length: {len(text)} chars")
        partial_summaries: List[str] = []

        # If the transcript is short enough for a single chunk, summarize directly
        if len(chunks) == 1:
            direct_prompt = f"""You are an expert assistant who creates concise, easy-to-read summaries of video transcripts.
Based on the following transcript, please provide a summary that includes:
1. **Main Topic:** A brief, one-sentence description of the video's central theme.
2. **Key Points:** A bulleted list of the most important ideas, arguments, or steps discussed.
3. **Conclusion:** A short summary of the final conclusion or takeaway message.

Transcript:
---
{chunks[0]}
---

Summary:"""
            direct_summary, direct_error = generate_with_gemini(
                prompt=direct_prompt,
                models_to_try=models_to_try,
                max_output_tokens=1200,
                temperature=0.4,
            )
            if direct_summary:
                return direct_summary
            err_text = str(direct_error) if direct_error else "Unknown Gemini API error"
            return f"⚠️ Error generating summary with Gemini: {err_text}"

        # Multi-chunk summarization with validation and retry
        MAX_RETRIES = 2
        for index, chunk in enumerate(chunks, start=1):
            print(f"📝 Summarizing chunk {index}/{len(chunks)} ({len(chunk)} chars)...")
            chunk_prompt = f"""Summarize the following section (part {index} of {len(chunks)}) of a video transcript.
Provide concise but substantive notes covering:
1. Main ideas discussed in this section
2. Important details, examples, or data mentioned
3. Any conclusions or action items

IMPORTANT: Your response must be a summary of the actual transcript content below. Do NOT ask for more information.

Transcript section:
---
{chunk}
---

Summary of this section:"""

            # Try generating with retries for bad responses
            chunk_summary = None
            chunk_error = None
            for attempt in range(MAX_RETRIES):
                chunk_summary, chunk_error = generate_with_gemini(
                    prompt=chunk_prompt,
                    models_to_try=models_to_try,
                    max_output_tokens=800,
                    temperature=0.4,
                )

                if chunk_summary and _is_valid_chunk_summary(chunk_summary, index):
                    break
                elif chunk_summary:
                    print(f"⚠️ Chunk {index} attempt {attempt + 1}: got invalid/echo response, retrying...")
                    chunk_summary = None  # Reset so we retry

            if chunk_summary:
                partial_summaries.append(f"Chunk {index}:\n{chunk_summary}")
                print(f"✅ Chunk {index} summarized successfully ({len(chunk_summary)} chars)")
                continue

            err_text = str(chunk_error) if chunk_error else "Unknown Gemini API error"
            if "429" in err_text or "quota" in err_text.lower():
                return (
                    "⚠️ Gemini quota exceeded while building a full summary. "
                    "Wait for quota reset, enable billing, or use a different Gemini project/key."
                )
            return f"⚠️ Error generating summary with Gemini: {err_text}"

        print(f"🔗 Merging {len(partial_summaries)} partial summaries into final summary...")
        merged_partials = "\n\n".join(partial_summaries)
        merge_prompt = f"""You are given partial summaries of different sections of a full video transcript.
Combine them into one complete, well-organized final summary with:
1. **Main Topic:** A brief, one-sentence description of the video's central theme.
2. **Key Points:** A bulleted list of the most important ideas, arguments, or steps discussed.
3. **Important Insights or Conclusions:** Key takeaways from the video.

Partial summaries:
---
{merged_partials}
---

Final summary:"""

        final_summary, final_error = generate_with_gemini(
            prompt=merge_prompt,
            models_to_try=models_to_try,
            max_output_tokens=1200,
            temperature=0.4,
        )

        if final_summary:
            return final_summary

        err_text = str(final_error) if final_error else "Unknown Gemini API error"
        if "429" in err_text or "quota" in err_text.lower():
            return (
                "⚠️ Gemini quota exceeded while generating final summary. "
                "Wait for quota reset, enable billing, or use a different Gemini project/key."
            )

        return f"⚠️ Error generating summary with Gemini: {err_text}"

    except Exception as e:
        return f"⚠️ Error generating summary with Gemini: {str(e)}"

# API Routes
@app.get("/")
async def root():
    return {"message": "YouTube Video Summarizer API (Simple Mode)", "status": "running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "mode": "simple",
        "gemini_api_configured": GEMINI_API_KEY is not None
    }

@app.post("/process", response_model=TranscriptResponse)
async def process_youtube_video(request: YouTubeRequest):
    """Process a YouTube video: download, transcribe, and summarize"""
    try:
        # Download audio
        audio_path = download_audio(str(request.url))
        
        try:
            # Transcribe audio
            transcript, meta = transcribe_audio(audio_path)
            
            # Summarize transcript
            summary = summarize_text(transcript, request.gemini_api_key)
            
            # Clean up audio file
            if audio_path and os.path.exists(audio_path):
                temp_dir = os.path.dirname(audio_path)
                shutil.rmtree(temp_dir, ignore_errors=True)
            
            return TranscriptResponse(
                transcript=transcript,
                summary=summary,
                metadata=meta
            )
            
        except Exception as e:
            # Clean up on error
            if audio_path and os.path.exists(audio_path):
                temp_dir = os.path.dirname(audio_path)
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise e
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)