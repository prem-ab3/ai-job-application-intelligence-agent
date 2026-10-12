from google import genai
from app.config import settings


def get_genai_client() -> genai.Client:
    """Returns an authenticated Google GenAI client instance using configured settings."""
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured in backend/.env")
    return genai.Client(api_key=settings.GEMINI_API_KEY)
