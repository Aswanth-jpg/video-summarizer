FROM python:3.12-slim

WORKDIR /app

# Install ffmpeg and build tools
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Always upgrade yt-dlp to latest — it updates frequently to keep up with YouTube
RUN pip install --no-cache-dir --upgrade yt-dlp

# Copy the application
COPY . .

# Expose FastAPI port
EXPOSE 8001

# Start FastAPI
CMD ["uvicorn", "simple_main:app", "--host", "0.0.0.0", "--port", "8001"]
