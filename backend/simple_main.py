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
import openai
import google.generativeai as genai

# Load environment variables
load_dotenv()

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

# Initialize API clients
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

if OPENAI_API_KEY:
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
    setup_ffmpeg()
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
    """Transcribe audio using OpenAI Whisper API"""
    if not OPENAI_API_KEY:
        # Fallback: return a message indicating API key needed
        return "⚠️ OpenAI API key not configured for transcription. Please add OPENAI_API_KEY to your environment variables.", {
            "language": "en",
            "language_probability": 0.99,
            "duration": 120,
        }
    
    try:
        # Create OpenAI client
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        with open(audio_file, "rb") as audio:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio,
                response_format="text"
            )
        
        # Get file duration (approximate)
        file_size = os.path.getsize(audio_file)
        estimated_duration = file_size / (32 * 1024)  # Rough estimate based on bitrate
        
        return transcript, {
            "language": "auto-detected",
            "language_probability": 0.95,
            "duration": estimated_duration,
        }
        
    except Exception as e:
        print(f"Transcription error: {e}")
        return f"⚠️ Transcription failed: {str(e)}", {
            "language": "unknown",
            "language_probability": 0.0,
            "duration": 0,
        }

def summarize_text(text: str, api_key: Optional[str] = None) -> str:
    """Summarize text using Google Gemini"""
    if not text.strip():
        return "⚠️ No transcript text available to summarize."
    
    # Use provided API key or fallback to environment variable
    effective_key = api_key or GEMINI_API_KEY
    if not effective_key:
        return "⚠️ Gemini API key not configured for summarization. Please add GEMINI_API_KEY to your environment variables or provide it in the request."
    
    try:
        # Configure with the provided API key
        genai.configure(api_key=effective_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        
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