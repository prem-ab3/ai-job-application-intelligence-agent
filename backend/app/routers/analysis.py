"""Router for job application analysis endpoints."""

import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agent.orchestrator import analyze_application
from app.database import get_db
from app.models import AnalysisJob, ExtractedSkill
from app.schemas import AnalysisJobCreate, AnalysisJobResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Analysis"])


@router.post("/analyze", response_model=AnalysisJobResponse, status_code=status.HTTP_201_CREATED)
def create_analysis(
    payload: AnalysisJobCreate,
    db: Session = Depends(get_db),
):
    """
    Analyzes a candidate's resume against a job description.
    1. Creates a pending analysis job record in Neon PostgreSQL.
    2. Invokes the AI Job Application Intelligence Agent with deterministic verification.
    3. Persists extracted skills, evidence, deterministic score, and suggestions.
    4. Safely rolls back and marks status as ERROR upon any failure.
    """
    job = AnalysisJob(
        resume_text=payload.resume_text,
        job_description=payload.job_description,
        status="PENDING",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        result = analyze_application(
            resume_text=payload.resume_text,
            job_description=payload.job_description,
        )

        for skill in result["skills"]:
            skill_record = ExtractedSkill(
                analysis_job_id=job.id,
                skill_name=skill.skill_name,
                category=skill.category,
                is_matched=skill.is_matched,
                resume_evidence=skill.resume_evidence,
            )
            db.add(skill_record)

        job.total_score = result["total_score"]
        job.suggestions = result["suggestions"]
        job.status = "COMPLETED"

        db.commit()
        db.refresh(job)
        return job

    except Exception as exc:
        db.rollback()

        # Update the job record to ERROR state in a clean transaction
        try:
            job.status = "ERROR"
            job.suggestions = "Analysis could not be completed at this time."
            db.commit()
        except Exception:
            db.rollback()

        logger.error("Analysis failed for job %s: %s", job.id, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis failed to complete. Please try again later.",
        )


@router.get("/analysis/{job_id}", response_model=AnalysisJobResponse)
def get_analysis(
    job_id: UUID,
    db: Session = Depends(get_db),
):
    """Retrieves an existing analysis job and its extracted skills by UUID."""
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis job not found.",
        )
    return job
