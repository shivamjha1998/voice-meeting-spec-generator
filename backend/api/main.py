import redis.asyncio as redis_async
import asyncio
import os
import httpx
import json
import redis
import requests
import uuid
from fastapi import FastAPI, Depends, HTTPException, Body, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel

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
# Added validate_token
from backend.api.auth import create_access_token, get_current_user, validate_token

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
    
    gh_access_token = token_data["access_token"]

    async with httpx.AsyncClient() as client:
        user_res = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {gh_access_token}"}
        )
        user_data = user_res.json()
        
        email_res = await client.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"Bearer {gh_access_token}"}
        )
        emails = email_res.json()
        primary_email = next((e["email"] for e in emails if e["primary"]), None)

    user_email = primary_email or user_data.get("email")
    if not user_email:
        raise HTTPException(status_code=400, detail="Could not retrieve email from GitHub")

    existing_user = crud.get_user_by_email(db, email=user_email)
    
    if existing_user:
        db_user = crud.update_user_token(db, existing_user.id, gh_access_token)
    else:
        new_user = schemas.UserCreate(
            email=user_email,
            username=user_data.get("login"),
            avatar_url=user_data.get("avatar_url"),
            github_token=gh_access_token
        )
        db_user = crud.create_user(db, new_user)

    # Generate JWT
    jwt_token = create_access_token(data={"sub": str(db_user.id)})

    # SECURITY FIX: Do not send token in URL. Use a short-lived code exchange.
    auth_code = str(uuid.uuid4())
    
    # Store JWT in Redis with 60s expiration
    r = redis_async.Redis(connection_pool=redis_pool)
    await r.setex(f"auth_code:{auth_code}", 60, jwt_token)
    await r.close()

    return RedirectResponse(f"http://localhost:5173/auth/success?code={auth_code}")

class TokenExchangeRequest(BaseModel):
    code: str

@app.post("/auth/exchange")
async def exchange_token(request: TokenExchangeRequest):
    """Exchanges a short-lived auth code for a JWT."""
    r = redis_async.Redis(connection_pool=redis_pool)
    
    # Retrieve token
    token_bytes = await r.get(f"auth_code:{request.code}")
    
    if not token_bytes:
        await r.close()
        raise HTTPException(status_code=400, detail="Invalid or expired authentication code")
    
    # Delete code (One-time use)
    await r.delete(f"auth_code:{request.code}")
    await r.close()
    
    return {"access_token": token_bytes.decode("utf-8")}

@app.get("/health")
def health_check():
    return {"status": "ok"}

# --- Project Routes (Secured) ---

