from typing import Optional
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai

from app.config import settings
from app.database import Base, engine
from app.routers import analysis, health, jobs, resumes
from app.agent.prompts import SYSTEM_PROMPT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create tables on startup if they do not already exist in Neon DB
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema initialized successfully.")
    except Exception as exc:
        logger.warning("Could not auto-create tables on startup (DB offline/DNS issue): %s", exc)
    yield

app = FastAPI(
    title="AI Job Application Intelligence Agent API",
    description="Backend API for analyzing resumes against job descriptions",
    version="1.0.0",
    lifespan=lifespan,
)

# Basic CORS configuration for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(analysis.router)
app.include_router(resumes.router)
app.include_router(jobs.router)

@app.get("/")
def root(question: Optional[str] = None):
    """
    Root endpoint: If a question is provided (?question=...), it queries Gemini and returns the answer.
    Otherwise, returns API status and usage information.
    """
    if not question:
        return {
            "message": "AI Job Application Intelligence Agent API is running",
            "usage": "Pass ?question=<your_question> to ask Gemini (e.g., /?question=What+is+Python)",
            "docs_url": "/docs",
            "health_check": "/health",
            "model": settings.GEMINI_MODEL,
        }

    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is not configured in backend/.env"
        )

    logger.info("Incoming question: %s", question)

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.interactions.create(
            model=settings.GEMINI_MODEL,
            input=question,
            system_instruction=SYSTEM_PROMPT,
        )
        answer = getattr(response, "output_text", None) or "No text response returned."
        logger.info("GEMINI ANSWER: %s", answer)
        return {
            "question": question,
            "answer": answer,
            "model": settings.GEMINI_MODEL,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Gemini API error: {str(exc)}"
        )

