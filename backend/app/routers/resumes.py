"""Router for resume upload and text extraction endpoints."""

import logging
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.schemas import ResumeExtractResponse
from app.services.resume_parser import ResumeParseError, parse_resume_upload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/resumes", tags=["Resumes"])


@router.post(
    "/upload",
    response_model=ResumeExtractResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and extract text from PDF or DOCX resume",
)
async def upload_resume(file: UploadFile = File(...)):
    """
    Accepts PDF or DOCX resume file, verifies magic bytes and a 5 MB stream limit,
    extracts readable text in memory, and validates length bounds (20 to 50,000 characters).
    Does NOT save files permanently or store text in the database.
    """
    try:
        clean_text, char_count = await parse_resume_upload(file)
        return ResumeExtractResponse(
            filename=file.filename or "uploaded_resume",
            extracted_text=clean_text,
            character_count=char_count,
        )
    except ResumeParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Unexpected error during resume upload processing: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process the uploaded resume file.",
        )
