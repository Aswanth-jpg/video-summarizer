# 🚀 YouTube AI Summarizer - Setup Guide

## Quick Start (Windows)

### Option 1: Start Both Servers Automatically
```bash
# Double-click this file to start both servers
start_both.bat
```

### Option 2: Start Servers Manually

#### Backend Server
```bash
# Option A: Use the batch file
start_backend.bat

# Option B: Manual commands
venv\Scripts\activate
cd backend
python start_server.py
```

#### Frontend Server
```bash
# Option A: Use the batch file
start_frontend.bat

# Option B: Manual commands
cd frontend
npm run dev
```

## 🔧 Configuration

### 1. Backend Configuration
Create/edit `backend/.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
HOST=0.0.0.0
PORT=8000
```

### 2. Get Your Gemini API Key
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy and paste it in `backend/.env`

## 🌐 Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🔍 Troubleshooting

### Backend Issues
- **Port 8000 already in use**: Change PORT in `backend/.env`
- **Whisper model not loading**: Ensure you have enough RAM (2GB+)
- **Gemini API errors**: Check your API key in `backend/.env`

### Frontend Issues
- **Port 5173 already in use**: Vite will automatically find another port
- **API connection errors**: Ensure backend is running on port 8000
- **Dependencies missing**: Run `npm install` in the frontend directory

### General Issues
- **FFmpeg not found**: Download and add to system PATH
- **Python dependencies**: Run `pip install -r requirements.txt` in backend
- **Node dependencies**: Run `npm install` in frontend

## 📝 Usage

1. Start both servers using `start_both.bat`
2. Open http://localhost:5173 in your browser
3. Enter a YouTube URL
4. Optionally configure your Gemini API key
5. Click "Summarize" and wait for processing
6. Download transcript and summary when ready

## 🛠️ Development

### Backend Development
- Server auto-reloads on file changes
- Check logs in the backend terminal
- API docs available at `/docs`

### Frontend Development
- Hot reload enabled
- Check browser console for errors
- Vite proxy handles API calls to backend

## 📦 Dependencies

### Backend (Python)
- FastAPI
- faster-whisper
- yt-dlp
- google-generativeai
- python-dotenv

### Frontend (Node.js)
- React 18
- Vite
- React Icons
- Axios

## 🔄 Architecture

```
Frontend (React + Vite) ←→ Backend (FastAPI)
     ↓                           ↓
http://localhost:5173    http://localhost:8000
     ↓                           ↓
   Browser ←→ Proxy ←→ API Endpoints
```

The frontend uses Vite's proxy to forward `/api/*` requests to the backend server.