@app.post("/projects/", response_model=schemas.Project)
def create_project(
    project: schemas.ProjectCreate, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.create_project(db=db, project=project, user_id=current_user.id)

@app.get("/projects/", response_model=List[schemas.Project])
def read_projects(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.get_projects(db, skip=skip, limit=limit, user_id=current_user.id)

@app.get("/projects/{project_id}", response_model=schemas.Project)
def read_project(
    project_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_project = crud.get_project(db, project_id=project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if db_project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this project")
        
    return db_project

@app.delete("/projects/{project_id}", response_model=schemas.Project)
def delete_project(
    project_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_project = crud.get_project(db, project_id=project_id)
    if db_project and db_project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this project")

    db_project = crud.delete_project(db, project_id=project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project

# --- Meeting Routes (Secured) ---

@app.post("/meetings/", response_model=schemas.Meeting)
def create_meeting(
    meeting: schemas.MeetingCreate, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    project = crud.get_project(db, project_id=meeting.project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to add meetings to this project")

    return crud.create_meeting(db=db, meeting=meeting)

@app.get("/meetings/", response_model=List[schemas.Meeting])
def read_meetings(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.get_meetings(db, skip=skip, limit=limit, user_id=current_user.id)

@app.get("/meetings/{meeting_id}", response_model=schemas.Meeting)
def read_meeting(
    meeting_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    meeting = crud.get_meeting(db, meeting_id=meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    if meeting.project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this meeting")
        
    return meeting

@app.get("/meetings/{meeting_id}/transcripts", response_model=List[schemas.Transcript])
def read_meeting_transcripts(
    meeting_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    meeting = crud.get_meeting(db, meeting_id=meeting_id)
    if not meeting or meeting.project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return crud.get_meeting_transcripts(db, meeting_id=meeting_id)

@app.post("/meetings/{meeting_id}/generate")
def generate_specification(
    meeting_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    meeting = crud.get_meeting(db, meeting_id=meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if meeting.project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    generate_specification_task.delay(meeting.id, meeting.project_id)

    return {"status": "queued", "message": "Specification generation started"}

@app.post("/meetings/{meeting_id}/join")
def join_meeting(
    meeting_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    meeting = crud.get_meeting(db, meeting_id=meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if meeting.project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
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
def read_meeting_specification(
    meeting_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    meeting = crud.get_meeting(db, meeting_id=meeting_id)
    if not meeting or meeting.project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    spec = crud.get_meeting_specification(db, meeting_id=meeting_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found")
    return spec

@app.put("/meetings/{meeting_id}/specification", response_model=schemas.Specification)
def update_meeting_specification(
    meeting_id: int, 
    spec_update: schemas.SpecificationUpdate, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    meeting = crud.get_meeting(db, meeting_id=meeting_id)
    if not meeting or meeting.project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    existing_spec = crud.get_meeting_specification(db, meeting_id)
    if not existing_spec:
        raise HTTPException(status_code=404, detail="Specification not found")
        
    updated_spec = crud.update_specification(db, meeting_id, spec_update.content)
    return updated_spec

@app.get("/meetings/{meeting_id}/tasks/preview")
def preview_tasks(
    meeting_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    meeting = crud.get_meeting(db, meeting_id=meeting_id)
    if not meeting or meeting.project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

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
    current_user: models.User = Depends(get_current_user)
):
    meeting = crud.get_meeting(db, meeting_id=meeting_id)
    if not meeting or meeting.project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    spec = crud.get_meeting_specification(db, meeting_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found")

    if not current_user.github_token:
        raise HTTPException(status_code=400, detail="User not authenticated with GitHub")

    token = decrypt_value(current_user.github_token)
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
                    "task_data": task_data
                }
            else:
                return {"success": False, "title": task_data.title, "error": f"HTTP {res.status_code}"}
        except Exception as e:
            return {"success": False, "title": task_data.title, "error": str(e)}

    async with httpx.AsyncClient() as client:
        coroutines = [create_issue(client, task) for task in tasks]
        results_list = await asyncio.gather(*coroutines)

    final_results = []
    success_count = 0

    for res in results_list:
        if res["success"]:
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
def read_user_repos(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not current_user.github_token:
        raise HTTPException(status_code=401, detail="User not authorised with GitHub")

    decrypted_token = decrypt_value(current_user.github_token)

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

# SECURITY FIX: Added token authentication to WebSocket
@app.websocket("/ws/meetings/{meeting_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    meeting_id: int, 
    token: str = Query(..., description="JWT Access Token"),
    db: Session = Depends(database.get_db)
):
    # 1. Authenticate
    user = validate_token(token, db)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid Token")
        return

    # 2. Authorize (Check project ownership)
    meeting = crud.get_meeting(db, meeting_id)
    if not meeting or meeting.project.owner_id != user.id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        return

    await websocket.accept()
    
    r = redis_async.Redis(connection_pool=redis_pool)
    pubsub = r.pubsub()
    
    channel_name = f"meeting_{meeting_id}_updates"
    await pubsub.subscribe(channel_name)
    
    print(f"🟢 WS Connected: {channel_name} (User: {user.email})")

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
def end_meeting(
    meeting_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    meeting = crud.get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if meeting.project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    meeting.ended_at = datetime.utcnow()
    db.commit()
    
    redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    redis_client.set(f"stop_meeting_{meeting_id}", "true")
    
    generate_specification_task.delay(meeting.id, meeting.project_id)

    return {"status": "success", "message": "Meeting ended, bot stopped, spec generation started."}

@app.get("/settings/", response_model=List[schemas.Setting])
def read_settings(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    settings = crud.get_settings(db)
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
def update_setting(
    key: str, 
    setting: schemas.SettingCreate, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    if key != setting.key:
         raise HTTPException(status_code=400, detail="Key mismatch")
    return crud.update_setting(db, setting)