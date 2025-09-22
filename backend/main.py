import os
import warnings
import tempfile
import shutil
from typing import Dict, List, Any, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Suppress ctranslate2 pkg_resources deprecation warning during import
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API",
    category=UserWarning,
    module="ctranslate2.*"
)

# Also suppress all pkg_resources warnings to be safe
warnings.filterwarnings(
    "ignore",
    message=".*pkg_resources.*",
    category=UserWarning
)

from faster_whisper import WhisperModel
import yt_dlp
import google.generativeai as genai

# Initialize FastAPI app
app = FastAPI(title="YouTube Video Summarizer API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite and CRA default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
whisper_model = None
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini if API key is available
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

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
    segments: List[Dict[str, Any]]

# Load Whisper model on startup
@app.on_event("startup")
async def load_whisper_model():
    global whisper_model
    print("Loading Whisper model...")
    whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    print("Whisper model loaded successfully!")

def download_audio(youtube_url: str) -> str:
    """Download audio from YouTube using yt-dlp"""
    temp_dir = tempfile.mkdtemp()
    
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio',
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'extractaudio': False,
        'writethumbnail': False,
        'writeinfojson': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            if not info:
                raise RuntimeError("Could not extract video information")
                
            duration = info.get('duration', 0)
            if duration and duration > 3600:
                print(f"Video is {duration//60} minutes long. This may take a while to process.")
            
            ydl.download([youtube_url])
            
            files = os.listdir(temp_dir)
            audio_files = [f for f in files if f.endswith(('.mp3', '.m4a', '.webm', '.opus', '.aac', '.ogg'))]
            
            if audio_files:
                downloaded_file = os.path.join(temp_dir, audio_files[0])
                if os.path.exists(downloaded_file) and os.path.getsize(downloaded_file) > 0:
                    return downloaded_file
                    
            raise RuntimeError("Audio file download failed or file is empty.")
            
    except yt_dlp.DownloadError as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError(f"YouTube download failed: {str(e)}")
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError(f"Failed to download audio: {str(e)}")

def maybe_convert_to_wav(input_path: str) -> str:
    """Convert to wav if needed"""
    ext = os.path.splitext(input_path)[1].lower()
    if ext in {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".webm"}:
        return input_path
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return input_path
    output_path = os.path.splitext(input_path)[0] + ".wav"
    os.system(f'"{ffmpeg}" -y -i "{input_path}" -ac 1 -ar 16000 "{output_path}" > NUL 2>&1')
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        return output_path
    return input_path

def transcribe_audio(audio_file: str):
    """Transcribe audio using faster-whisper"""
    global whisper_model
    if not whisper_model:
        raise RuntimeError("Whisper model not loaded")
    
    audio_for_model = maybe_convert_to_wav(audio_file)
    segments, info = whisper_model.transcribe(audio_for_model)

    segment_rows = []
    parts = []
    for seg in segments:
        parts.append(seg.text)
        segment_rows.append({
            "start": getattr(seg, "start", None),
            "end": getattr(seg, "end", None),
            "text": seg.text,
        })

    transcript = " ".join(parts).strip()

    meta = {
        "language": getattr(info, "language", None),
        "language_probability": getattr(info, "language_probability", None),
        "duration": getattr(info, "duration", None),
    }

    return transcript, segment_rows, meta

def summarize_text(text: str, api_key: Optional[str] = None, model_name: str = "gemini-1.5-flash") -> str:
    """Summarize text using Google Gemini"""
    if not text.strip():
        return "⚠️ No transcript text available to summarize."
    
    effective_key = api_key or GEMINI_API_KEY
    if not effective_key:
        return "⚠️ Gemini API key not configured."
    
    try:
        # Configure with the provided API key
        genai.configure(api_key=effective_key)
        model = genai.GenerativeModel(model_name)
        
        prompt = f"""You are a helpful assistant that summarizes YouTube transcripts. 
        Please provide a clear, concise summary of the following transcript:

        {text}

        Please organize your summary with:
        1. Main topic/subject
        2. Key points discussed
        3. Important insights or conclusions

        Summary:"""
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=500,
                temperature=0.5,
            )
        )
        
        return response.text.strip()
        
    except Exception as e:
        return f"⚠️ Error generating summary with Gemini: {str(e)}"

# API Routes
@app.get("/")
async def root():
    return {"message": "YouTube Video Summarizer API", "status": "running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "whisper_model_loaded": whisper_model is not None,
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
            transcript, segments, meta = transcribe_audio(audio_path)
            
            # Summarize transcript
            summary = summarize_text(transcript, request.gemini_api_key)
            
            # Clean up audio file
            if audio_path and os.path.exists(audio_path):
                temp_dir = os.path.dirname(audio_path)
                shutil.rmtree(temp_dir, ignore_errors=True)
            
            return TranscriptResponse(
                transcript=transcript,
                summary=summary,
                metadata=meta,
                segments=segments
            )
            
        except Exception as e:
            # Clean up on error
            if audio_path and os.path.exists(audio_path):
                temp_dir = os.path.dirname(audio_path)
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise e
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/download/transcript")
async def download_transcript(data: dict):
    """Download transcript as a text file"""
    transcript = data.get("transcript", "")
    if not transcript:
        raise HTTPException(status_code=400, detail="No transcript provided")
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
    temp_file.write(transcript)
    temp_file.close()
    
    return FileResponse(
        temp_file.name,
        media_type='text/plain',
        filename='transcript.txt',
        background=BackgroundTasks()
    )

@app.post("/download/summary")
async def download_summary(data: dict):
    """Download summary as a text file"""
    summary = data.get("summary", "")
    if not summary:
        raise HTTPException(status_code=400, detail="No summary provided")
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
    temp_file.write(summary)
    temp_file.close()
    
    return FileResponse(
        temp_file.name,
        media_type='text/plain',
        filename='summary.txt',
        background=BackgroundTasks()
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)