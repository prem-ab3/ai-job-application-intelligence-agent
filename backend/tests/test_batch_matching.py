"""Unit and integration tests for Phase 2C resume-to-multiple-jobs matching and ranking."""

import json
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app

client = TestClient(app)

SAMPLE_RESUME = (
    "Senior Full-Stack Developer with 6 years of experience building web applications. "
    "Expert in Python, FastAPI, React, and PostgreSQL. "
    "Designed scalable microservices and automated CI/CD pipelines on AWS."
)


def test_batch_match_ranking_order_and_scores():
    """Verify jobs are ranked descending by match score and separated correctly."""
    mock_gemini_json = {
        "evaluations": [
            {
                "job_id": "job-alpha",
                "skills": [
                    {
                        "skill_name": "Python",
                        "category": "REQUIRED",
                        "is_matched": True,
                        "resume_evidence": "Expert in Python, FastAPI, React, and PostgreSQL.",
                    },
                    {
                        "skill_name": "FastAPI",
                        "category": "REQUIRED",
                        "is_matched": True,
                        "resume_evidence": "Expert in Python, FastAPI, React, and PostgreSQL.",
                    },
                ],
                "suggestions": "Great fit for backend role.",
            },
            {
                "job_id": "job-beta",
                "skills": [
                    {
                        "skill_name": "Python",
                        "category": "REQUIRED",
                        "is_matched": True,
                        "resume_evidence": "Expert in Python, FastAPI, React, and PostgreSQL.",
                    },
                    {
                        "skill_name": "Kubernetes",
                        "category": "REQUIRED",
                        "is_matched": False,
                        "resume_evidence": None,
                    },
                ],
                "suggestions": "Consider learning Kubernetes.",
            },
        ]
    }

    mock_response = MagicMock()
    mock_response.output_text = json.dumps(mock_gemini_json)

    mock_genai_client = MagicMock()
    mock_genai_client.interactions.create.return_value = mock_response

    payload = {
        "resume_text": SAMPLE_RESUME,
        "jobs": [
            {
                "id": "job-beta",
                "title": "Cloud Platform Engineer",
                "company": "CloudTech",
                "description": "Seeking a platform engineer with strong Python and Kubernetes experience.",
                "location": "Bengaluru",
            },
            {
                "id": "job-alpha",
                "title": "Senior Python Developer",
                "company": "AlphaCorp",
                "description": "Looking for an expert Python and FastAPI developer to architect scalable services.",
                "location": "Remote",
            },
        ],
    }

    with patch("app.agent.orchestrator.get_genai_client", return_value=mock_genai_client):
        response = client.post("/api/v1/jobs/match", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["total_jobs"] == 2
    assert len(data["ranked_jobs"]) == 2
    assert len(data["unranked_jobs"]) == 0

    # job-alpha has 2/2 required skills matched = 100.0% -> rank 1
    rank1 = data["ranked_jobs"][0]
    assert rank1["job_id"] == "job-alpha"
    assert rank1["rank"] == 1
    assert rank1["match_score"] == 100.0
    assert rank1["match_status"] == "RELIABLE_MATCH"
    assert len(rank1["matched_skills"]) == 2
    assert rank1["matched_skills"][0]["is_verified_evidence"] is True

    # job-beta has 1/2 required skills matched = 50.0% -> rank 2
    rank2 = data["ranked_jobs"][1]
    assert rank2["job_id"] == "job-beta"
    assert rank2["rank"] == 2
    assert rank2["match_score"] == 50.0
    assert len(rank2["missing_skills"]) == 1


def test_batch_match_hallucinated_evidence_downgraded():
    """Verify evidence not present in resume is downgraded to False before scoring."""
    mock_gemini_json = {
        "evaluations": [
            {
                "job_id": "job-1",
                "skills": [
                    {
                        "skill_name": "Go",
                        "category": "REQUIRED",
                        "is_matched": True,
                        # Hallucinated quote NOT in SAMPLE_RESUME
                        "resume_evidence": "5 years of Go programming at previous employer.",
                    }
                ],
                "suggestions": "Strengthen Go portfolio.",
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.output_text = json.dumps(mock_gemini_json)

    mock_genai_client = MagicMock()
    mock_genai_client.interactions.create.return_value = mock_response

    payload = {
        "resume_text": SAMPLE_RESUME,
        "jobs": [
            {
                "id": "job-1",
                "title": "Go Developer",
                "company": "GoLang Labs",
                "description": "Expert Go programmer needed for high throughput distributed engine.",
            }
        ],
    }

    with patch("app.agent.orchestrator.get_genai_client", return_value=mock_genai_client):
        response = client.post("/api/v1/jobs/match", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert len(data["ranked_jobs"]) == 1
    job_result = data["ranked_jobs"][0]

    # Hallucinated quote must be downgraded: score becomes 0.0%
    assert job_result["match_score"] == 0.0
    assert len(job_result["matched_skills"]) == 0
    assert len(job_result["missing_skills"]) == 1
    assert job_result["missing_skills"][0]["skill_name"] == "Go"
    assert job_result["missing_skills"][0]["resume_evidence"] is None


def test_batch_match_insufficient_description_honestly_separated():
    """Verify jobs with < 40 chars description are placed into unranked_jobs without calling Gemini."""
    mock_gemini_json = {
        "evaluations": [
            {
                "job_id": "job-long",
                "skills": [
                    {
                        "skill_name": "Python",
                        "category": "REQUIRED",
                        "is_matched": True,
                        "resume_evidence": "Expert in Python, FastAPI, React, and PostgreSQL.",
                    }
                ],
                "suggestions": "Good match.",
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.output_text = json.dumps(mock_gemini_json)

    mock_genai_client = MagicMock()
    mock_genai_client.interactions.create.return_value = mock_response

    payload = {
        "resume_text": SAMPLE_RESUME,
        "jobs": [
            {
                "id": "job-short",
                "title": "Software Dev",
                "company": "Brief Co",
                # < 40 characters snippet
                "description": "Software dev wanted.",
            },
            {
                "id": "job-long",
                "title": "Senior Python Engineer",
                "company": "Tech Corp",
                "description": "Looking for a seasoned Python engineer to develop backend microservices.",
            },
        ],
    }

    with patch("app.agent.orchestrator.get_genai_client", return_value=mock_genai_client):
        response = client.post("/api/v1/jobs/match", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["total_jobs"] == 2

    # job-long is in ranked_jobs
    assert len(data["ranked_jobs"]) == 1
    assert data["ranked_jobs"][0]["job_id"] == "job-long"
    assert data["ranked_jobs"][0]["rank"] == 1
    assert data["ranked_jobs"][0]["match_score"] == 100.0

    # job-short is in unranked_jobs with no misleading score
    assert len(data["unranked_jobs"]) == 1
    unranked = data["unranked_jobs"][0]
    assert unranked["job_id"] == "job-short"
    assert unranked["rank"] is None
    assert unranked["match_score"] is None
    assert unranked["match_status"] == "INSUFFICIENT_DESCRIPTION"
    assert "too brief" in unranked["suggestions"].lower()


def test_batch_match_gemini_malformed_json_fallback():
    """Verify malformed JSON from Gemini is handled gracefully without crashing."""
    mock_response = MagicMock()
    mock_response.output_text = "Sorry, I cannot format this in JSON right now."

    mock_genai_client = MagicMock()
    mock_genai_client.interactions.create.return_value = mock_response

    payload = {
        "resume_text": SAMPLE_RESUME,
        "jobs": [
            {
                "id": "job-1",
                "title": "Python Engineer",
                "company": "Company A",
                "description": "Experienced Python engineer needed for backend microservices and databases.",
            }
        ],
    }

    with patch("app.agent.orchestrator.get_genai_client", return_value=mock_genai_client):
        response = client.post("/api/v1/jobs/match", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert len(data["ranked_jobs"]) == 0
    assert len(data["unranked_jobs"]) == 1
    assert data["unranked_jobs"][0]["match_status"] == "EVALUATION_FAILED"
    assert data["unranked_jobs"][0]["match_score"] is None


def test_batch_match_request_validation():
    """Verify input validation constraints (resume length and jobs count)."""
    # Resume too short (< 20 chars)
    resp1 = client.post(
        "/api/v1/jobs/match",
        json={"resume_text": "Short", "jobs": [{"id": "1", "title": "Dev"}]},
    )
    assert resp1.status_code == 422

    # Empty jobs list
    resp2 = client.post(
        "/api/v1/jobs/match",
        json={"resume_text": SAMPLE_RESUME, "jobs": []},
    )
    assert resp2.status_code == 422


def test_batch_match_unrelated_roles_excluded_from_ranking_without_calling_gemini():
    """Verify irrelevant roles (Orthopedics, Inventory, Supplier QA, Sales) are gated to unranked_jobs with score=None, bypassing Gemini."""
    mock_gemini_json = {
        "evaluations": [
            {
                "job_id": "job-tech",
                "skills": [
                    {
                        "skill_name": "Python",
                        "category": "REQUIRED",
                        "is_matched": True,
                        "resume_evidence": "Expert in Python, FastAPI, React, and PostgreSQL.",
                    }
                ],
                "suggestions": "Strong alignment.",
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.output_text = json.dumps(mock_gemini_json)

    mock_genai_client = MagicMock()
    mock_genai_client.interactions.create.return_value = mock_response

    payload = {
        "resume_text": SAMPLE_RESUME,
        "jobs": [
            {
                "id": "job-ortho",
                "title": "Consultant Orthopedics",
                "company": "City Hospital",
                "description": "Looking for orthopedic consultant to diagnose fractures and perform joint surgeries in clinic.",
                "location": "Bengaluru",
            },
            {
                "id": "job-inventory",
                "title": "Inventory Manager",
                "company": "Logistics Hub",
                "description": "Supervise warehouse stock levels, inventory audits, supply chain, dispatch and procurement.",
                "location": "Mumbai",
            },
            {
                "id": "job-sqa",
                "title": "Supplier Quality Assurance Engineer",
                "company": "AutoMech Ltd",
                "description": "Audit hardware suppliers, inspect mechanical parts, and enforce supplier manufacturing QA standards.",
                "location": "Pune",
            },
            {
                "id": "job-sales",
                "title": "Senior Sales Associate - Inside sales",
                "company": "Outreach Sales Corp",
                "description": "Drive B2B sales pipeline, customer telecalling, cold outreach and sales revenue targets.",
                "location": "Remote",
            },
            {
                "id": "job-tech",
                "title": "Senior Python Developer",
                "company": "Software Lab",
                "description": "Architect scalable microservices using Python, FastAPI, and PostgreSQL with cloud CI/CD.",
                "location": "Bengaluru",
            },
        ],
    }

    with patch("app.agent.orchestrator.get_genai_client", return_value=mock_genai_client):
        response = client.post("/api/v1/jobs/match", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["total_jobs"] == 5

    # Only job-tech was sent to Gemini and placed in ranked_jobs
    assert len(data["ranked_jobs"]) == 1
    assert data["ranked_jobs"][0]["job_id"] == "job-tech"
    assert data["ranked_jobs"][0]["rank"] == 1
    assert data["ranked_jobs"][0]["match_score"] == 100.0

    # The 4 unrelated roles are placed in unranked_jobs with score=None and ROLE_MISMATCH
    assert len(data["unranked_jobs"]) == 4
    unranked_ids = {u["job_id"]: u for u in data["unranked_jobs"]}

    for role_id in ["job-ortho", "job-inventory", "job-sqa", "job-sales"]:
        assert role_id in unranked_ids
        item = unranked_ids[role_id]
        assert item["rank"] is None
        assert item["match_score"] is None
        assert item["is_reliable"] is False
        assert item["match_status"] == "ROLE_MISMATCH"
        assert item["role_relevance"] == "UNRELATED_ROLE"
        assert item["is_technical"] is False

    # Quota check: Verify Gemini was called only once with prompt containing ONLY job-tech
    mock_genai_client.interactions.create.assert_called_once()
    called_prompt = mock_genai_client.interactions.create.call_args[1]["input"]
    assert "job-tech" in called_prompt
    assert "job-ortho" not in called_prompt
    assert "job-inventory" not in called_prompt
    assert "job-sqa" not in called_prompt
    assert "job-sales" not in called_prompt


def test_batch_match_model_failover_on_503():
    """Verify that when the primary model throws a 503 high-demand error, automatic fallback succeeds."""
    mock_gemini_json = {
        "evaluations": [
            {
                "job_id": "job-py",
                "skills": [
                    {
                        "skill_name": "Python",
                        "category": "REQUIRED",
                        "is_matched": True,
                        "resume_evidence": "Expert in Python, FastAPI, React, and PostgreSQL.",
                    }
                ],
                "match_explanation": "Direct match for Python backend engineering requirements.",
                "suggestions": "Good fit.",
            }
        ]
    }

    mock_success_response = MagicMock()
    mock_success_response.output_text = json.dumps(mock_gemini_json)

    # First call simulates 503 UNAVAILABLE on gemini-3.8-flash, second call succeeds on gemini-3.5-flash-lite
    mock_genai_client = MagicMock()
    mock_genai_client.interactions.create.side_effect = [
        Exception("503 UNAVAILABLE: This model is currently experiencing high demand."),
        mock_success_response,
    ]

    payload = {
        "resume_text": SAMPLE_RESUME,
        "jobs": [
            {
                "id": "job-py",
                "title": "Backend Python Developer",
                "company": "TechCorp",
                "description": "Looking for backend Python developer with microservices experience.",
                "location": "Bengaluru",
            }
        ],
    }

    with patch("app.agent.orchestrator.get_genai_client", return_value=mock_genai_client):
        response = client.post("/api/v1/jobs/match", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert len(data["ranked_jobs"]) == 1
    assert data["ranked_jobs"][0]["job_id"] == "job-py"
    assert data["ranked_jobs"][0]["match_score"] == 100.0
    assert data["ranked_jobs"][0]["rank"] == 1
    assert "Python backend" in data["ranked_jobs"][0]["match_explanation"]
    # Verify interactions.create was called twice (initial attempt + failover)
    assert mock_genai_client.interactions.create.call_count == 2


def test_batch_match_seniority_weighting_entry_vs_architect():
    """Verify that entry-level candidates have junior roles prioritized over architect roles despite skill overlap."""
    junior_resume = (
        "Fresher / Junior Python Developer with 1 year internship experience in backend software development. "
        "Proficient in Python, Git, and building REST APIs. Graduated with B.Tech in 2025."
    )

    mock_gemini_json = {
        "evaluations": [
            {
                "job_id": "job-junior",
                "skills": [
                    {
                        "skill_name": "Python",
                        "category": "REQUIRED",
                        "is_matched": True,
                        "resume_evidence": "Proficient in Python, Git, and building REST APIs.",
                    }
                ],
                "match_explanation": "Ideal entry-level position matching junior developer foundation.",
                "suggestions": "Apply promptly.",
            },
            {
                "job_id": "job-architect",
                "skills": [
                    {
                        "skill_name": "Python",
                        "category": "REQUIRED",
                        "is_matched": True,
                        "resume_evidence": "Proficient in Python, Git, and building REST APIs.",
                    }
                ],
                "match_explanation": "Position requires extensive enterprise architecture leadership.",
                "suggestions": "Seniority gap.",
            },
        ]
    }

    mock_resp = MagicMock()
    mock_resp.output_text = json.dumps(mock_gemini_json)

    mock_genai_client = MagicMock()
    mock_genai_client.interactions.create.return_value = mock_resp

    payload = {
        "resume_text": junior_resume,
        "jobs": [
            {
                "id": "job-architect",
                "title": "Lead Enterprise AI Architect",
                "company": "Megacorp",
                "description": "Seeking 10+ years Lead Enterprise AI Architect with Python and distributed systems.",
                "location": "Bengaluru",
            },
            {
                "id": "job-junior",
                "title": "Junior Python Developer",
                "company": "Startup",
                "description": "Looking for junior python developer with 0-1 year experience in Python and REST APIs.",
                "location": "Bengaluru",
            },
        ],
    }

    with patch("app.agent.orchestrator.get_genai_client", return_value=mock_genai_client):
        response = client.post("/api/v1/jobs/match", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert len(data["ranked_jobs"]) == 2

    # Junior job should be ranked #1 with 100.0 score (aligned seniority)
    job_rank_1 = data["ranked_jobs"][0]
    assert job_rank_1["job_id"] == "job-junior"
    assert job_rank_1["rank"] == 1
    assert job_rank_1["match_score"] == 100.0
    assert job_rank_1["seniority_alignment"] == "ALIGNED_ENTRY"

    # Architect role should receive seniority multiplier (0.60), resulting in score 60.0 and rank #2
    job_rank_2 = data["ranked_jobs"][1]
    assert job_rank_2["job_id"] == "job-architect"
    assert job_rank_2["rank"] == 2
    assert job_rank_2["match_score"] == 60.0
    assert job_rank_2["seniority_alignment"] == "MISMATCH_LEAD_ARCHITECT"


def test_batch_match_evaluation_failure_honestly_unranked():
    """Verify that when all Gemini models fail, jobs are honestly placed in unranked_jobs without fabricated scores."""
    mock_genai_client = MagicMock()
    mock_genai_client.interactions.create.side_effect = Exception("503 Service Unavailable: All models down")

    payload = {
        "resume_text": SAMPLE_RESUME,
        "jobs": [
            {
                "id": "job-backend",
                "title": "Software Engineer",
                "company": "Acme Inc",
                "description": "Full stack engineer proficient with Python and React.",
                "location": "Hyderabad",
            }
        ],
    }

    with patch("app.agent.orchestrator.get_genai_client", return_value=mock_genai_client):
        response = client.post("/api/v1/jobs/match", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert len(data["ranked_jobs"]) == 0
    assert len(data["unranked_jobs"]) == 1

    unranked = data["unranked_jobs"][0]
    assert unranked["job_id"] == "job-backend"
    assert unranked["rank"] is None
    assert unranked["match_score"] is None
    assert unranked["is_reliable"] is False
    assert unranked["match_status"] == "EVALUATION_FAILED"
    assert "temporary service issue" in unranked["match_explanation"].lower()
