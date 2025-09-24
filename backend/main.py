import os
import warnings
import tempfile
import shutil
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Suppress unnecessary warnings from imported libraries
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API",
    category=UserWarning
)

from faster_whisper import WhisperModel
import yt_dlp
import google.generativeai as genai

# --- App Initialization ---
app = FastAPI(title="YouTube Video Summarizer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global Variables & Setup ---
whisper_model = None
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def setup_ffmpeg():
    """Ensure ffmpeg is available to the application."""
    ffmpeg_dir = Path(__file__).parent / "ffmpeg"
    if ffmpeg_dir.exists() and (ffmpeg_dir / "ffmpeg.exe").exists():
        print("✅ Found local ffmpeg, adding to PATH.")
        os.environ["PATH"] = str(ffmpeg_dir) + os.pathsep + os.environ["PATH"]
    elif not shutil.which("ffmpeg"):
        print("⚠️ ffmpeg not found in the system PATH or in a local 'ffmpeg' folder.")
        print("   Please download ffmpeg and place it in a folder named 'ffmpeg' next to your script.")

@app.on_event("startup")
async def startup_event():
    """Load models and setup dependencies when the server starts."""
    global whisper_model
    setup_ffmpeg()
    print("🚀 Loading Whisper model...")
    # Using "base" model for speed. For higher accuracy, consider "small" or "medium".
    whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    print("✅ Whisper model loaded successfully!")

# --- Pydantic Models ---
class YouTubeRequest(BaseModel):
    url: HttpUrl
    gemini_api_key: Optional[str] = None

class TranscriptResponse(BaseModel):
    transcript: str
    summary: str
    metadata: Dict[str, Any]

# --- Core Logic Functions ---
def download_audio(youtube_url: str) -> str:
    """Download audio from YouTube using a reliable cookie file strategy."""
    temp_dir = tempfile.mkdtemp()
    cookie_file = "youtube-cookies.txt"

    # CRITICAL: Check if the cookie file exists before proceeding.
    if not os.path.exists(cookie_file):
        shutil.rmtree(temp_dir)  # Clean up the created temp directory
        raise RuntimeError(
            f"Cookie file not found at '{cookie_file}'. "
            "Please export it from your browser and place it in the project directory."
        )

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'cookies': cookie_file,  # <-- This is the key fix for authentication issues.
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': False,
    }

    print(f"⬇️ Attempting to download audio from {youtube_url}...")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])

        # Find the single downloaded audio file
        files = os.listdir(temp_dir)
        audio_files = [f for f in files if f.endswith(('.mp3', '.m4a', '.webm', '.opus', '.wav'))]

        if not audio_files:
            raise RuntimeError("Download finished, but no audio file was found in the output directory.")

        downloaded_file = os.path.join(temp_dir, audio_files[0])
        print(f"✅ Download successful: {downloaded_file}")
        return downloaded_file

    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True) # Clean up on failure
        print(f"❌ Download failed: {e}")
        raise e # Re-raise the exception to be caught by the API endpoint

def transcribe_audio(audio_file_path: str) -> (str, Dict[str, Any]):
    """Transcribe audio using the pre-loaded faster-whisper model."""
    if not whisper_model:
        raise RuntimeError("Whisper model is not loaded.")

    print(f"🎤 Transcribing audio file: {os.path.basename(audio_file_path)}...")
    segments, info = whisper_model.transcribe(audio_file_path)

    transcript = " ".join(seg.text for seg in segments).strip()

    metadata = {
        "language": info.language,
        "language_probability": info.language_probability,
        "duration_seconds": info.duration,
    }
    print("✅ Transcription complete.")
    return transcript, metadata

def summarize_text(text: str, api_key: Optional[str] = None) -> str:
    """Summarize the transcript using the Google Gemini API."""
    if not text:
        return "No transcript was generated to summarize."

    effective_key = api_key or GEMINI_API_KEY
    if not effective_key:
        return "Gemini API key not configured. Cannot generate summary."

    print("🤖 Generating summary with Gemini...")
    try:
        genai.configure(api_key=effective_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
        You are an expert assistant who creates concise, easy-to-read summaries of video transcripts.
        Based on the following transcript, please provide a summary that includes:
        1.  **Main Topic:** A brief, one-sentence description of the video's central theme.
        2.  **Key Points:** A bulleted list of the most important ideas, arguments, or steps discussed.
        3.  **Conclusion:** A short summary of the final conclusion or takeaway message.

        Transcript:
        ---
        {text}
        ---
        """

        response = model.generate_content(prompt)
        print("✅ Summary generated.")
        return response.text.strip()
    except Exception as e:
        print(f"❌ Error during summary generation: {e}")
        return f"Could not generate summary. Error: {e}"

# --- API Endpoints ---
@app.get("/")
async def root():
    return {"message": "YouTube Summarizer API is running"}

@app.post("/process", response_model=TranscriptResponse)
async def process_youtube_video(request: YouTubeRequest):
    """Main endpoint to download, transcribe, and summarize a YouTube video."""
    audio_path = None
    try:
        audio_path = download_audio(str(request.url))
        transcript, metadata = transcribe_audio(audio_path)
        summary = summarize_text(transcript, request.gemini_api_key)

        return TranscriptResponse(
            transcript=transcript,
            summary=summary,
            metadata=metadata
        )
    except Exception as e:
        # This will catch errors from any step (download, transcribe, etc.)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # IMPORTANT: Clean up the temporary directory and file regardless of success or failure.
        if audio_path:
            temp_dir = os.path.dirname(audio_path)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                print(f"🧹 Cleaned up temporary directory: {temp_dir}")

# Note: Download endpoints for transcript/summary are omitted for brevity
# but can be added back from your original code if needed.

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    # Using reload=True is great for development
    uvicorn.run("main:app", host=host, port=port, reload=True)