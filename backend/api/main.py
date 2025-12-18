import redis.asyncio as redis_async
import asyncio
import os
import httpx
import json
import redis
import requests
from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

from backend.common import models, database
from backend.api import schemas, crud
from backend.ai.llm_client import LLMClient

load_dotenv()

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL", "http://localhost:8000/auth/github/callback")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create DB tables
    models.Base.metadata.create_all(bind=database.engine)
    yield
    # Shutdown: Clean up if necessary (e.g. close connections)

app = FastAPI(title="Voice Meeting Spec Generator API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to Voice Meeting Spec Generator API"}

# --- Auth Routes ---
@app.get("/auth/github/login")
async def github_login():
    return RedirectResponse(
        f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=repo,user:email"
    )

@app.get("/auth/github/callback")
async def github_callback(code: str, db: Session = Depends(database.get_db)):
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": CALLBACK_URL
            }
        )
        token_data = token_res.json()
    
    if "error" in token_data:
        raise HTTPException(status_code=400, detail=token_data.get("error_description"))
    
    access_token = token_data["access_token"]

    async with httpx.AsyncClient() as client:
        user_res = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_data = user_res.json()
        
        email_res = await client.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        emails = email_res.json()
        primary_email = next((e["email"] for e in emails if e["primary"]), None)

    user_email = primary_email or user_data.get("email")
    if not user_email:
        raise HTTPException(status_code=400, detail="Could not retrieve email from GitHub")

    existing_user = crud.get_user_by_email(db, email=user_email)
    
    if existing_user:
        db_user = crud.update_user_token(db, existing_user.id, access_token)
    else:
        new_user = schemas.UserCreate(
            email=user_email,
            username=user_data.get("login"),
            avatar_url=user_data.get("avatar_url"),
            github_token=access_token
        )
        db_user = crud.create_user(db, new_user)

    return RedirectResponse(f"http://localhost:5173?user_id={db_user.id}")

@app.get("/health")
def health_check():
    return {"status": "ok"}

# Project Routes
@app.post("/projects/", response_model=schemas.Project)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(database.get_db)):
    return crud.create_project(db=db, project=project)

