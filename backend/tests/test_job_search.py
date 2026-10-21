"""Unit and integration tests for Adzuna job search API integration (all external calls mocked)."""

from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch
import httpx
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.main import app
from app.services.adzuna_client import clean_html, search_adzuna_jobs

client = TestClient(app)

MOCK_ADZUNA_SUCCESS_RESPONSE = {
    "count": 42,
    "results": [
        {
            "id": "4920192301",
            "title": "<strong>Python</strong> Backend <i>Engineer</i>",
            "company": {"display_name": "Tech Corp &amp; Partners"},
            "location": {"display_name": "Bengaluru, Karnataka"},
            "description": "Looking for a <strong>FastAPI</strong> and &amp; Python engineer to build microservices.",
            "salary_min": 1200000,
            "salary_max": 1800000,
            "created": "2026-03-15T10:00:00Z",
            "redirect_url": "https://www.adzuna.in/land/ad/4920192301?v=abc",
        },
        {
            "id": "4920192302",
            "title": "Data Analyst",
            "company": {},  # Missing display_name
            "location": {"area": ["Mumbai", "Maharashtra"]},  # Missing display_name
            "description": "SQL and Excel expert wanted.",
            "salary_min": None,
            "salary_max": None,
            "created": "2026-03-14T08:30:00Z",
            "redirect_url": "https://www.adzuna.in/land/ad/4920192302?v=def",
        },
    ],
}


def test_clean_html_strips_tags_and_unescapes():
    """Verify HTML tag stripping and entity unescaping."""
    assert clean_html("<strong>Senior</strong> &amp; Lead &lt;Engineer&gt;") == "Senior & Lead <Engineer>"
    assert clean_html(None) == ""
    assert clean_html("   multiple   spaces  \n  here ") == "multiple spaces here"
    assert clean_html("Already clean text") == "Already clean text"


import asyncio

def test_search_adzuna_jobs_normalization_with_mock():
    """Verify data normalization without network calls."""
    async def _run():
        mock_response = httpx.Response(
            status_code=200,
            json=MOCK_ADZUNA_SUCCESS_RESPONSE,
            request=httpx.Request("GET", "https://api.adzuna.com/test"),
        )

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.object(settings, "ADZUNA_APP_ID", "mock_app_id"), patch.object(
            settings, "ADZUNA_APP_KEY", "mock_app_key"
        ):
            result = await search_adzuna_jobs(
                keywords="Python",
                location="Bengaluru",
                page=1,
                results_per_page=10,
                client=mock_client,
            )

        assert result.total_results == 42
        assert result.page == 1
        assert result.results_per_page == 10
        assert len(result.jobs) == 2

        job1 = result.jobs[0]
        assert job1.id == "4920192301"
        # Tag stripping verification
        assert job1.title == "Python Backend Engineer"
        assert job1.company == "Tech Corp & Partners"
        assert job1.location == "Bengaluru, Karnataka"
        assert "FastAPI and & Python engineer" in job1.description_snippet
        assert job1.salary_min == 1200000.0
        assert job1.salary_max == 1800000.0
        assert job1.salary_currency == "INR"
        assert job1.salary_period == "annual"
        # Non-fabrication verification
        assert job1.closing_date is None
        assert job1.direct_apply_url is None
        assert job1.status == "UNVERIFIED_SEARCH_INDEX"
        assert job1.source_name == "Adzuna India"
        assert job1.source_url == "https://www.adzuna.in/land/ad/4920192301?v=abc"

        job2 = result.jobs[1]
        assert job2.title == "Data Analyst"
        assert job2.company == "Undisclosed Company"
        assert job2.location == "Mumbai, Maharashtra"
        assert job2.salary_min is None
        assert job2.salary_max is None
        assert job2.salary_currency is None
        assert job2.salary_period == "undisclosed"
        assert job2.closing_date is None
        assert job2.direct_apply_url is None
        assert job2.status == "UNVERIFIED_SEARCH_INDEX"

    asyncio.run(_run())


