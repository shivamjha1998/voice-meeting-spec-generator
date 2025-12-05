# Voice Meeting Spec Generator

A Python application that auto-generates project specifications from voice meetings.

## Architecture

- **Backend**: FastAPI
- **Frontend**: React + TypeScript (Vite)
- **Database**: PostgreSQL
- **Queue**: Redis
- **Bot**: Python (Zoom/Google Meet)

## Getting Started

1.  Start the infrastructure:
    ```bash
    docker compose up -d
    ```

2.  Run the API:
    ```bash
    cd backend/api
    pip install -r requirements.txt
    uvicorn main:app --reload
    ```

3.  Run the Frontend:
    ```bash
    cd frontend
    npm install
    npm run dev
    ```
