"""Unit tests for deterministic scoring, evidence verification, and edge cases."""

from pathlib import Path
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.agent.tools import (
    calculate_deterministic_score,
    validate_evidence_in_resume,
    verify_and_adjust_skills,
)
from app.schemas import SkillItem


def test_calculate_score_all_matched():
    skills = [
        SkillItem(skill_name="Python", category="REQUIRED", is_matched=True, resume_evidence="Python"),
        SkillItem(skill_name="FastAPI", category="REQUIRED", is_matched=True, resume_evidence="FastAPI"),
        SkillItem(skill_name="Docker", category="PREFERRED", is_matched=True, resume_evidence="Docker"),
    ]
    score, is_reliable = calculate_deterministic_score(skills)
    assert score == 100.0
    assert is_reliable is True


def test_calculate_score_none_matched():
    skills = [
        SkillItem(skill_name="Python", category="REQUIRED", is_matched=False, resume_evidence=None),
        SkillItem(skill_name="PostgreSQL", category="REQUIRED", is_matched=False, resume_evidence=None),
        SkillItem(skill_name="Docker", category="PREFERRED", is_matched=False, resume_evidence=None),
    ]
    score, is_reliable = calculate_deterministic_score(skills)
    assert score == 0.0
    assert is_reliable is True


def test_calculate_score_partial_required_and_preferred():
    # 3 of 4 required matched = 75% base score (weight 0.8 -> 60.0)
    # 1 of 2 preferred matched = 50% bonus score (weight 0.2 -> 10.0)
    # Total = 70.0
    skills = [
        SkillItem(skill_name="Python", category="REQUIRED", is_matched=True),
        SkillItem(skill_name="SQL", category="REQUIRED", is_matched=True),
        SkillItem(skill_name="Git", category="REQUIRED", is_matched=True),
        SkillItem(skill_name="Kubernetes", category="REQUIRED", is_matched=False),
        SkillItem(skill_name="AWS", category="PREFERRED", is_matched=True),
        SkillItem(skill_name="GCP", category="PREFERRED", is_matched=False),
    ]
    score, is_reliable = calculate_deterministic_score(skills)
    assert score == 70.0
    assert is_reliable is True


def test_calculate_score_only_required_skills():
    # 2 of 3 required matched = 66.666...% -> rounded to 66.7
    skills = [
        SkillItem(skill_name="Python", category="REQUIRED", is_matched=True),
        SkillItem(skill_name="FastAPI", category="REQUIRED", is_matched=True),
        SkillItem(skill_name="PostgreSQL", category="REQUIRED", is_matched=False),
    ]
    score, is_reliable = calculate_deterministic_score(skills)
    assert score == 66.7
    assert is_reliable is True


def test_calculate_score_no_required_skills_flagged_unreliable():
    # Only preferred skills present -> unreliable, defaults to 0.0
    skills = [
        SkillItem(skill_name="Docker", category="PREFERRED", is_matched=True),
        SkillItem(skill_name="Kubernetes", category="PREFERRED", is_matched=True),
    ]
    score, is_reliable = calculate_deterministic_score(skills)
    assert score == 0.0
    assert is_reliable is False


def test_validate_evidence_in_resume():
    resume = "Senior Python engineer with 5 years building scalable FastAPI microservices."

    # Direct match
    assert validate_evidence_in_resume("scalable FastAPI microservices", resume) is True
    # Case insensitive
    assert validate_evidence_in_resume("SCALABLE FASTAPI MICROSERVICES", resume) is True
    # Whitespace normalization (newlines/extra spaces)
    assert validate_evidence_in_resume("scalable   FastAPI\n microservices", resume) is True
    # Non-existent quote (hallucination)
    assert validate_evidence_in_resume("10 years of Kubernetes experience", resume) is False
    # Empty evidence
    assert validate_evidence_in_resume("", resume) is False
    assert validate_evidence_in_resume(None, resume) is False


def test_verify_and_adjust_skills_downgrades_hallucinated_evidence():
    resume = "Full-stack developer experienced with React and Node.js."

    skills = [
        SkillItem(
            skill_name="React",
            category="REQUIRED",
            is_matched=True,
            resume_evidence="experienced with React",
        ),
        SkillItem(
            skill_name="Docker",
            category="REQUIRED",
            is_matched=True,
            resume_evidence="orchestrated Docker containers in production",  # not in resume!
        ),
        SkillItem(
            skill_name="Kubernetes",
            category="PREFERRED",
            is_matched=True,
            resume_evidence=None,  # claimed matched without evidence!
        ),
    ]

    verified = verify_and_adjust_skills(skills, resume)

    # React remains matched with evidence intact
    assert verified[0].skill_name == "React"
    assert verified[0].is_matched is True
    assert verified[0].resume_evidence == "experienced with React"

    # Docker is downgraded because evidence was hallucinated
    assert verified[1].skill_name == "Docker"
    assert verified[1].is_matched is False
    assert verified[1].resume_evidence is None

    # Kubernetes is downgraded because evidence was missing
    assert verified[2].skill_name == "Kubernetes"
    assert verified[2].is_matched is False
    assert verified[2].resume_evidence is None


if __name__ == "__main__":
    test_calculate_score_all_matched()
    test_calculate_score_none_matched()
    test_calculate_score_partial_required_and_preferred()
    test_calculate_score_only_required_skills()
    test_calculate_score_no_required_skills_flagged_unreliable()
    test_validate_evidence_in_resume()
    test_verify_and_adjust_skills_downgrades_hallucinated_evidence()
    print("All 7 tests passed successfully!")

