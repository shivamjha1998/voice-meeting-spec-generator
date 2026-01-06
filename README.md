# Voice Meeting Spec Generator

A comprehensive application that auto-generates project specifications from voice meetings using AI. It records meetings, transcribes audio, and uses LLMs to structure the information into a clear specification.

## Architecture

The project consists of several microservices orchestrated to handle the meeting lifecycle:

- **Frontend**: React + TypeScript (Vite) - _User interface for managing projects and meetings._
- **API**: FastAPI - _Core backend logic, meeting management, and frontend communication._
- **Bot**: Python (Playwright) - _Headless browser bot to join Zoom/Google Meet calls and record audio._
- **Transcription**: Python (FastAPI/Background Worker) - _Handles audio transcription using ElevenLabs Whisper._
- **AI**: Python (Celery Worker) - _Processes transcripts to generate specifications using LLMs (HuggingFace)._
- **Real-time AI**: Python (Background Service) - _Generates clarifying questions during meetings._
- **TTS**: Python (FastAPI/Background Worker) - _Text-to-Speech service using ElevenLabs for bot interactions._
- **Database**: PostgreSQL - _Persistent storage for projects, meetings, and specs._
- **Queue**: Redis - _Message broker for asynchronous tasks and service communication._

## Prerequisites

Before running the project, ensure you have the following installed:

- **Docker & Docker Compose**: For running the backend services.
- **Node.js (v18+) & npm**: For the frontend.
- **Python (v3.11+)**: For local bot development.

### For Local Bot Development (macOS)

- **PortAudio**: Required for PyAudio

```bash
    brew install portaudio
```

- **FFmpeg**: Required for audio recording
```bash
    brew install ffmpeg
```

- **BlackHole Audio Driver**: Required for audio routing

```bash
    brew install blackhole-2ch blackhole-16ch
```

- **System Audio Configuration**:
  - Open Audio MIDI Setup
  - Create a Multi-Output Device combining your speakers and BlackHole 2ch
  - Create an Aggregate Device combining BlackHole 2ch (input) and BlackHole 16ch (output)

## Configuration

Create a `.env` file in the root directory with the following keys:

```env
# Database
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=voice_meeting_db
DATABASE_URL=postgresql://user:password@db:5432/voice_meeting_db

# Redis
REDIS_URL=redis://redis:6379/0

# API Keys
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
HUGGING_FACE_KEY=your_huggingface_key

# GitHub OAuth (Optional - for GitHub integration)
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
CALLBACK_URL=http://localhost:8000/auth/github/callback

# Security
ENCRYPTION_KEY=your_fernet_encryption_key_here
```

> **Note**: Generate an encryption key using: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

## Getting Started

### Step 1: Start Backend Services

Start all backend services except the bot:

```bash
docker compose up -d
```

Then stop the bot container (we'll run it locally):

```bash
docker compose stop bot
```

Verify services are running:

```bash
docker compose ps
```

You should see:

- ✅ db (PostgreSQL)
- ✅ redis
- ✅ api (FastAPI on port 8000)
- ✅ transcription
- ✅ ai (Celery worker)
- ✅ realtime-ai
- ✅ tts
- ⏸️ bot (stopped - we'll run this locally)

### Step 2: Run Bot Locally

In a new terminal window:

```bash
python3 -m backend.bot.main
```
> **Note**: Ensure you're in the project root

> **Why run the bot locally?** The bot requires access to your system's audio devices (BlackHole) and browser profile, which is easier to configure when running locally during development.

### Step 3: Start Frontend

In another terminal window:

```bash
cd frontend
npm install  # Only needed first time
npm run dev
```

The frontend will be available at `http://localhost:5173`

### Step 4: First-Time Setup

1. **Authenticate with GitHub** (if using GitHub integration):

   - Click "Sign in with GitHub" on the homepage
   - Authorize the application
   - You'll be redirected back to the dashboard

2. **Manual Google Login** (required for Google Meet):

```bash
   python3 backend/bot/manual_login.py
```

- Log in to your Google account in the browser that opens
- Complete any 2FA if required
- Press Enter when done to save the session
- This creates a persistent browser profile for the bot

### Step 5: Start a Meeting

1. Create a new project from the dashboard
2. Click "Start New Meeting"
3. Enter the meeting URL (Zoom or Google Meet)
4. ✅ Check the consent box (required)
5. Click "Start Meeting & Invite Bot"
6. The bot will automatically join and start recording

## Development Workflow

### Stopping Services

```bash
# Stop all Docker services
docker compose down

# Or keep data and just stop
docker compose stop

# Stop local bot (Ctrl+C in its terminal)
# Stop frontend (Ctrl+C in its terminal)
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f transcription
docker compose logs -f ai

# Local bot logs appear in its terminal
# Frontend logs appear in its terminal
```

### Resetting the Database

```bash
docker compose down -v  # Removes volumes (WARNING: deletes all data)
docker compose up -d
```

## Troubleshooting

### Bot Issues

**Bot won't join meetings:**

- Ensure BlackHole audio drivers are installed
- Run `python3 backend/bot/manual_login.py` to refresh Google login
- Check that your audio devices are properly configured in Audio MIDI Setup

**Audio not recording:**

- Verify BlackHole devices are active: `python3 -c "import pyaudio; p = pyaudio.PyAudio(); [print(p.get_device_info_by_index(i)) for i in range(p.get_device_count())]"`
- Ensure Multi-Output and Aggregate devices are configured correctly

### Backend Issues

**Services won't start:**

```bash
docker compose down
docker compose up -d --build
```

**Database connection errors:**

- Check `.env` file has correct DATABASE_URL
- Ensure PostgreSQL container is running: `docker compose ps db`

### Frontend Issues

**Port 5173 already in use:**

```bash
# Kill the process using the port
lsof -ti:5173 | xargs kill -9
npm run dev
```

**API connection refused:**

- Verify API is running: `curl http://localhost:8000/health`
- Check CORS settings in `backend/api/main.py`

## API Documentation

Once the API is running, visit:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Testing

```bash
# Run backend tests
docker compose exec api pytest backend/tests

# Run frontend tests (if configured)
cd frontend
npm test
```

## Production Deployment

For production deployment, you'll need to:

1. Set `headless=True` in bot configuration
2. Configure proper audio device mapping in Docker
3. Use environment-specific `.env` files
4. Set up proper SSL/TLS certificates
5. Configure production database with backups
6. Set up monitoring and logging aggregation

Refer to the CI/CD pipeline configuration in `.github/workflows/ci_cd.yml` for automated deployment.

## Architecture Notes

- **Real-time Communication**: WebSockets for live transcript streaming
- **Audio Processing**: BlackHole virtual audio devices for system audio capture
- **Persistent Sessions**: Playwright browser profiles for authenticated meeting access
- **Asynchronous Processing**: Celery + Redis for background spec generation
- **Encryption**: All sensitive data (tokens, audio files) encrypted at rest

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request
