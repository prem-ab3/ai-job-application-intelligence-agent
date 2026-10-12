import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_text = Column(Text, nullable=False)
    job_description = Column(Text, nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)
    total_score = Column(Float, nullable=True)
    suggestions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    skills = relationship("ExtractedSkill", back_populates="job", cascade="all, delete-orphan")


class ExtractedSkill(Base):
    __tablename__ = "extracted_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_job_id = Column(UUID(as_uuid=True), ForeignKey("analysis_jobs.id"), nullable=False)
    skill_name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)  # "REQUIRED" or "PREFERRED"
    is_matched = Column(Boolean, default=False, nullable=False)
    resume_evidence = Column(Text, nullable=True)

    job = relationship("AnalysisJob", back_populates="skills")