@app.get("/projects/", response_model=List[schemas.Project])
def read_projects(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    return crud.get_projects(db, skip=skip, limit=limit)

@app.get("/projects/{project_id}", response_model=schemas.Project)
def read_project(project_id: int, db: Session = Depends(database.get_db)):
    db_project = crud.get_project(db, project_id=project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project

@app.delete("/projects/{project_id}", response_model=schemas.Project)
def delete_project(project_id: int, db: Session = Depends(database.get_db)):
    db_project = crud.delete_project(db, project_id=project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project

# Meeting Routes
@app.post("/meetings/", response_model=schemas.Meeting)
def create_meeting(meeting: schemas.MeetingCreate, db: Session = Depends(database.get_db)):
    return crud.create_meeting(db=db, meeting=meeting)

@app.get("/meetings/", response_model=List[schemas.Meeting])
def read_meetings(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    return crud.get_meetings(db, skip=skip, limit=limit)

@app.get("/meetings/{meeting_id}", response_model=schemas.Meeting)
def read_meeting(meeting_id: int, db: Session = Depends(database.get_db)):
    db_meeting = crud.get_meeting(db, meeting_id=meeting_id)
    if db_meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return db_meeting

@app.get("/meetings/{meeting_id}/transcripts", response_model=List[schemas.Transcript])
def read_meeting_transcripts(meeting_id: int, db: Session = Depends(database.get_db)):
    return crud.get_meeting_transcripts(db, meeting_id=meeting_id)

@app.post("/meetings/{meeting_id}/generate")
def generate_specification(meeting_id: int, db: Session = Depends(database.get_db)):
    meeting = crud.get_meeting(db, meeting_id=meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    try:
        redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        job_data = {"meeting_id": meeting.id, "project_id": meeting.project_id}
        redis_client.rpush("spec_generation_queue", json.dumps(job_data))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue task: {str(e)}")

    return {"status": "queued", "message": "Specification generation started"}

@app.post("/meetings/{meeting_id}/join")
def join_meeting(meeting_id: int, db: Session = Depends(database.get_db)):
    meeting = crud.get_meeting(db, meeting_id=meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    try:
        redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        job_data = {
            "meeting_id": meeting.id,
            "meeting_url": meeting.meeting_url,
            "platform": "zoom" if "zoom.us" in meeting.meeting_url else "meet"
        }
        redis_client.rpush("bot_join_queue", json.dumps(job_data))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue bot join task: {str(e)}")

    return {"status": "queued", "message": "Bot join request queued"}

@app.get("/meetings/{meeting_id}/specification", response_model=schemas.Specification)
def read_meeting_specification(meeting_id: int, db: Session = Depends(database.get_db)):
    spec = crud.get_meeting_specification(db, meeting_id=meeting_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found")
    return spec

@app.put("/meetings/{meeting_id}/specification", response_model=schemas.Specification)
def update_meeting_specification(
    meeting_id: int, 
    spec_update: schemas.SpecificationUpdate, 
    db: Session = Depends(database.get_db)
):
    # Check if exists first
    existing_spec = crud.get_meeting_specification(db, meeting_id)
    if not existing_spec:
        raise HTTPException(status_code=404, detail="Specification not found")
        
    updated_spec = crud.update_specification(db, meeting_id, spec_update.content)
    return updated_spec

@app.get("/meetings/{meeting_id}/tasks/preview")
def preview_tasks(meeting_id: int, db: Session = Depends(database.get_db)):
    """Extracts tasks using AI but does not save them. Returns a list for review."""
    spec = crud.get_meeting_specification(db, meeting_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found")

    try:
        llm = LLMClient()
        tasks_json = llm.extract_tasks(spec.content)
        tasks_data = json.loads(tasks_json).get("tasks", [])
        return tasks_data
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"AI Task Extraction failed: {str(e)}")

@app.post("/meetings/{meeting_id}/tasks/sync")
def sync_tasks_to_github(
    meeting_id: int, 
    tasks: List[schemas.TaskBase], 
    db: Session = Depends(database.get_db), 
    user_id: int = 1
):
    """Takes a reviewed list of tasks, creates GitHub issues, and saves to DB."""
    
    # 1. Validation
    spec = crud.get_meeting_specification(db, meeting_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.github_token:
        raise HTTPException(status_code=400, detail="User not authenticated with GitHub")

    project = crud.get_project(db, spec.project_id)
    if not project or not project.github_repo_url:
        raise HTTPException(status_code=400, detail="Project missing GitHub Repo URL")

    try:
        parts = project.github_repo_url.strip("/").split("/")
        owner, repo = parts[-2], parts[-1]
    except:
        raise HTTPException(status_code=400, detail="Invalid GitHub Repo URL")

    headers = {
        "Authorization": f"token {user.github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    results = []
    
    # 2. Loop through reviewed tasks
    for task_data in tasks:
        # Create on GitHub
        issue_body = {
            "title": task_data.title,
            "body": f"{task_data.description}\n\n*Generated by Voice Meeting Spec Generator*"
        }
        res = requests.post(f"https://api.github.com/repos/{owner}/{repo}/issues", json=issue_body, headers=headers)
        
        issue_num = None
        status = "failed"
        html_url = ""
        
        if res.status_code == 201:
            gh_data = res.json()
            issue_num = gh_data.get("number")
            html_url = gh_data.get("html_url")
            status = "created"
        
        # Save to DB (even if GitHub failed, we might want to keep the local record, 
        # but here we only save if GitHub succeeded or partially succeeded)
        if issue_num:
            db_task = schemas.TaskCreate(
                specification_id=spec.id,
                title=task_data.title,
                description=task_data.description,
                github_issue_number=issue_num
            )
            crud.create_task(db, db_task)

        results.append({
            "title": task_data.title, 
            "status": status, 
            "issue_url": html_url
        })

    return {"results": results}

@app.get("/user/repos")
def read_user_repos(user_id: int, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.github_token:
        raise HTTPException(status_code=401, detail="User not authorised with GitHub")

    headers = {
        "Authorization": f"token {user.github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.get("https://api.github.com/user/repos?sort=updated&per_page=100", headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch repositories")

    repos = response.json()
    return [
        {"id": r["id"], "name": r["name"], "full_name": r["full_name"], "html_url": r["html_url"]} 
        for r in repos
    ]

@app.websocket("/ws/meetings/{meeting_id}")
async def websocket_endpoint(websocket: WebSocket, meeting_id: int):
    await websocket.accept()
    
    # Create a dedicated async Redis connection for this websocket
    r = redis_async.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    pubsub = r.pubsub()
    
    channel_name = f"meeting_{meeting_id}_updates"
    await pubsub.subscribe(channel_name)
    
    print(f"🟢 WS Connected: {channel_name}")

    try:
        while True:
            # Wait for message from Redis
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            
            if message:
                # message['data'] is bytes, decode to string
                data = message['data'].decode('utf-8')
                # Send to Frontend
                await websocket.send_text(data)
            
            # Keep connection alive / yield control
            # (In a real app, you might want a heartbeart or rely on ping/pong)
            await asyncio.sleep(0.01)
            
    except WebSocketDisconnect:
        print(f"mb WS Disconnected: {channel_name}")
    except Exception as e:
        print(f"❌ WS Error: {e}")
    finally:
        await pubsub.unsubscribe(channel_name)
        await r.close()

@app.post("/meetings/{meeting_id}/end")
def end_meeting(meeting_id: int, db: Session = Depends(database.get_db)):
    """Ends the meeting, stops the bot, and triggers spec generation."""
    
    # 1. Update DB
    meeting = crud.get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    meeting.ended_at = datetime.utcnow()
    db.commit()
    
    redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

    # 2. Send STOP signal to Bot
    # We'll use a specific key pattern that the bot checks
    redis_client.set(f"stop_meeting_{meeting_id}", "true")
    
    # 3. Trigger Spec Generation (Auto-generate)
    try:
        job_data = {"meeting_id": meeting.id, "project_id": meeting.project_id}
        redis_client.rpush("spec_generation_queue", json.dumps(job_data))
    except Exception as e:
        print(f"Failed to queue spec generation: {e}")

    return {"status": "success", "message": "Meeting ended, bot stopped, spec generation started."}

@app.get("/settings/", response_model=List[schemas.Setting])
def read_settings(db: Session = Depends(database.get_db)):
    settings = crud.get_settings(db)
    # Seed defaults if empty
    if not settings:
        defaults = [
            {"key": "spec_prompt", "value": "Create a detailed technical specification based on this summary. Include: 1. Overview 2. Functional Requirements 3. Database Schema.", "description": "Prompt used to generate the final specification"},
            {"key": "question_prompt", "value": "You are a helpful PM. If the transcript is ambiguous, ask a short clarifying question. If clear, say NO_QUESTION.", "description": "Prompt used for real-time clarifying questions"}
        ]
        results = []
        for d in defaults:
            s = crud.update_setting(db, schemas.SettingCreate(**d))
            results.append(s)
        return results
    return settings

@app.put("/settings/{key}", response_model=schemas.Setting)
def update_setting(key: str, setting: schemas.SettingCreate, db: Session = Depends(database.get_db)):
    if key != setting.key:
         raise HTTPException(status_code=400, detail="Key mismatch")
    return crud.update_setting(db, setting)