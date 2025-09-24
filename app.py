import streamlit as st
import warnings
import os
import shutil
import tempfile

def load_env_file():
    """Load environment variables from .env file"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    os.environ[key] = value

# Load environment variables from .env file
load_env_file()

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

# --- Set Gemini API ---
gemini_secrets_key = None
try:
    gemini_secrets_key = st.secrets.get("GEMINI_API_KEY")
except Exception:
    gemini_secrets_key = None

gemini_env_key = os.getenv("GEMINI_API_KEY")
GEMINI_API_KEY = gemini_secrets_key or gemini_env_key

# Initialize Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Sidebar for API configuration
with st.sidebar:
    st.markdown("**🤖 Gemini AI Configuration**")
    
    current_set = bool(GEMINI_API_KEY)
    st.caption(f"Gemini API key loaded: {'✅ Yes' if current_set else '❌ No'}")
    
    if "gemini_key" not in st.session_state:
        st.session_state.gemini_key = ""
    
    entered = st.text_input(
        "Enter GEMINI_API_KEY", 
        value=st.session_state.gemini_key, 
        type="password", 
        help="Get your key from https://aistudio.google.com/app/apikey"
    )
    
    if entered and entered != st.session_state.gemini_key:
        st.session_state.gemini_key = entered
        genai.configure(api_key=entered)
        GEMINI_API_KEY = entered
        st.rerun()
    
    st.markdown("---")
    st.markdown("**📖 How to get Gemini API key:**")
    st.markdown("1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)")
    st.markdown("2. Sign in with your Google account")
    st.markdown("3. Create a new API key")
    st.markdown("4. Copy and paste it above")

# Warning message
if not (GEMINI_API_KEY or st.session_state.get("gemini_key")):
    st.warning("🔑 Gemini API key not found. Add it in the sidebar, or set in .streamlit/secrets.toml or env var GEMINI_API_KEY.")

# --- Load Whisper model ---
@st.cache_resource
def load_model():
    return WhisperModel("base", device="cpu", compute_type="int8")

model = load_model()

# --- Helper: Download YouTube audio using yt-dlp ---
def download_audio(youtube_url: str) -> str:
    """Download audio from YouTube using yt-dlp with robust error handling"""
    temp_dir = tempfile.mkdtemp()
    
    # Multiple strategies to handle different YouTube protection schemes
    strategies = [
        # Strategy 1: Standard audio (works best for most videos)
        {
            'format': 'bestaudio/best',
            'extractaudio': False,
            'writethumbnail': False,
            'writeinfojson': False,
        },
        # Strategy 2: Specific audio formats
        {
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio',
            'extractaudio': False,
            'writethumbnail': False,
            'writeinfojson': False,
        },
        # Strategy 3: Extract audio from low-quality video
        {
            'format': 'best[height<=480]',
            'extractaudio': True,
            'audioformat': 'mp3',
            'writethumbnail': False,
            'writeinfojson': False,
        },
        # Strategy 4: Any video format for audio extraction
        {
            'format': 'worst',
            'extractaudio': True,
            'audioformat': 'mp3',
            'writethumbnail': False,
            'writeinfojson': False,
        }
    ]
    
    for i, strategy in enumerate(strategies):
        ydl_opts = {
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'extract_flat': False,
            # Add more options to handle YouTube's protection
            'extractor_args': {
                'youtube': {
                    'skip': ['translated_subs'],
                    'player_skip': ['webpage'],
                }
            },
            **strategy
        }
    
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                if not info:
                    continue
                    
                duration = info.get('duration', 0)
                if duration and duration > 3600:
                    st.warning(f"Video is {duration//60} minutes long. This may take a while to process.")
                
                ydl.download([youtube_url])
                
                files = os.listdir(temp_dir)
                audio_files = [f for f in files if f.endswith(('.mp3', '.m4a', '.webm', '.opus', '.aac', '.ogg', '.flac', '.wav'))]
                
                if audio_files:
                    downloaded_file = os.path.join(temp_dir, audio_files[0])
                    if os.path.exists(downloaded_file) and os.path.getsize(downloaded_file) > 0:
                        return downloaded_file
                        
        except yt_dlp.DownloadError as e:
            continue
        except Exception as e:
            continue
    
    # If all strategies failed
    shutil.rmtree(temp_dir, ignore_errors=True)
    raise RuntimeError("All download strategies failed. This video may be region-restricted, age-restricted, or have YouTube's new protection that prevents downloading.")

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

# --- Helper: Transcribe with faster-whisper ---
def transcribe_audio(audio_file: str):
    audio_for_model = maybe_convert_to_wav(audio_file)
    segments, info = model.transcribe(audio_for_model)

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

# --- Helper: Summarize text with Gemini AI ---
def summarize_text(text: str, model_name: str = "gemini-1.5-flash") -> str:
    """Summarize text using Google Gemini"""
    if not text.strip():
        return "⚠️ No transcript text available to summarize."
    
    effective_key = GEMINI_API_KEY or st.session_state.get("gemini_key")
    if not effective_key:
        return "⚠️ Gemini API key not configured. Add it in the sidebar."
    
    if st.session_state.get("gemini_key") and st.session_state.get("gemini_key") != GEMINI_API_KEY:
        genai.configure(api_key=st.session_state.get("gemini_key"))
    
    try:
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

# --- Streamlit UI ---
st.title("🎬 YouTube Video Summarizer (Whisper + Gemini AI)")
st.write("Paste a YouTube link → download audio → transcribe → summarize with Google Gemini.")

url = st.text_input("Enter YouTube video link:")

if st.button("Summarize"):
    if url:
        try:
            with st.spinner("📥 Downloading audio..."):
                audio_path = download_audio(url)

            with st.spinner("📝 Transcribing with Faster-Whisper..."):
                transcript, segments, meta = transcribe_audio(audio_path)

            st.subheader("🗣️ Transcript")
            if meta.get("language") is not None or meta.get("duration") is not None:
                lang = meta.get("language") or "unknown"
                dur = meta.get("duration")
                if isinstance(dur, (int, float)):
                    st.caption(f"Detected language: {lang} • Duration: {dur:.1f}s")
                else:
                    st.caption(f"Detected language: {lang}")
            st.text_area("Full transcript", transcript, height=200)
            st.download_button("Download Transcript", transcript, file_name="transcript.txt")

            # with st.expander("Show timed segments"):
            #     try:
            #         import pandas as pd
            #         st.dataframe(pd.DataFrame(segments))
            #     except Exception:
            #         st.write(segments)

            with st.spinner("✨ Summarizing with Gemini AI..."):
                summary = summarize_text(transcript)

            st.subheader("📌 Video Summary")
            st.write(summary)

            st.download_button("Download Summary", summary, file_name="summary.txt")

        except Exception as e:
            st.error(f"Error: {str(e)}")
    else:
        st.warning("Please enter a YouTube link.")