def test_api_endpoint_success_with_mock():
    """Verify GET /api/v1/jobs/search endpoint returns 200 with normalized response."""
    mock_response = httpx.Response(
        status_code=200,
        json=MOCK_ADZUNA_SUCCESS_RESPONSE,
        request=httpx.Request("GET", "https://api.adzuna.com/test"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, patch.object(
        settings, "ADZUNA_APP_ID", "mock_app_id"
    ), patch.object(settings, "ADZUNA_APP_KEY", "mock_app_key"):
        mock_get.return_value = mock_response

        response = client.get("/api/v1/jobs/search?keywords=Python&location=Bengaluru&page=1&results_per_page=10")

    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] == 42
    assert len(data["jobs"]) == 2
    assert data["jobs"][0]["title"] == "Python Backend Engineer"
    assert data["jobs"][0]["status"] == "UNVERIFIED_SEARCH_INDEX"
    assert data["jobs"][0]["closing_date"] is None
    assert data["jobs"][0]["direct_apply_url"] is None


def test_api_endpoint_missing_credentials_returns_503():
    """Verify 503 is returned if Adzuna credentials are not configured."""
    with patch.object(settings, "ADZUNA_APP_ID", ""), patch.object(settings, "ADZUNA_APP_KEY", ""):
        response = client.get("/api/v1/jobs/search?keywords=Python")

    assert response.status_code == 503
    data = response.json()
    assert "credentials are not configured" in data["detail"].lower()


def test_api_endpoint_upstream_timeout_returns_504():
    """Verify 504 is returned when Adzuna API times out."""
    with patch(
        "httpx.AsyncClient.get",
        side_effect=httpx.TimeoutException("Connection timed out"),
    ), patch.object(settings, "ADZUNA_APP_ID", "mock_id"), patch.object(
        settings, "ADZUNA_APP_KEY", "mock_key"
    ):
        response = client.get("/api/v1/jobs/search?keywords=Python")

    assert response.status_code == 504
    data = response.json()
    assert "timed out" in data["detail"].lower()


def test_api_endpoint_upstream_auth_failure_returns_502():
    """Verify 502 is returned when Adzuna returns 401 Unauthorized."""
    mock_response = httpx.Response(
        status_code=401,
        json={"error": "unauthorized"},
        request=httpx.Request("GET", "https://api.adzuna.com/test"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, patch.object(
        settings, "ADZUNA_APP_ID", "bad_id"
    ), patch.object(settings, "ADZUNA_APP_KEY", "bad_key"):
        mock_get.return_value = mock_response
        response = client.get("/api/v1/jobs/search?keywords=Python")

    assert response.status_code == 502
    data = response.json()
    assert "authentication failed" in data["detail"].lower()


def test_api_endpoint_upstream_rate_limit_returns_429():
    """Verify 429 is passed through safely when Adzuna returns 429."""
    mock_response = httpx.Response(
        status_code=429,
        json={"error": "rate limit exceeded"},
        request=httpx.Request("GET", "https://api.adzuna.com/test"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, patch.object(
        settings, "ADZUNA_APP_ID", "mock_id"
    ), patch.object(settings, "ADZUNA_APP_KEY", "mock_key"):
        mock_get.return_value = mock_response
        response = client.get("/api/v1/jobs/search?keywords=Python")

    assert response.status_code == 429
    data = response.json()
    assert "rate limit" in data["detail"].lower()


def test_api_endpoint_validation_constraints():
    """Verify parameter validation (page >= 1, results_per_page between 1 and 50)."""
    # Invalid page = 0
    resp1 = client.get("/api/v1/jobs/search?page=0")
    assert resp1.status_code == 422

    # Invalid results_per_page = 100 (> 50)
    resp2 = client.get("/api/v1/jobs/search?results_per_page=100")
    assert resp2.status_code == 422


def test_classify_job_relevance_distinguishes_technical_from_sales():
    """Verify deterministic relevance classification distinguishes technical roles from non-technical roles."""
    from app.services.adzuna_client import classify_job_relevance

    # Non-technical sales role mentioned in user feedback
    is_tech1, cat1 = classify_job_relevance(
        title="Senior Sales Associate - Inside sales",
        snippet="Drive customer acquisition, telesales calls, and lead generation.",
    )
    assert is_tech1 is False
    assert cat1 == "NON_TECHNICAL"

    # Technical engineering roles
    is_tech2, cat2 = classify_job_relevance(
        title="Senior AI Engineer",
        snippet="Build LLM applications and agent workflows using Python.",
    )
    assert is_tech2 is True
    assert cat2 == "TECHNICAL"

    is_tech3, cat3 = classify_job_relevance(
        title="Backend Developer (FastAPI / Python)",
        snippet="Architect robust REST APIs and database models.",
    )
    assert is_tech3 is True
    assert cat3 == "TECHNICAL"

    is_tech4, cat4 = classify_job_relevance(
        title="Software Engineer",
        snippet="Full-stack development using React and Python.",
    )
    assert is_tech4 is True
    assert cat4 == "TECHNICAL"


def test_classify_role_family_and_relevance_excludes_unrelated_domains():
    """Verify specific irrelevant job families reported in user feedback are classified as UNRELATED_ROLE."""
    from app.services.adzuna_client import classify_role_family_and_relevance

    # 1. Healthcare: Consultant Orthopedics
    is_tech, cat, family, rel = classify_role_family_and_relevance(
        title="Consultant Orthopedics",
        snippet="Provide orthopedic consultations and clinical diagnoses for joint and bone conditions.",
    )
    assert is_tech is False
    assert cat == "NON_TECHNICAL"
    assert family == "HEALTHCARE"
    assert rel == "UNRELATED_ROLE"

    # 2. Logistics: Inventory Manager
    is_tech, cat, family, rel = classify_role_family_and_relevance(
        title="Inventory Manager",
        snippet="Manage warehouse stock levels, inventory audits, supply chain, and logistics tracking.",
    )
    assert is_tech is False
    assert cat == "NON_TECHNICAL"
    assert family == "LOGISTICS"
    assert rel == "UNRELATED_ROLE"

    # 3. Manufacturing / Hardware QA: Supplier Quality Assurance Engineer
    is_tech, cat, family, rel = classify_role_family_and_relevance(
        title="Supplier Quality Assurance Engineer",
        snippet="Audit manufacturing suppliers, inspect mechanical parts, and ensure ISO compliance.",
    )
    assert is_tech is False
    assert cat == "NON_TECHNICAL"
    assert family == "MANUFACTURING_HARDWARE"
    assert rel == "UNRELATED_ROLE"

    # 4. Sales / BPO: Inside Sales Associate
    is_tech, cat, family, rel = classify_role_family_and_relevance(
        title="Inside Sales Associate",
        snippet="Execute cold calling campaigns, lead conversion, and direct sales targets.",
    )
    assert is_tech is False
    assert cat == "NON_TECHNICAL"
    assert family == "SALES_BPO"
    assert rel == "UNRELATED_ROLE"

    # 5. Technical / AI Engineer: Direct Fit
    is_tech, cat, family, rel = classify_role_family_and_relevance(
        title="AI Engineer",
        snippet="Build LLM chains, agentic workflows, and FastAPI microservices with Python.",
    )
    assert is_tech is True
    assert cat == "TECHNICAL"
    assert family == "SOFTWARE_AI"
    assert rel == "DIRECT_FIT"


def test_calculate_freshness_categorization():
    """Verify posting date calculations accurately tag RECENT, MODERATE, STALE, and UNKNOWN listings."""
    from datetime import datetime, timezone, timedelta
    from app.services.adzuna_client import calculate_freshness

    now = datetime.now(timezone.utc)

    # 1. 5 days ago -> RECENT
    recent_date = (now - timedelta(days=5)).isoformat()
    days, cat = calculate_freshness(recent_date)
    assert days == 5
    assert cat == "RECENT"

    # 2. 45 days ago -> MODERATE
    mod_date = (now - timedelta(days=45)).isoformat()
    days, cat = calculate_freshness(mod_date)
    assert days == 45
    assert cat == "MODERATE"

    # 3. 2022 posting (stale listing from screenshots) -> STALE
    stale_date = "2022-04-15T10:00:00Z"
    days, cat = calculate_freshness(stale_date)
    assert days is not None and days > 300
    assert cat == "STALE"

    # 4. Missing date -> UNKNOWN
    days_none, cat_none = calculate_freshness(None)
    assert days_none is None
    assert cat_none == "UNKNOWN"


def test_api_endpoint_with_sort_by_and_max_days_old():
    """Verify search endpoint accepts sort_by and max_days_old and passes them to client."""
    mock_response = httpx.Response(
        status_code=200,
        json={"results": [], "count": 0},
        request=httpx.Request("GET", "https://api.adzuna.com/test"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, patch.object(
        settings, "ADZUNA_APP_ID", "mock_id"
    ), patch.object(settings, "ADZUNA_APP_KEY", "mock_key"):
        mock_get.return_value = mock_response
        response = client.get("/api/v1/jobs/search?keywords=Python&sort_by=date&max_days_old=30")

    assert response.status_code == 200
    mock_get.assert_called_once()
    called_params = mock_get.call_args[1]["params"]
    assert called_params["sort_by"] == "date"
    assert called_params["max_days_old"] == 30
