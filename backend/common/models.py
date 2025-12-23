from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base

class MeetingPlatform(str, enum.Enum):
    ZOOM = "zoom"
    GOOGLE_MEET = "google_meet"

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    github_repo_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    meetings = relationship("Meeting", back_populates="project")
    specifications = relationship("Specification", back_populates="project")

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    platform = Column(Enum(MeetingPlatform))
    meeting_url = Column(String)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="meetings")
    transcripts = relationship("Transcript", back_populates="meeting")
    specifications = relationship("Specification", back_populates="meeting")

class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"))
    speaker = Column(String)
    text = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    meeting = relationship("Meeting", back_populates="transcripts")

class Specification(Base):
    __tablename__ = "specifications"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=True)
    content = Column(Text)
    version = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="specifications")
    meeting = relationship("Meeting", back_populates="specifications")
    tasks = relationship("Task", back_populates="specification")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    specification_id = Column(Integer, ForeignKey("specifications.id"))
    title = Column(String)
    description = Column(Text, nullable=True)
    github_issue_number = Column(Integer, nullable=True)

    specification = relationship("Specification", back_populates="tasks")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String)
    avatar_url = Column(String)
    github_token = Column(String) #In prod, encrypt this!
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=False)
    description = Column(String, nullable=True)

class AudioFile(Base):
    __tablename__ = "audio_files"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"))
    file_path = Column(String)
    duration = Column(Integer, nullable=True) # Duration in seconds
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    meeting = relationship("Meeting")
