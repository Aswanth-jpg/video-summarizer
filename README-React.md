# YouTube Video Summarizer - React + FastAPI

A modern web application that converts YouTube videos into concise summaries using AI-powered transcription and analysis.

## Architecture

- **Frontend**: React 18 + Vite with modern responsive design
- **Backend**: FastAPI with async processing
- **AI**: Faster-Whisper + Google Gemini AI

## Quick Start

### Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
copy .env.example .env  # Add your GEMINI_API_KEY
python main.py
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` to use the app!

## Usage

1. Enter a YouTube URL
2. Optionally configure your Gemini API key
3. Click "Summarize"
4. Download transcript/summary when ready

## API Endpoints

- `POST /process` - Process YouTube video
- `GET /health` - Check system status
- `POST /download/transcript` - Download transcript
- `POST /download/summary` - Download summary

Backend runs on `http://localhost:8000`