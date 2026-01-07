FROM python:3.11-slim

WORKDIR /app

# 1. Install System Dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    portaudio19-dev \
    ffmpeg \
    python3-dev \
    pulseaudio \
    pulseaudio-utils \
    alsa-utils \
    xvfb \
    curl \
    # DBus is often required for PulseAudio
    dbus \
    && rm -rf /var/lib/apt/lists/*

# 2. Configure Audio Permissions
# Add root to audio groups
RUN usermod -aG pulse-access root
RUN usermod -aG audio root

# 3. Configure PulseAudio for Root/System usage
# Allow root, disable spawning (we handle it), set default socket path
RUN sed -i 's/^; daemonize = no/daemonize = yes/' /etc/pulse/daemon.conf && \
    sed -i 's/^; system-instance = no/system-instance = yes/' /etc/pulse/daemon.conf && \
    sed -i 's/^; enable-shm = yes/enable-shm = no/' /etc/pulse/daemon.conf

# 4. ALSA Configuration (Force Pulse)
RUN echo "pcm.!default { type pulse }" > /etc/asound.conf && \
    echo "ctl.!default { type pulse }" >> /etc/asound.conf

# 5. Client Configuration (Point to the shared socket)
ENV PULSE_SERVER=unix:/run/pulse/native
ENV PULSE_COOKIE=/root/.config/pulse/cookie

# Install Python dependencies
COPY backend/api/requirements.txt /tmp/api_reqs.txt
COPY backend/bot/requirements.txt /tmp/bot_reqs.txt
COPY backend/transcription/requirements.txt /tmp/transcription_reqs.txt

RUN pip install --no-cache-dir -r /tmp/api_reqs.txt
RUN pip install --no-cache-dir -r /tmp/bot_reqs.txt
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r /tmp/transcription_reqs.txt
RUN pip install --no-cache-dir google-cloud-texttospeech cryptography celery
RUN playwright install --with-deps chromium

COPY . /app

# Entrypoint setup
COPY backend/entrypoint.sh /app/backend/entrypoint.sh
RUN chmod +x /app/backend/entrypoint.sh

ENV PYTHONPATH=/app
ENV DISPLAY=:99
ENTRYPOINT ["/app/backend/entrypoint.sh"]
CMD ["python", "-m", "backend.api.main"]