"""Single-agent orchestrator for analyzing resumes against job descriptions."""

import json
import logging
import re
from typing import Any, Dict

from app.agent.client import get_genai_client
from app.agent.prompts import SYSTEM_PROMPT, build_analysis_prompt
from app.agent.tools import calculate_deterministic_score, verify_and_adjust_skills
from app.config import settings
from app.schemas import AgentAnalysisOutput

logger = logging.getLogger(__name__)


class AgentAnalysisError(Exception):
    """Raised when the AI analysis pipeline fails."""
    pass


def _clean_json_text(raw_text: str) -> str:
    """Strips markdown code fence wrappers (```json ... ```) if returned by the LLM."""
    cleaned = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return cleaned


def analyze_application(resume_text: str, job_description: str) -> Dict[str, Any]:
    """
    Executes the single-agent analysis workflow:
    1. Sends untrusted resume and job description to Gemini using configured settings.
    2. Enforces structured JSON output.
    3. Validates evidence against the actual resume text (Python).
    4. Computes deterministic score using verified metrics (Python).

    Returns:
        dict with total_score, skills (list of SkillItem), and suggestions.
    """
    client = get_genai_client()
    prompt = build_analysis_prompt(
        resume_text=resume_text,
        job_description=job_description,
    )

    try:
        response = client.interactions.create(
            model=settings.GEMINI_MODEL,
            input=prompt,
            system_instruction=SYSTEM_PROMPT,
        )
    except Exception as exc:
        logger.error("Gemini Interactions API request failed: %s", type(exc).__name__)
        raise AgentAnalysisError("AI service unavailable. Please try again later.") from exc

    raw_output = getattr(response, "output_text", None)
    if not raw_output:
        logger.error("Gemini returned empty or non-text response.")
        raise AgentAnalysisError("Empty response received from analysis model.")

    try:
        cleaned_json = _clean_json_text(raw_output)
        data = json.loads(cleaned_json)
        parsed_output = AgentAnalysisOutput.model_validate(data)
    except Exception as exc:
        logger.error("Failed to parse and validate AI response JSON: %s", type(exc).__name__)
        raise AgentAnalysisError("Model output format was invalid.") from exc

    # 1. Enforce evidence verification in Python (no hallucinations)
    verified_skills = verify_and_adjust_skills(
        skills=parsed_output.skills,
        resume_text=resume_text,
    )

    # 2. Deterministic scoring in Python
    score, is_reliable = calculate_deterministic_score(verified_skills)

    suggestions = parsed_output.suggestions.strip()
    if not is_reliable:
        suggestions = (
            "[Notice: Insufficient required skills identified in the job description "
            "for reliable deterministic scoring. Score defaulted to 0.0.]\n\n"
            + suggestions
        )

    return {
        "total_score": score,
        "skills": verified_skills,
        "suggestions": suggestions,
    }
