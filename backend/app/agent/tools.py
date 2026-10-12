"""Deterministic tools for skill validation and scoring in the AI Job Application Intelligence Agent."""

import re
from typing import List, Optional, Tuple
from app.schemas import SkillItem


def normalize_text(text: str) -> str:
    """Normalizes whitespace and converts text to lowercase for robust fuzzy substring checks."""
    return re.sub(r"\s+", " ", text).strip().lower()


def validate_evidence_in_resume(evidence: Optional[str], resume_text: str) -> bool:
    """
    Validates whether the claimed evidence quote genuinely appears in the resume text.
    Returns True only if evidence is non-empty and a normalized substring match is found.
    """
    if not evidence or not evidence.strip():
        return False
    norm_evidence = normalize_text(evidence)
    norm_resume = normalize_text(resume_text)
    return norm_evidence in norm_resume


def verify_and_adjust_skills(
    skills: List[SkillItem],
    resume_text: str
) -> List[SkillItem]:
    """
    Enforces evidence integrity:
    If a skill is marked as matched (is_matched == True), its evidence MUST be confirmed
    to exist in the resume text. If evidence is missing or hallucinated, is_matched is
    downgraded to False and evidence is cleared.
    """
    verified_skills: List[SkillItem] = []

    for skill in skills:
        category = skill.category.upper() if skill.category else "REQUIRED"
        if category not in ("REQUIRED", "PREFERRED"):
            category = "REQUIRED"

        is_matched = skill.is_matched
        evidence = skill.resume_evidence

        if is_matched:
            if not validate_evidence_in_resume(evidence, resume_text):
                # Downgrade: evidence not verified in original resume
                is_matched = False
                evidence = None
        else:
            evidence = None

        verified_skills.append(
            SkillItem(
                skill_name=skill.skill_name.strip(),
                category=category,
                is_matched=is_matched,
                resume_evidence=evidence,
            )
        )

    return verified_skills


def calculate_deterministic_score(skills: List[SkillItem]) -> Tuple[float, bool]:
    """
    Calculates the candidate match score deterministically using Python code.

    Scoring Rules:
    - Base Score = (Matched Required / Total Required) * 100
    - Bonus Score = (Matched Preferred / Total Preferred) * 100
    - If both Required and Preferred skills exist:
        Final Score = round((Base Score * 0.8) + (Bonus Score * 0.2), 1)
    - If only Required skills exist:
        Final Score = round(Base Score, 1)
    - If no Required skills are identified:
        Final Score = 0.0, is_reliable = False (insufficient requirements for reliable scoring)

    Returns:
        (final_score: float, is_reliable: bool)
    """
    required_skills = [s for s in skills if s.category == "REQUIRED"]
    preferred_skills = [s for s in skills if s.category == "PREFERRED"]

    if not required_skills:
        return 0.0, False

    matched_required = sum(1 for s in required_skills if s.is_matched)
    base_score = (matched_required / len(required_skills)) * 100.0

    if not preferred_skills:
        return round(base_score, 1), True

    matched_preferred = sum(1 for s in preferred_skills if s.is_matched)
    bonus_score = (matched_preferred / len(preferred_skills)) * 100.0

    final_score = (base_score * 0.8) + (bonus_score * 0.2)
    return round(final_score, 1), True
