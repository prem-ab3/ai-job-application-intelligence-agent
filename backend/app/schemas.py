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


class ResumeExtractResponse(BaseModel):
    filename: str
    extracted_text: str
    character_count: int


class JobSearchResultItem(BaseModel):
    id: str
    title: str
    company: str
    location: str
    description_snippet: str
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_period: str = "undisclosed"
    posted_date: Optional[str] = None
    closing_date: Optional[str] = None
    status: str = "UNVERIFIED_SEARCH_INDEX"
    source_name: str = "Adzuna India"
    source_url: str
    direct_apply_url: Optional[str] = None
    is_technical: bool = True
    role_category: str = "TECHNICAL"
    days_ago: Optional[int] = None
    freshness: str = "RECENT"  # "RECENT", "MODERATE", "STALE", "UNKNOWN"
    role_family: str = "SOFTWARE_AI"
    role_relevance: str = "DIRECT_FIT"  # "DIRECT_FIT", "RELATED_TECH", "UNRELATED_ROLE"
    seniority_level: Optional[str] = "MID_LEVEL"  # "ENTRY_JUNIOR", "MID_LEVEL", "SENIOR", "ARCHITECT_LEAD"


class JobSearchResponse(BaseModel):
    total_results: int
    page: int
    results_per_page: int
    jobs: List[JobSearchResultItem]


class JobMatchTarget(BaseModel):
    id: str
    title: str
    company: Optional[str] = "Undisclosed Company"
    location: Optional[str] = "India"
    description: Optional[str] = ""
    source_url: Optional[str] = ""
    is_technical: Optional[bool] = True
    role_category: Optional[str] = "TECHNICAL"
    days_ago: Optional[int] = None
    freshness: Optional[str] = "RECENT"
    role_family: Optional[str] = "SOFTWARE_AI"
    role_relevance: Optional[str] = "DIRECT_FIT"
    seniority_level: Optional[str] = None


class BatchJobMatchRequest(BaseModel):
    resume_text: str = Field(
        ...,
        min_length=20,
        max_length=50000,
        description="Raw text of candidate resume",
    )
    jobs: List[JobMatchTarget] = Field(
        ...,
        min_length=1,
        max_length=25,
        description="List of target jobs to evaluate and rank",
    )


class SkillMatchDetail(BaseModel):
    skill_name: str
    category: str
    is_matched: bool
    resume_evidence: Optional[str] = None
    is_verified_evidence: bool = False


class JobMatchRankedItem(BaseModel):
    job_id: str
    title: str
    company: str
    location: str
    source_url: str
    match_score: Optional[float] = None
    is_reliable: bool
    match_status: str  # "RELIABLE_MATCH", "INSUFFICIENT_DESCRIPTION", "ROLE_MISMATCH", "EVALUATION_FAILED"
    matched_skills: List[SkillMatchDetail] = []
    missing_skills: List[SkillMatchDetail] = []
    suggestions: str
    rank: Optional[int] = None  # Integer rank for reliable jobs; None for unranked
    is_technical: bool = True
    role_category: str = "TECHNICAL"
    days_ago: Optional[int] = None
    freshness: str = "RECENT"
    role_family: str = "SOFTWARE_AI"
    role_relevance: str = "DIRECT_FIT"
    relevance_reason: Optional[str] = None
    match_explanation: Optional[str] = None
    seniority_level: Optional[str] = None
    seniority_alignment: Optional[str] = None




class BatchJobMatchResponse(BaseModel):
    total_jobs: int
    ranked_jobs: List[JobMatchRankedItem] = []
    unranked_jobs: List[JobMatchRankedItem] = []


class SingleJobEvaluationOutput(BaseModel):
    job_id: str
    skills: List[SkillItem] = []
    suggestions: str = ""
    match_explanation: Optional[str] = None


class BatchEvaluationOutput(BaseModel):
    evaluations: List[SingleJobEvaluationOutput] = []
