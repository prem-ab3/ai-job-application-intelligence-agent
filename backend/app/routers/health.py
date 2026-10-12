from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import HealthResponse

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse)
def check_health(db: Session = Depends(get_db)):
    try:
        # Ping the Neon PostgreSQL database
        db.execute(text("SELECT 1"))
        return HealthResponse(
            status="healthy",
            database="connected",
            message="Database connection established successfully with Neon PostgreSQL"
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(exc)}"
        )
