# Voice Meeting Spec Generator

A comprehensive application that auto-generates project specifications from voice meetings using AI. It records meetings, transcribes audio, and uses LLMs to structure the information into a clear specification.

## Architecture

The project consists of several microservices orchestrated to handle the meeting lifecycle:

-   **Frontend**: React + TypeScript (Vite) - *User interface for managing projects and meetings.*
-   **API**: FastAPI - *Core backend logic, meeting management, and frontend communication.*
-   **Bot**: Python (Selenium/Playwright) - *Headless browser bot to join Zoom/Google Meet calls and record audio.*
-   **Transcription**: Python (FastAPI/Background Worker) - *Handles audio transcription (e.g., interacting with OpenAI Whisper or similar).*
-   **AI**: Python (FastAPI/Background Worker) - *Processes transcripts to generate specifications using LLMs (OpenAI/HuggingFace).*
-   **TTS**: Python (FastAPI/Background Worker) - *Text-to-Speech service for bot interactions.*
-   **Database**: PostgreSQL - *Persistent storage for projects, meetings, and specs.*
-   **Queue**: Redis - *Message broker for asynchronous tasks and service communication.*

## Prerequisites

Before running the project, ensure you have the following installed:

*   **Docker & Docker Compose**: For running the full stack easily.
*   **Node.js (v18+) & npm**: For the frontend.
*   **Python (v3.11+)**: For backend development.
*   **System Dependencies** (for local backend dev):
    *   `ffmpeg`: Required for audio processing.
    *   `portaudio19-dev` (Linux) / `portaudio` (Mac via Homebrew): Required for audio recording libraries.

## Configuration

Create a `.env` file in the root directory based on `.env.example` (if available) or add the following keys:

```env
# Database
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=voice_meeting_db
DATABASE_URL=postgresql://user:password@localhost:5432/voice_meeting_db

# Redis
REDIS_URL=redis://localhost:6379/0

# API Keys
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
HUGGING_FACE_KEY=your_huggingface_key
```

> **Note**: For Docker, the service hostnames (`db`, `redis`) are handled automatically in `docker-compose.yml`.

## Getting Started

### Option 1: Running with Docker (Recommended)

This enables all services (Frontend, API, Bot, AI, Transcription, TTS, DB, Redis).

1.  **Build and Start Services**:
    ```bash
    docker compose up -d --build
    ```

2.  **Access the Application**:
    *   Frontend: `http://localhost:5173` (or port defined in compose)
    *   API Docs: `http://localhost:8000/docs`

### Option 2: Running Locally

If you need to develop on specific services, you can run them locally.

#### 1. Infrastructure (DB & Redis)
You still need the database and redis running. You can use Docker for just these:
```bash
docker compose up -d db redis
```

#### 2. Backend Services
It is recommended to use a virtual environment.

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install System Dependencies (MacOS example)
brew install ffmpeg portaudio

# Install Python Dependencies
# You may need to install requirements for specific services you are working on
pip install -r backend/api/requirements.txt
pip install -r backend/bot/requirements.txt
pip install -r backend/transcription/requirements.txt
# Install additional packages if needed
pip install google-cloud-texttospeech

# Run a Service (example: API)
# Ensure your .env variables are exported or available to the process
export PYTHONPATH=$PYTHONPATH:.
uvicorn backend.api.main:app --reload --port 8000
```

#### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```
The frontend will typically run on `http://localhost:5173`.
