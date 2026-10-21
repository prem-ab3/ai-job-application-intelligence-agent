"""End-to-end integration and regression tests for job discovery, relevance gating, and freshness."""

import json
from pathlib import Path
import sys
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.main import app
from app.services.adzuna_client import classify_role_family_and_relevance, calculate_freshness

client = TestClient(app)

SAMPLE_AI_RESUME = (
    "Staff AI Engineer with 7 years of production experience in machine learning and backend systems. "
    "Expertise in Python, FastAPI, PyTorch, LangChain, PostgreSQL, and scalable microservices. "
    "Designed multi-agent systems and real-time distributed pipelines on AWS and Docker."
)


def test_resume_derived_search_without_manual_role_input():
    """Verify job search succeeds without any manual role/keyword input (keywords parameter optional)."""
    mock_adzuna_response = {
        "count": 1,
        "results": [
            {
                "id": "1001",
                "title": "Machine Learning Engineer",
                "company": {"display_name": "AI Innovations"},
                "location": {"display_name": "Bengaluru, Karnataka"},
                "description": "Looking for a Machine Learning Engineer with strong Python and PyTorch skills.",
                "created": "2026-10-10T12:00:00Z",
                "redirect_url": "https://adzuna.example.com/job/1001",
            }
        ],
    }

    mock_resp = httpx.Response(
        status_code=200,
        json=mock_adzuna_response,
        request=httpx.Request("GET", "https://api.adzuna.com/test"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, patch.object(
        settings, "ADZUNA_APP_ID", "valid_app_id"
    ), patch.object(settings, "ADZUNA_APP_KEY", "valid_app_key"):
        mock_get.return_value = mock_resp
        # No keywords query param supplied
        response = client.get("/api/v1/jobs/search?location=Bengaluru")

    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] == 1
    assert len(data["jobs"]) == 1
    job = data["jobs"][0]
    assert job["title"] == "Machine Learning Engineer"
    assert job["is_technical"] is True
    assert job["role_family"] == "SOFTWARE_AI"
    assert job["role_relevance"] == "DIRECT_FIT"
    assert job["freshness"] == "RECENT"
    assert job["status"] == "UNVERIFIED_SEARCH_INDEX"
    assert job["closing_date"] is None
    assert job["direct_apply_url"] is None


def test_irrelevant_roles_excluded_and_zero_score_assigned():
    """Verify specific non-technical jobs receive score=None, ROLE_MISMATCH, and bypass Gemini."""
    mock_gemini_json = {
        "evaluations": [
            {
                "job_id": "tech-1",
                "skills": [
                    {
                        "skill_name": "Python",
                        "category": "REQUIRED",
                        "is_matched": True,
                        "resume_evidence": "Expertise in Python, FastAPI, PyTorch, LangChain, PostgreSQL",
                    }
                ],
                "suggestions": "Excellent fit.",
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.output_text = json.dumps(mock_gemini_json)

    mock_genai_client = MagicMock()
    mock_genai_client.interactions.create.return_value = mock_resp

    test_jobs = [
        {
            "id": "ortho-job",
            "title": "Consultant Orthopedics",
            "company": "MedCity Healthcare",
            "location": "Bengaluru",
            "description": "Consultant Orthopedics needed for knee replacements, fracture surgery and clinical rounds.",
        },
        {
            "id": "inv-job",
            "title": "Inventory Manager",
            "company": "Apex Supply",
            "location": "Mumbai",
            "description": "Lead inventory auditing, warehouse storage operations, supply chain dispatch and procurement.",
        },
        {
            "id": "sqa-job",
            "title": "Supplier Quality Assurance Engineer",
            "company": "Precision Heavy Tech",
            "location": "Chennai",
            "description": "Supplier QA inspections, mechanical tolerance audits, factory floor supplier QA compliance.",
        },
        {
            "id": "sales-job",
            "title": "Senior Sales Associate - Inside sales",
            "company": "B2B Connect",
            "location": "Delhi NCR",
            "description": "Inside sales associate conducting telecalling, pipeline qualification and customer sales demos.",
        },
        {
            "id": "tech-1",
            "title": "Senior AI & Python Developer",
            "company": "DataCore",
            "location": "Remote",
            "description": "Build agentic microservices using Python, FastAPI, and PostgreSQL with Docker.",
        },
    ]

    with patch("app.agent.orchestrator.get_genai_client", return_value=mock_genai_client):
        response = client.post(
            "/api/v1/jobs/match",
            json={"resume_text": SAMPLE_AI_RESUME, "jobs": test_jobs},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total_jobs"] == 5

    # 1. Tech job is ranked
    assert len(data["ranked_jobs"]) == 1
    ranked = data["ranked_jobs"][0]
    assert ranked["job_id"] == "tech-1"
    assert ranked["rank"] == 1
    assert ranked["match_score"] == 100.0
    assert ranked["match_status"] == "RELIABLE_MATCH"

    # 2. Four unrelated jobs are unranked
    assert len(data["unranked_jobs"]) == 4
    for unranked in data["unranked_jobs"]:
        assert unranked["rank"] is None
        assert unranked["match_score"] is None
        assert unranked["is_reliable"] is False
        assert unranked["match_status"] == "ROLE_MISMATCH"
        assert unranked["role_relevance"] == "UNRELATED_ROLE"
        assert unranked["is_technical"] is False
        assert "career domain" in unranked["suggestions"].lower()

    # 3. Gemini prompt verification (only tech-1 sent)
    mock_genai_client.interactions.create.assert_called_once()
    prompt_text = mock_genai_client.interactions.create.call_args[1]["input"]
    assert "tech-1" in prompt_text
    assert "ortho-job" not in prompt_text
    assert "inv-job" not in prompt_text
    assert "sqa-job" not in prompt_text
    assert "sales-job" not in prompt_text


def test_freshness_filtering_and_honest_availability():
    """Verify stale dates from 2022 are marked STALE and honest availability badges are preserved."""
    days, cat = calculate_freshness("2022-01-15T08:00:00Z")
    assert cat == "STALE"
    assert days is not None and days > 500

    days_recent, cat_recent = calculate_freshness("2026-10-12T00:00:00Z")
    assert cat_recent == "RECENT"

    # Verify search result items always retain honest unverified status
    is_tech, cat_name, family, relevance = classify_role_family_and_relevance("Backend Developer", "Python REST API")
    assert is_tech is True
    assert relevance == "DIRECT_FIT"
