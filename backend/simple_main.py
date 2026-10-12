#!/usr/bin/env python3
"""YouTube video summarizer API.

Pipeline:
YouTube URL -> yt-dlp -> local faster-whisper -> Gemini
"""

import os
import shutil
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, List, Optional

import yt_dlp
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from faster_whisper import WhisperModel
from google import genai
from google.genai import types


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR.parent / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "base")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

whisper_model: WhisperModel | None = None


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class YouTubeRequest(BaseModel):
    url: HttpUrl


class TranscriptResponse(BaseModel):
    transcript: str
    summary: str
    metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# FFmpeg
# ---------------------------------------------------------------------------

def setup_ffmpeg() -> None:
    """Find FFmpeg and add its directory to PATH if necessary."""
    if shutil.which("ffmpeg"):
        print("FFmpeg is already available in PATH.")
        return

    local_app_data = os.getenv("LOCALAPPDATA")
    candidates: list[Path] = []

    if local_app_data:
        winget_dir = (
            Path(local_app_data)
            / "Microsoft"
            / "WinGet"
            / "Packages"
        )
        if winget_dir.exists():
            candidates.extend(winget_dir.glob("**/bin/ffmpeg.exe"))

    project_root = BACKEND_DIR.parent
    candidates.extend(
        [
            project_root / "ffmpeg" / "bin" / "ffmpeg.exe",
            project_root / "ffmpeg" / "ffmpeg.exe",
        ]
    )

    ffmpeg_exe = next((path for path in candidates if path.is_file()), None)

    if ffmpeg_exe:
        os.environ["PATH"] = (
            str(ffmpeg_exe.parent)
            + os.pathsep
            + os.environ.get("PATH", "")
        )
        print(f"Found FFmpeg at {ffmpeg_exe}")
    else:
        print("Warning: FFmpeg was not found.")


# ---------------------------------------------------------------------------
# Application startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global whisper_model

    setup_ffmpeg()

    if not GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY is not configured.")

    try:
        whisper_model = WhisperModel(
            WHISPER_MODEL_NAME,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
        print(
            f"Loaded faster-whisper model: "
            f"{WHISPER_MODEL_NAME} ({WHISPER_DEVICE}/{WHISPER_COMPUTE_TYPE})"
        )
    except Exception as exc:
        whisper_model = None
        print(f"Could not load faster-whisper: {exc}")

    print("Backend server started!")
    yield


app = FastAPI(
    title="YouTube Video Summarizer API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# YouTube download
# ---------------------------------------------------------------------------

def download_audio(youtube_url: str) -> tuple[str, str]:
    """Download the best available YouTube audio stream."""
    temp_dir = tempfile.mkdtemp(prefix="yt_summarizer_")

    options = {
        "format": "bestaudio/best",
        "outtmpl": str(Path(temp_dir) / "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
    }

    try:
        print(f"Downloading audio from: {youtube_url}")

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(youtube_url, download=True)

        if not info:
            raise RuntimeError("yt-dlp could not extract video information.")

        audio_files = [
            path
            for path in Path(temp_dir).iterdir()
            if path.is_file()
            and path.suffix.lower() in {".m4a", ".webm", ".opus", ".mp3", ".aac"}
            and path.stat().st_size > 0
        ]

        if not audio_files:
            raise RuntimeError("yt-dlp did not produce an audio file.")

        audio_path = audio_files[0]
        print(f"Successfully downloaded: {audio_path}")

        title = info.get("title") or "YouTube video"
        return str(audio_path), title

    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

def transcribe_audio(audio_file: str) -> tuple[str, dict[str, Any]]:
    """Transcribe downloaded audio using local faster-whisper."""
    if whisper_model is None:
        raise RuntimeError(
            "faster-whisper is not available. "
            "Check the backend startup log."
        )

    print("Transcribing audio with faster-whisper...")

    segments, info = whisper_model.transcribe(
        audio_file,
        vad_filter=True,
    )

    transcript = " ".join(
        segment.text.strip()
        for segment in segments
        if segment.text.strip()
    ).strip()

    if not transcript:
        raise RuntimeError("Whisper returned an empty transcript.")

    metadata = {
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
    }

    print("Transcription completed.")
    return transcript, metadata


# ---------------------------------------------------------------------------
# Gemini summarization
# ---------------------------------------------------------------------------

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
    model_name: str = GEMINI_MODEL,
    max_output_tokens: int = 500,
    temperature: float = 0.5,
    api_key: Optional[str] = None,
) -> tuple[Optional[str], Optional[Exception]]:
    """Generate content using Gemini with retries for temporary failures."""
    client = genai.Client(api_key=api_key or GEMINI_API_KEY)
    max_attempts = 3
    last_error: Optional[Exception] = None

    for attempt in range(max_attempts):
        try:
            print(
                f"Using Gemini model: {model_name} "
                f"(attempt {attempt + 1}/{max_attempts})"
            )

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=max_output_tokens,
                    temperature=temperature,
                ),
            )

            result_text = getattr(response, "text", None)
            if result_text and result_text.strip():
                return result_text.strip(), None

            last_error = Exception("Gemini returned an empty response")

        except Exception as error:
            last_error = error
            error_text = str(error).upper()
            is_temporary = any(
                marker in error_text
                for marker in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")
            )

            print(f"Gemini model failed: {model_name} -> {error}")

            if not is_temporary:
                return None, error

        if attempt < max_attempts - 1:
            delay = 2 ** (attempt + 1)
            print(f"Retrying Gemini in {delay} seconds...")
            time.sleep(delay)

    return None, last_error or Exception(
        "Gemini failed after all retry attempts"
    )

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
                max_output_tokens=1200,
                temperature=0.4,
                api_key=effective_key,
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
                    max_output_tokens=800,
                    temperature=0.4,
                    api_key=effective_key,
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
            max_output_tokens=1200,
            temperature=0.4,
            api_key=effective_key,
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


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "YouTube Video Summarizer API",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "whisper_loaded": whisper_model is not None,
        "gemini_configured": bool(GEMINI_API_KEY),
        "gemini_model": GEMINI_MODEL,
    }


@app.post("/process", response_model=TranscriptResponse)
def process_youtube_video(request: YouTubeRequest):
    """Download, transcribe, summarize, and clean up a YouTube video."""
    audio_path: str | None = None

    try:
        audio_path, title = download_audio(str(request.url))
        transcript, metadata = transcribe_audio(audio_path)
        summary = summarize_text(transcript)

        metadata["title"] = title
        metadata["url"] = str(request.url)

        return TranscriptResponse(
            transcript=transcript,
            summary=summary,
            metadata=metadata,
        )

    except Exception as exc:
        message = str(exc)
        print(f"Processing failed: {message}")
        raise HTTPException(status_code=500, detail=message) from exc

    finally:
        if audio_path:
            temp_dir = Path(audio_path).parent
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "simple_main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )