from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    database: str
    message: str


class SkillBase(BaseModel):
    skill_name: str
    category: str
    is_matched: bool
    resume_evidence: Optional[str] = None


class SkillItem(BaseModel):
    skill_name: str
    category: str
    is_matched: bool
    resume_evidence: Optional[str] = None


class SkillResponse(SkillBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)


class AgentAnalysisOutput(BaseModel):
    skills: List[SkillItem]
    suggestions: str


class AnalysisJobCreate(BaseModel):
    resume_text: str = Field(
        ...,
        min_length=20,
        max_length=50000,
        description="Raw text of candidate resume",
    )
    job_description: str = Field(
        ...,
        min_length=20,
        max_length=50000,
        description="Raw text of job description",
    )


class AnalysisJobResponse(BaseModel):
    id: UUID
    status: str
    total_score: Optional[float] = None
    suggestions: Optional[str] = None
    created_at: datetime
    skills: List[SkillResponse] = []

    model_config = ConfigDict(from_attributes=True)
