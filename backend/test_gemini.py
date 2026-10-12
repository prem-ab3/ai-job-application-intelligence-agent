from pathlib import Path
import sys

# Ensure the backend directory is in the Python module search path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings


def test_connection():
    if not settings.GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY is not set or empty in backend/.env")
        sys.exit(1)

    try:
        from google import genai

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.interactions.create(
            model=settings.GEMINI_MODEL,
            input="Say 'ping' in one word.",
        )

        if response and (getattr(response, "output_text", None) or getattr(response, "id", None)):
            print("Gemini API connection successful.")
        else:
            print("Gemini API connection succeeded, but no content returned.")

    except Exception as exc:
        print(f"Gemini API connection failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    test_connection()
