import redis.asyncio as redis_async
import asyncio
import os
import httpx
import json
import redis
import redis.asyncio as redis_async
import requests
from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List
from dotenv import load_dotenv
load_dotenv()

from backend.common import models, database
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

from backend.api import schemas, crud
from backend.ai.llm_client import LLMClient
from backend.common.security import decrypt_value
from backend.celery_app import celery_app
from backend.ai.tasks import generate_specification_task

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL", "http://localhost:8000/auth/github/callback")

redis_pool = redis_async.ConnectionPool.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

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
    
    generate_specification_task.delay(meeting.id, meeting.project_id)

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
async def sync_tasks_to_github(
    meeting_id: int, 
    tasks: List[schemas.TaskBase], 
    db: Session = Depends(database.get_db), 
    user_id: int = 1
):
    """
    Syncs tasks to GitHub Issues asynchronously (High Performance).
    """
    # 1. Validation (Same as before)
    spec = crud.get_meeting_specification(db, meeting_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.github_token:
        raise HTTPException(status_code=400, detail="User not authenticated with GitHub")

    token = decrypt_value(user.github_token)
    project = crud.get_project(db, spec.project_id)

    try:
        parts = project.github_repo_url.strip("/").split("/")
        owner, repo = parts[-2], parts[-1]
    except:
        raise HTTPException(status_code=400, detail="Invalid GitHub Repo URL")

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # 2. Define Async Worker for a single task
    async def create_issue(client, task_data):
        issue_body = {
            "title": task_data.title,
            "body": f"{task_data.description}\n\n*Generated by Voice Meeting Spec Generator*"
        }
        try:
            res = await client.post(
                f"https://api.github.com/repos/{owner}/{repo}/issues", 
                json=issue_body, 
                headers=headers
            )
            if res.status_code == 201:
                gh_data = res.json()
                return {
                    "success": True,
                    "title": task_data.title,
                    "github_number": gh_data.get("number"),
                    "url": gh_data.get("html_url"),
                    "task_data": task_data # Return original data to save to DB
                }
            else:
                return {"success": False, "title": task_data.title, "error": f"HTTP {res.status_code}"}
        except Exception as e:
            return {"success": False, "title": task_data.title, "error": str(e)}

    # 3. Run all requests in parallel
    async with httpx.AsyncClient() as client:
        # Create a list of coroutines
        coroutines = [create_issue(client, task) for task in tasks]
        # execute them
        results_list = await asyncio.gather(*coroutines)

    # 4. Process results and Save to DB (Sync DB operations)
    final_results = []
    success_count = 0

    for res in results_list:
        if res["success"]:
            # DB Write
            db_task = schemas.TaskCreate(
                specification_id=spec.id,
                title=res["task_data"].title,
                description=res["task_data"].description,
                github_issue_number=res["github_number"]
            )
            crud.create_task(db, db_task)
            success_count += 1
            final_results.append({"title": res["title"], "status": "created", "issue_url": res["url"]})
        else:
            final_results.append({"title": res["title"], "status": "failed", "error": res["error"]})

    return {
        "summary": f"{success_count}/{len(tasks)} Created",
        "results": final_results
    }

@app.get("/user/repos")
def read_user_repos(user_id: int, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.github_token:
        raise HTTPException(status_code=401, detail="User not authorised with GitHub")

    decrypted_token = decrypt_value(user.github_token)

    headers = {
        "Authorization": f"token {decrypted_token}",
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
    
    # Use the global pool to create a client
    r = redis_async.Redis(connection_pool=redis_pool)
    pubsub = r.pubsub()
    
    channel_name = f"meeting_{meeting_id}_updates"
    await pubsub.subscribe(channel_name)
    
    print(f"🟢 WS Connected: {channel_name}")

    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                data = message['data'].decode('utf-8')
                await websocket.send_text(data)
            await asyncio.sleep(0.01)
            
    except WebSocketDisconnect:
        print(f"⚪ WS Disconnected: {channel_name}")
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
    redis_client.set(f"stop_meeting_{meeting_id}", "true")
    
    # 2. Trigger Celery Task
    generate_specification_task.delay(meeting.id, meeting.project_id)

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