"""Jobs router exposing job search endpoints."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.agent.orchestrator import match_multiple_jobs
from app.schemas import (
    BatchJobMatchRequest,
    BatchJobMatchResponse,
    JobSearchResponse,
)
from app.services.adzuna_client import AdzunaClientError, search_adzuna_jobs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs"])


@router.get(
    "/search",
    response_model=JobSearchResponse,
    summary="Search jobs via Adzuna India API",
)
async def search_jobs(
    keywords: Optional[str] = Query(
        None,
        description="Search term or job title (e.g., Python Developer, Data Scientist)",
    ),
    location: Optional[str] = Query(
        None,
        description="Location in India (e.g., Bengaluru, Mumbai, Remote)",
    ),
    page: int = Query(
        1,
        ge=1,
        le=50,
        description="Page number (1-based index)",
    ),
    results_per_page: int = Query(
        10,
        ge=1,
        le=50,
        description="Number of results per page (1 to 50)",
    ),
    sort_by: Optional[str] = Query(
        "date",
        description="Sort order: 'date', 'salary', or 'relevance'",
    ),
    max_days_old: Optional[int] = Query(
        None,
        ge=1,
        le=365,
        description="Maximum age of listings in days",
    ),
) -> JobSearchResponse:
    """
    Search available job postings in India using Adzuna's job search API.
    Results are normalized and unverified; closing dates and direct ATS URLs are not fabricated.
    """
    try:
        results = await search_adzuna_jobs(
            keywords=keywords,
            location=location,
            page=page,
            results_per_page=results_per_page,
            sort_by=sort_by,
            max_days_old=max_days_old,
        )
        return results
    except AdzunaClientError as exc:
        logger.warning("Adzuna client error: %s (status %s)", exc.message, exc.status_code)
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:
        logger.error("Unexpected error in search_jobs endpoint: %s", type(exc).__name__)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while searching for jobs.",
        )


@router.post(
    "/match",
    response_model=BatchJobMatchResponse,
    summary="Match and rank candidate resume against multiple discovered job postings",
)
def match_jobs(
    payload: BatchJobMatchRequest,
) -> BatchJobMatchResponse:
    """
    Evaluates candidate resume against multiple jobs using batch Gemini processing,
    verifies evidence against resume text, calculates deterministic match scores,
    and returns ranked reliable results separated from jobs with insufficient descriptions.
    Does NOT persist to database.
    """
    try:
        response = match_multiple_jobs(
            resume_text=payload.resume_text,
            jobs=payload.jobs,
        )
        return response
    except Exception as exc:
        logger.error("Unexpected error in match_jobs endpoint: %s", type(exc).__name__)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while evaluating job matches.",
        )
