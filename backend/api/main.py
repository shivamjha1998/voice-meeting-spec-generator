import os
import httpx
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List
from dotenv import load_dotenv

from backend.common import models, database
from backend.api import schemas, crud

load_dotenv()

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL", "http://localhost:8000/auth/github/callback")

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Voice Meeting Spec Generator API")

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
        
        # GitHub doesn't always return email in the public profile, fetch it explicitly
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
        # Update token if user exists
        db_user = crud.update_user_token(db, existing_user.id, access_token)
    else:
        # Create new user
        new_user = schemas.UserCreate(
            email=user_email,
            username=user_data.get("login"),
            avatar_url=user_data.get("avatar_url"),
            github_token=access_token
        )
        db_user = crud.create_user(db, new_user)

    # 4. Redirect to Frontend (Dashboard) with a session/cookie
    # For simplicity, we are passing the user_id in the URL, but in production, 
    # you should use JWT or Session Cookies.
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
