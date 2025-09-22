# 🎬 YouTube AI Summarizer Bot

An intelligent YouTube video summarizer that automatically downloads, transcribes, and generates AI-powered summaries of YouTube videos using OpenAI's Whisper and Google's Gemini AI.

## 🚀 Features

### Core Functionality
- **🎥 YouTube Video Processing**: Download audio from any YouTube video using `yt-dlp`
- **🗣️ Audio Transcription**: High-quality speech-to-text using OpenAI's Faster Whisper model
- **🤖 AI-Powered Summarization**: Generate intelligent summaries using Google Gemini AI
- **📱 Web Interface**: User-friendly Streamlit web application
- **📥 Download Options**: Download both transcripts and summaries as text files

### Key Capabilities
- **Multi-format Audio Support**: Handles various audio formats (MP3, M4A, WebM, etc.)
- **Language Detection**: Automatically detects the language of the video
- **Duration Awareness**: Warns for long videos and shows processing time estimates
- **Timed Segments**: Maintains timestamp information for detailed transcript analysis
- **Error Handling**: Robust error handling with informative messages
- **API Key Management**: Secure handling of API keys through environment variables or UI input

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+ (tested with Python 3.13)
- FFmpeg (for audio processing)
- Google Gemini API key

### 1. Clone the Repository
```bash
git clone https://github.com/Aswanth-jpg/video-summarizer.git
cd video-summarizer
```

### 2. Create Virtual Environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install FFmpeg
**Windows:**
- Download from [FFmpeg official site](https://ffmpeg.org/download.html)
- Extract and add to system PATH

**Linux:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Mac:**
```bash
brew install ffmpeg
```

### 5. Configure API Keys

#### Option A: Environment File (Recommended)
Create a `.env` file in the project root:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

#### Option B: Streamlit Secrets
Create `.streamlit/secrets.toml`:
```toml
GEMINI_API_KEY = "your_gemini_api_key_here"
```

#### Option C: Runtime Input
Enter your API key directly in the web interface sidebar.

### 6. Get Your Gemini API Key
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy and use in your configuration

## 🎯 Usage

### Start the Application
```bash
streamlit run app.py
```

### Using the Web Interface
1. **Open your browser** to `http://localhost:8501`
2. **Configure API key** (if not already set in environment)
3. **Paste YouTube URL** in the input field
4. **Click "Summarize"** and wait for processing
5. **View results**:
   - Full transcript with language detection
   - AI-generated summary with key points
   - Download options for both transcript and summary

### Example Workflow
```
YouTube URL → Audio Download → Whisper Transcription → Gemini Summarization → Results
```

## 📁 Project Structure

```
AI-YT-bot/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore rules
├── README.md             # This file
├── test_gemini.py        # Gemini API test script
├── test_openai.py        # OpenAI API test script
├── test_whisper.py       # Whisper model test script
└── test_ytdlp.py         # YouTube download test script
```

## 🧪 Testing

Test individual components:

```bash
# Test Gemini API connection
python test_gemini.py

# Test YouTube download
python test_ytdlp.py

# Test Whisper transcription
python test_whisper.py

# Test OpenAI API (if applicable)
python test_openai.py
```

## 📋 Dependencies

| Package | Purpose |
|---------|---------|
| `streamlit` | Web interface framework |
| `yt-dlp` | YouTube video/audio downloader |
| `faster-whisper` | Speech-to-text transcription |
| `google-generativeai` | Google Gemini AI integration |
| `ctranslate2` | Optimized inference engine |
| `pandas` | Data manipulation (optional) |

## ⚙️ Configuration Options

### Model Settings
- **Whisper Model**: Currently uses `base` model (can be changed to `tiny`, `small`, `medium`, `large`)
- **Compute Type**: Set to `int8` for CPU optimization
- **Gemini Model**: Uses `gemini-1.5-flash` for fast responses

### Audio Processing
- **Automatic Format Detection**: Supports multiple audio formats
- **Quality Optimization**: Converts to optimal format for Whisper
- **Duration Warnings**: Alerts for videos longer than 1 hour

## 🔧 Troubleshooting

### Common Issues

**1. FFmpeg Not Found**
```
Error: ffmpeg not found
Solution: Install FFmpeg and add to system PATH
```

**2. API Key Issues**
```
Error: API key not valid
Solution: Check your Gemini API key in .env file or sidebar
```

**3. Large Video Processing**
```
Warning: Video is X minutes long
Solution: Be patient, processing time scales with video length
```

**4. Module Import Errors**
```
Error: No module named 'X'
Solution: pip install -r requirements.txt
```

## 🚀 Performance Tips

- Use shorter videos (< 30 minutes) for faster processing
- Ensure stable internet connection for YouTube downloads
- Consider using `tiny` Whisper model for faster transcription
- Close other applications to free up system resources

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for speech recognition
- [Google Gemini](https://ai.google.dev/) for AI summarization
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube downloading
- [Streamlit](https://streamlit.io/) for the web interface

## 📞 Support

If you encounter any issues or have questions:
1. Check the troubleshooting section
2. Run the test scripts to isolate the problem
3. Open an issue on GitHub with detailed error messages

---

**Made with ❤️ by [Aswanth](https://github.com/Aswanth-jpg)**
