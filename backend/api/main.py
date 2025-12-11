import os
import httpx
import json
import redis
import requests
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

from backend.common import models, database
from backend.api import schemas, crud
from backend.ai.llm_client import LLMClient

load_dotenv()

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL", "http://localhost:8000/auth/github/callback")

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Voice Meeting Spec Generator API")

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
    """Redirects the user to GitHub to authorize the app."""
    return RedirectResponse(
        f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=repo,user:email"
    )

@app.get("/auth/github/callback")
async def github_callback(code: str, db: Session = Depends(database.get_db)):
    """Handles the callback from GitHub, swaps code for token, and creates user."""
    
    # 1. Exchange code for access token
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

    # 2. Fetch User Info using the token
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

    # 3. Create or Update User in DB
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

    # 4. Redirect to Frontend (Dashboard) with a session/cookie
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
    projects = crud.get_projects(db, skip=skip, limit=limit)
    return projects

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
    meetings = crud.get_meetings(db, skip=skip, limit=limit)
    return meetings

@app.get("/meetings/{meeting_id}", response_model=schemas.Meeting)
def read_meeting(meeting_id: int, db: Session = Depends(database.get_db)):
    db_meeting = crud.get_meeting(db, meeting_id=meeting_id)
    if db_meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return db_meeting

@app.get("/meetings/{meeting_id}/transcripts", response_model=List[schemas.Transcript])
def read_meeting_transcripts(meeting_id: int, db: Session = Depends(database.get_db)):
    transcripts = crud.get_meeting_transcripts(db, meeting_id=meeting_id)
    return transcripts

# Get Specification for a Meeting
@app.post("/meetings/{meeting_id}/generate")
def generate_specification(meeting_id: int, db: Session = Depends(database.get_db)):
    """Triggers the AI Service to generate a spec for the given meeting."""
    # 1. Check if meeting exists
    meeting = crud.get_meeting(db, meeting_id=meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # 2. Push job to Redis Queue
    try:
        redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        job_data = {"meeting_id": meeting.id, "project_id": meeting.project_id}
        redis_client.rpush("spec_generation_queue", json.dumps(job_data))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue task: {str(e)}")

    return {"status": "queued", "message": "Specification generation started"}

@app.get("/meetings/{meeting_id}/specification", response_model=schemas.Specification)
def read_meeting_specification(meeting_id: int, db: Session = Depends(database.get_db)):
    spec = crud.get_meeting_specification(db, meeting_id=meeting_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found (or still generating)")
    return spec

@app.post("/meetings/{meeting_id}/create-issues")
def create_github_issues(meeting_id: int, db: Session = Depends(database.get_db), user_id: int = 1):
    """Extracts tasks from spec and creates GitHub Issues."""
    # 1. Get the Spec
    spec = crud.get_meeting_specification(db, meeting_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found")

    # 2. Get User for GitHub Token
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
        
    if not user.github_token:
        raise HTTPException(status_code=400, detail="User not authenticated with GitHub")

    # 3. Extract Tasks using AI
    try:
        llm = LLMClient()
        tasks_json = llm.extract_tasks(spec.content)
        tasks_data = json.loads(tasks_json).get("tasks", [])
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"AI Task Extraction failed: {str(e)}")

    # 4. Create Issues on GitHub
    created_issues = []
    
    # Retrieve Project to get Repo URL
    project = crud.get_project(db, spec.project_id)
    if not project or not project.github_repo_url:
        raise HTTPException(status_code=400, detail="Project does not have a GitHub Repo URL")

    # Extract owner/repo from URL (Simplistic parsing)
    # URL format: https://github.com/owner/repo
    try:
        parts = project.github_repo_url.strip("/").split("/")
        owner, repo = parts[-2], parts[-1]
    except:
        raise HTTPException(status_code=400, detail="Invalid GitHub Repo URL format")

    headers = {
        "Authorization": f"token {user.github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    errors = []
    for task in tasks_data:
        issue_body = {
            "title": task["title"],
            "body": f"{task['description']}\n\n*Generated by Voice Meeting Spec Generator*"
        }
        res = requests.post(f"https://api.github.com/repos/{owner}/{repo}/issues", json=issue_body, headers=headers)
        if res.status_code == 201:
            created_issues.append(res.json().get("html_url"))
        else:
            errors.append(f"Failed to create '{task['title']}': {res.text}")

    return {"status": "success", "created_issues": created_issues, "errors": errors}

@app.get("/user/repos")
def read_user_repos(user_id: int, db: Session = Depends(database.get_db)):
    """Fetch the list of repositories for the given user"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.github_token:
        raise HTTPException(status_code=401, detail="User not authorised with GitHub")

    headers = {
        "Authorization": f"token {user.github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.get("https://api.github.com/user/repos?sort=updated&per_page=100", headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch repositories from GitHub")

    repos = response.json()

    return [
        {"id": r["id"], "name": r["name"], "full_name": r["full_name"], "html_url": r["html_url"]} 
        for r in repos
    ]
