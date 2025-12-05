from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    github_repo_url: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class MeetingBase(BaseModel):
    meeting_url: str
    platform: str

class MeetingCreate(MeetingBase):
    project_id: int

class Meeting(MeetingBase):
    id: int
    project_id: int
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    email: str
    username: str | None = None
    avatar_url: str | None = None

class UserCreate(UserBase):
    github_token: str

class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class TranscriptBase(BaseModel):
    speaker: str
    text: str

class TranscriptCreate(TranscriptBase):
    meeting_id: int

class Transcript(TranscriptBase):
    id: int
    meeting_id: int
    timestamp: datetime

    class Config:
        from_attributes = True

class SpecificationBase(BaseModel):
    content: str
    version: str = "1.0.0"

class SpecificationCreate(SpecificationBase):
    project_id: int
    meeting_id: int

class Specification(SpecificationBase):
    id: int
    project_id: int
    meeting_id: int
    created_at: datetime

    class Config:
        from_attributes = True