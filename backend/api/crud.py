from sqlalchemy.orm import Session
from datetime import datetime
from backend.common import models
from backend.common.security import encrypt_value
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
    # Encrypt the token before creating the model
    encrypted_token = encrypt_value(user.github_token)
    # Create the user
    db_user = models.User(
        email=user.email,
        username=user.username,
        avatar_url=user.avatar_url,
        github_token=encrypted_token
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_token(db: Session, user_id: int, new_token: str):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        # Encrypt the new token before updating
        user.github_token = encrypt_value(new_token)
        db.commit()
        db.refresh(user)
    return user

def get_meeting_transcripts(db: Session, meeting_id: int):
    return db.query(models.Transcript).filter(models.Transcript.meeting_id == meeting_id).order_by(models.Transcript.timestamp).all()

def get_meeting_specification(db: Session, meeting_id: int):
    return db.query(models.Specification).filter(models.Specification.meeting_id == meeting_id).order_by(models.Specification.created_at.desc()).first()

def update_specification(db: Session, meeting_id: int, content: str):
    spec = get_meeting_specification(db, meeting_id)
    if spec:
        spec.content = content
        spec.created_at = datetime.utcnow()
        db.commit()
        db.refresh(spec)
    return spec

def create_task(db: Session, task: schemas.TaskCreate):
    db_task = models.Task(**task.dict())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_setting(db: Session, key: str):
    return db.query(models.Setting).filter(models.Setting.key == key).first()

def get_settings(db: Session):
    return db.query(models.Setting).all()

def update_setting(db: Session, setting: schemas.SettingCreate):
    db_setting = db.query(models.Setting).filter(models.Setting.key == setting.key).first()
    if db_setting:
        db_setting.value = setting.value
        db.commit()
        db.refresh(db_setting)
        return db_setting
    else:
        db_setting = models.Setting(**setting.dict())
        db.add(db_setting)
        db.commit()
        db.refresh(db_setting)
        return db_setting

def create_audio_file(db: Session, audio_file: schemas.AudioFileCreate):
    db_audio = models.AudioFile(**audio_file.dict())
    db.add(db_audio)
    db.commit()
    db.refresh(db_audio)
    return db_audio
