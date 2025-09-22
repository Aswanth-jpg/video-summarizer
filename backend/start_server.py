#!/usr/bin/env python3
"""
Backend server startup script
"""
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":
    import uvicorn
    from main import app
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    print(f"🚀 Starting YouTube Summarizer API server...")
    print(f"📍 Server will be available at: http://{host}:{port}")
    print(f"📚 API docs available at: http://{host}:{port}/docs")
    
    uvicorn.run(
        "main:app",  # Use import string for reload to work properly
        host=host, 
        port=port,
        reload=True,  # Enable auto-reload for development
        log_level="info"
    )
