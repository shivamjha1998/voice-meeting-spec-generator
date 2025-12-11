from sqlalchemy.orm import Session
from backend.common import models
from . import schemas

def get_project(db: Session, project_id: int):
    return db.query(models.Project).filter(models.Project.id == project_id).first()

def get_projects(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Project).offset(skip).limit(limit).all()

def create_project(db: Session, project: schemas.ProjectCreate):
    db_project = models.Project(**project.dict())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

def delete_project(db: Session, project_id: int):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if db_project:
        db.delete(db_project)
        db.commit()
    return db_project

def create_meeting(db: Session, meeting: schemas.MeetingCreate):
    db_meeting = models.Meeting(**meeting.dict())
    db.add(db_meeting)
    db.commit()
    db.refresh(db_meeting)
    return db_meeting

def get_meetings(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Meeting).offset(skip).limit(limit).all()

def get_meeting(db: Session, meeting_id: int):
    return db.query(models.Meeting).filter(models.Meeting.id == meeting_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        email=user.email,
        username=user.username,
        avatar_url=user.avatar_url,
        github_token=user.github_token
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_token(db: Session, user_id: int, new_token: str):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.github_token = new_token
        db.commit()
        db.refresh(user)
    return user

def get_meeting_transcripts(db: Session, meeting_id: int):
    return db.query(models.Transcript).filter(models.Transcript.meeting_id == meeting_id).order_by(models.Transcript.timestamp).all()

def get_meeting_specification(db: Session, meeting_id: int):
    return db.query(models.Specification).filter(models.Specification.meeting_id == meeting_id).order_by(models.Specification.created_at.desc()).first()

