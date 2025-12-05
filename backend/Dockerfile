FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# portaudio19-dev is required for pyaudio
# ffmpeg is required for audio processing
RUN apt-get update && apt-get install -y \
    gcc \
    portaudio19-dev \
    ffmpeg \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY backend/api/requirements.txt /tmp/api_reqs.txt
COPY backend/bot/requirements.txt /tmp/bot_reqs.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /tmp/api_reqs.txt
RUN pip install --no-cache-dir -r /tmp/bot_reqs.txt
# Install additional dependencies for other services not yet in requirements.txt
RUN pip install --no-cache-dir google-cloud-texttospeech

# Copy the entire project
COPY . /app

# Set PYTHONPATH to include the project root
ENV PYTHONPATH=/app

# Default command (overridden in docker-compose)
CMD ["python", "-m", "backend.api.main"]
