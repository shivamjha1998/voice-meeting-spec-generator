FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    portaudio19-dev \
    ffmpeg \
    python3-dev \
    pulseaudio \
    pulseaudio-utils \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY backend/api/requirements.txt /tmp/api_reqs.txt
COPY backend/bot/requirements.txt /tmp/bot_reqs.txt
COPY backend/transcription/requirements.txt /tmp/transcription_reqs.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /tmp/api_reqs.txt
RUN pip install --no-cache-dir -r /tmp/bot_reqs.txt
RUN pip install --no-cache-dir -r /tmp/transcription_reqs.txt
RUN pip install --no-cache-dir google-cloud-texttospeech cryptography

# Copy the entire project
COPY . /app

# Copy and set up the entrypoint script
COPY backend/entrypoint.sh /app/backend/entrypoint.sh
RUN chmod +x /app/backend/entrypoint.sh

# Set PYTHONPATH to include the project root
ENV PYTHONPATH=/app

# Use the script as the entrypoint
ENTRYPOINT ["/app/backend/entrypoint.sh"]

# Default command (overridden in docker-compose)
CMD ["python", "-m", "backend.api.main"]
