"""Adzuna API client for job search in India."""

import html
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from app.config import settings
from app.schemas import JobSearchResponse, JobSearchResultItem

logger = logging.getLogger(__name__)

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"
REQUEST_TIMEOUT_SECONDS = 10.0


class AdzunaClientError(Exception):
    """Safe client-facing error for Adzuna API operations."""
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def clean_html(text: Optional[str]) -> str:
    """Strips HTML markup and unescapes HTML entities from strings."""
    if not text:
        return ""
    # Remove HTML tags like <strong>, </strong>, <p>, etc.
    no_tags = re.sub(r"<[^>]+>", "", text)
    # Unescape HTML entities like &amp;, &nbsp;, &#39;
    clean = html.unescape(no_tags)
    # Normalize multiple whitespaces
    return re.sub(r"\s+", " ", clean).strip()


HEALTHCARE_REGEX = re.compile(
    r"\b(orthopedic|orthopaedics|surgeon|doctor|physician|nurse|nursing|dentist|dental|clinic|clinical|hospital|"
    r"radiology|pharmacist|pharmacy|pathology|cardiologist|pediatrician|consultant\s+orthopedics|medical\s+officer|"
    r"healthcare|therapist|optometrist|veterinarian)\b",
    re.IGNORECASE,
)

LOGISTICS_REGEX = re.compile(
    r"\b(inventory\s+manager|inventory\s+executive|warehouse|storekeeper|supply\s+chain|procurement|"
    r"materials\s+manager|dispatch\s+executive|dispatch\s+manager|fleet\s+manager|logistics\s+executive|"
    r"logistics\s+manager|freight|shipping\s+executive)\b",
    re.IGNORECASE,
)

MANUFACTURING_HARDWARE_REGEX = re.compile(
    r"\b("
    r"supplier\s+quality\s+assurance|supplier\s+qa|sqa\s+engineer|"
    r"mechanical\s+engineer(ing)?|mechanical\s+design\s+engineer|"
    r"civil\s+engineer(ing)?|civil\s+site\s+engineer|site\s+engineer|"
    r"electrical\s+engineer(ing)?|electronics\s+engineer(ing)?|"
    r"chemical\s+engineer(ing)?|aerospace\s+engineer(ing)?|aeronautical\s+engineer|"
    r"structural\s+engineer(ing)?|automotive\s+engineer|biomedical\s+engineer|"
    r"petroleum\s+engineer|marine\s+engineer|environmental\s+engineer|"
    r"industrial\s+engineer|production\s+engineer|plant\s+engineer|"
    r"manufacturing\s+engineer|maintenance\s+engineer|process\s+engineer|"
    r"piping\s+engineer|hvac(\s+engineer)?|welding(\s+engineer)?|"
    r"plant\s+supervisor|metallurg(y|ical)|mining\s+engineer"
    r")\b",
    re.IGNORECASE,
)

SALES_RETAIL_REGEX = re.compile(
    r"\b("
    r"inside\s+sales|field\s+sales|direct\s+sales|sales\s+associate|sales\s+executive|sales\s+manager|"
    r"sales\s+representative|sales\s+consultant|sales\s+officer|sales\s+lead\b|"
    r"telecaller|tele-caller|tele-sales|telesales|bde\b|bpo\b|business\s+development\s+executive|"
    r"business\s+development\s+associate|business\s+development\s+manager|"
    r"retail\s+associate|retail\s+executive|store\s+manager|cashier|"
    r"real\s+estate|realtor|insurance\s+agent|front\s+desk|receptionist|"
    r"customer\s+support\s+executive|customer\s+care|call\s+center\s+executive|"
    r"marketing\s+executive|digital\s+marketer|seo\s+executive|content\s+writer"
    r")\b",
    re.IGNORECASE,
)

FINANCE_REGEX = re.compile(
    r"\b("
    r"chartered\s+accountant|accountant\b|accounting\b|accounts\s+executive|accounts\s+manager|"
    r"bookkeeper|bookkeeping|audit\s+associate|auditor\b|internal\s+audit|tax\s+consultant|"
    r"teller\b|bank\s+teller|loan\s+officer|credit\s+analyst|financial\s+analyst|"
    r"finance\s+manager|finance\s+executive|wealth\s+manager|actuary"
    r")\b",
    re.IGNORECASE,
)

HR_ADMIN_REGEX = re.compile(
    r"\b("
    r"hr\s+executive|hr\s+manager|hr\s+generalist|hr\s+associate|hr\s+assistant|hr\s+intern|hr\s+recruiter|"
    r"human\s+resources|talent\s+acquisition|recruiter\b|recruitment\s+specialist|staffing\s+specialist|"
    r"payroll\s+executive|payroll\s+specialist|office\s+administrator|office\s+assistant|"
    r"administrative\s+assistant|admin\s+executive|executive\s+assistant"
    r")\b",
    re.IGNORECASE,
)

QA_TESTING_REGEX = re.compile(
    r"\b("
    r"sdet\b|"
    r"software\s+development\s+engineer\s+in\s+test|"
    r"qa(\s+automation)?(\s+engineer|\s+tester|\s+analyst|\s+lead)?\b|"
    r"quality\s+assurance(\s+engineer|\s+tester|\s+analyst|\s+automation)?\b|"
    r"test\s+automation(\s+engineer)?\b|"
    r"automation\s+test(er|ing)?(\s+engineer|\s+analyst)?\b|"
    r"manual\s+test(er|ing)?(\s+engineer|\s+analyst)?\b|"
    r"data\s+test(er|ing)?(\s+engineer|\s+analyst)?\b|"
    r"etl\s+test(er|ing)?(\s+engineer|\s+analyst)?\b|"
    r"software\s+test(er|ing)?(\s+engineer|\s+analyst)?\b|"
    r"test\s+engineer\b|"
    r"testing\s+engineer\b|"
    r"performance\s+test(er|ing)?(\s+engineer)?\b|"
    r"security\s+tester\b|penetration\s+tester\b"
    r")\b",
    re.IGNORECASE,
)

SOFTWARE_AI_DIRECT_REGEX = re.compile(
    r"(?:"
    r"\b(?:ai\s+engineer|artificial\s+intelligence(\s+engineer)?|"
    r"machine\s+learning(\s+engineer)?|ml\s+engineer|mlops(\s+engineer)?|deep\s+learning(\s+engineer)?|"
    r"data\s+scientist|data\s+science|data\s+engineer|big\s+data\s+engineer|"
    r"nlp\s+engineer|computer\s+vision\s+engineer|llm\s+engineer|genai\s+engineer|generative\s+ai|"
    r"python(\s+developer|\s+engineer|\s+programmer)?|"
    r"backend(\s+developer|\s+engineer)?|back-end(\s+developer|\s+engineer)?|"
    r"frontend(\s+developer|\s+engineer)?|front-end(\s+developer|\s+engineer)?|"
    r"full\s*stack(\s+developer|\s+engineer)?|fullstack(\s+developer|\s+engineer)?|"
    r"react(\s+developer|\s+engineer|\s+native|\.js)?|"
    r"angular(\s+developer|\s+engineer)?|"
    r"vue(\.?js)?(\s+developer|\s+engineer)?|"
    r"software\s+engineer(ing)?|software\s+developer|software\s+programmer|software\s+architect|"
    r"devops(\s+engineer)?|sre\b|site\s+reliability\s+engineer|"
    r"cloud\s+engineer|cloud\s+architect|cloud\s+developer|"
    r"platform\s+engineer|infrastructure\s+engineer|"
    r"systems?\s+engineer|systems?\s+developer|systems?\s+programmer|"
    r"firmware\s+engineer|embedded\s+software(\s+engineer)?|"
    r"mobile\s+developer|ios\s+developer|android\s+developer|"
    r"golang(\s+developer|\s+engineer)?|\bgo\s+developer|"
    r"java(\s+developer|\s+engineer)?|"
    r"javascript(\s+developer|\s+engineer)?|typescript(\s+developer|\s+engineer)?|"
    r"node\.?js(\s+developer|\s+engineer)?|"
    r"fastapi(\s+developer|\s+engineer)?|django(\s+developer|\s+engineer)?|"
    r"solutions?\s+architect|technical\s+architect|enterprise\s+architect|"
    r"programmer|coder|web\s+developer|application\s+developer|app\s+developer)\b|"
    r"\bc\+\+(?!\w|\+)(\s+developer|\s+engineer)?|"
    r"\bc#(?!\w)(\s+developer|\s+engineer)?|"
    r"(?<!\w)\.net(\s+developer|\s+engineer)?\b|"
    r"\bdotnet(\s+developer|\s+engineer)?\b|"
    r"\basp\.net(\s+developer|\s+engineer)?\b"
    r")",
    re.IGNORECASE,
)

# Backward-compatibility alias
SOFTWARE_AI_REGEX = SOFTWARE_AI_DIRECT_REGEX


def classify_role_family_and_relevance(title: str, snippet: str = "") -> tuple[bool, str, str, str]:
    """
    Deterministically evaluates role-family relevance against technical/software engineering profiles.
    Returns:
        (is_technical: bool, role_category: str, role_family: str, role_relevance: str)
    """
    clean_title = (title or "").lower()
    clean_snippet = (snippet or "").lower()

    # 1. Non-technical / unrelated career families
    if HEALTHCARE_REGEX.search(clean_title):
        return False, "NON_TECHNICAL", "HEALTHCARE", "UNRELATED_ROLE"
    if LOGISTICS_REGEX.search(clean_title):
        return False, "NON_TECHNICAL", "LOGISTICS", "UNRELATED_ROLE"
    if MANUFACTURING_HARDWARE_REGEX.search(clean_title):
        return False, "NON_TECHNICAL", "MANUFACTURING_HARDWARE", "UNRELATED_ROLE"
    if SALES_RETAIL_REGEX.search(clean_title):
        return False, "NON_TECHNICAL", "SALES_BPO", "UNRELATED_ROLE"
    if FINANCE_REGEX.search(clean_title):
        return False, "NON_TECHNICAL", "FINANCE", "UNRELATED_ROLE"
    if HR_ADMIN_REGEX.search(clean_title):
        return False, "NON_TECHNICAL", "HR_ADMIN", "UNRELATED_ROLE"

    # 2. Related technical roles (QA, SDET, Testing, Verification)
    if QA_TESTING_REGEX.search(clean_title):
        return True, "TECHNICAL", "QA_TESTING", "RELATED_TECH"

    # 3. Direct technical fit (Software, AI, Machine Learning, Web/Cloud Developers)
    if SOFTWARE_AI_DIRECT_REGEX.search(clean_title):
        return True, "TECHNICAL", "SOFTWARE_AI", "DIRECT_FIT"

    # 4. Snippet fallback checks (when title is generic but description specifies domain)
    if QA_TESTING_REGEX.search(clean_snippet):
        return True, "TECHNICAL", "QA_TESTING", "RELATED_TECH"
    if SOFTWARE_AI_DIRECT_REGEX.search(clean_snippet):
        return True, "TECHNICAL", "SOFTWARE_AI", "RELATED_TECH"

    return True, "GENERAL", "OTHER", "RELATED_TECH"


ARCHITECT_LEAD_TITLE_REGEX = re.compile(
    r"\b("
    r"architect\b|"
    r"principal\b|"
    r"director\b|"
    r"chief\b|"
    r"head\s+of\b|"
    r"tech\s+lead\b|"
    r"technical\s+lead\b|"
    r"team\s+lead\b|"
    r"engineering\s+lead\b|"
    r"lead\s+(developer|engineer|programmer|architect|scientist|analyst)\b|"
    r"staff\s+engineer\b"
    r")",
    re.IGNORECASE,
)

SENIOR_TITLE_REGEX = re.compile(
    r"\b(senior|sr(?:\.|\b))\b",
    re.IGNORECASE,
)

ENTRY_JUNIOR_TITLE_REGEX = re.compile(
    r"\b(junior|jr(?:\.|\b)|intern\b|internship|fresher|trainee|graduate\b|entry\s+level)\b",
    re.IGNORECASE,
)

# Backward-compatibility aliases
ARCHITECT_LEAD_REGEX = ARCHITECT_LEAD_TITLE_REGEX
SENIOR_REGEX = SENIOR_TITLE_REGEX
ENTRY_JUNIOR_REGEX = ENTRY_JUNIOR_TITLE_REGEX

# Snippet-only fallback patterns (used only when title contains no seniority indication)
ARCHITECT_LEAD_SNIPPET_REGEX = re.compile(
    r"\b(principal\s+architect|chief\s+architect|head\s+of\s+engineering|1[0-9]\+?\s*(?:years?|yrs?)(?:\s+of)?\s+experience)\b",
    re.IGNORECASE,
)

SENIOR_SNIPPET_REGEX = re.compile(
    r"\b([5-9]\+?\s*(?:to\s*\d+\s*)?(?:years?|yrs?)(?:\s+of)?\s+experience|senior\s+level|senior\s+role)\b",
    re.IGNORECASE,
)

ENTRY_JUNIOR_SNIPPET_REGEX = re.compile(
    r"\b((?:0-1|0-2|1-2)\s*(?:years?|yrs?)(?:\s+of)?\s+experience|entry\s+level|freshers?\s+(?:can\s+apply|welcome))\b",
    re.IGNORECASE,
)


def detect_job_seniority(title: str, snippet: str = "") -> str:
    """
    Classifies job posting into ARCHITECT_LEAD, SENIOR, ENTRY_JUNIOR, or MID_LEVEL.
    Priority is strictly given to job-title evidence over description keywords,
    ensuring that junior roles are never misclassified as senior merely because
    the description mentions senior-level experience or senior teammates.
    """
    clean_title = (title or "").lower()
    clean_snippet = (snippet or "").lower()

    # Priority 1: Direct title evidence strictly governs seniority
    if ARCHITECT_LEAD_TITLE_REGEX.search(clean_title):
        return "ARCHITECT_LEAD"
    if SENIOR_TITLE_REGEX.search(clean_title):
        return "SENIOR"
    if ENTRY_JUNIOR_TITLE_REGEX.search(clean_title):
        return "ENTRY_JUNIOR"

    # Priority 2: Only if title has no explicit seniority, examine snippet requirements
    if ARCHITECT_LEAD_SNIPPET_REGEX.search(clean_snippet):
        return "ARCHITECT_LEAD"
    if SENIOR_SNIPPET_REGEX.search(clean_snippet):
        return "SENIOR"
    if ENTRY_JUNIOR_SNIPPET_REGEX.search(clean_snippet):
        return "ENTRY_JUNIOR"

    return "MID_LEVEL"


def detect_candidate_seniority(resume_text: str) -> str:
    """Classifies candidate into SENIOR_LEAD, MID_LEVEL, or ENTRY_JUNIOR."""
    text = (resume_text or "").lower()
    has_lead_senior = bool(
        re.search(
            r"\b(senior|lead|principal|staff|architect|director|5\+?\s*years|6\+?\s*years|7\+?\s*years|8\+?\s*years|10\+?\s*years)\b",
            text,
        )
    )
    has_entry_junior = bool(
        re.search(
            r"\b(junior|entry\s+level|fresher|intern|internship|student|graduate|fresher|0-1\s*year|0-2\s*years|b\.?tech\s+student)\b",
            text,
        )
    )

    if has_lead_senior:
        return "SENIOR_LEAD"
    if has_entry_junior:
        return "ENTRY_JUNIOR"
    return "MID_LEVEL"


def evaluate_seniority_alignment(candidate_seniority: str, job_seniority: str) -> tuple[str, float]:
    """
    Evaluates seniority fit and returns (alignment_label, score_multiplier).
    Prevents senior AI/ML architect roles from outranking junior/entry roles for junior candidates.
    """
    if candidate_seniority == "ENTRY_JUNIOR":
        if job_seniority == "ARCHITECT_LEAD":
            return "MISMATCH_LEAD_ARCHITECT", 0.60
        if job_seniority == "SENIOR":
            return "EXPERIENCE_GAP_SENIOR", 0.80
        if job_seniority in ("ENTRY_JUNIOR", "MID_LEVEL"):
            return "ALIGNED_ENTRY", 1.0
    elif candidate_seniority == "SENIOR_LEAD":
        if job_seniority in ("ARCHITECT_LEAD", "SENIOR", "MID_LEVEL"):
            return "ALIGNED_SENIOR", 1.0
        if job_seniority == "ENTRY_JUNIOR":
            return "OVERQUALIFIED_CANDIDATE", 0.90
    else:  # MID_LEVEL
        if job_seniority == "ARCHITECT_LEAD":
            return "EXPERIENCE_GAP_LEAD", 0.85
        return "ALIGNED_MID", 1.0
    return "ALIGNED", 1.0


def classify_job_relevance(title: str, snippet: str = "") -> tuple[bool, str]:
    """Backward-compatible helper returning (is_technical, role_category)."""
    is_tech, role_cat, _, _ = classify_role_family_and_relevance(title, snippet)
    return is_tech, role_cat




def calculate_freshness(created_str: Optional[str]) -> tuple[Optional[int], str]:
    """
    Calculates job age and freshness using the source timestamp.
    Future-dated listings are explicitly flagged.
    """
    if not created_str:
        return None, "UNKNOWN"

    try:
        clean_str = created_str.replace("Z", "+00:00")
        created_dt = datetime.fromisoformat(clean_str)

        if created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)

        now_dt = datetime.now(timezone.utc)

        if created_dt > now_dt:
            return None, "FUTURE"

        days_ago = (now_dt - created_dt).days

        if days_ago <= 30:
            return days_ago, "RECENT"
        elif days_ago <= 90:
            return days_ago, "MODERATE"
        else:
            return days_ago, "STALE"

    except (ValueError, TypeError):
        return None, "UNKNOWN"



'''
def calculate_freshness(created_str: Optional[str]) -> tuple[Optional[int], str]:
    """
    Calculates age in days and freshness category from ISO timestamp.
    Returns (days_ago: Optional[int], freshness: str).
    """
    if not created_str:
        return None, "UNKNOWN"

    try:
        clean_str = created_str.replace("Z", "+00:00")
        created_dt = datetime.fromisoformat(clean_str)
        now_dt = datetime.now(timezone.utc)
        days_ago = max(0, (now_dt - created_dt).days)

        if days_ago <= 30:
            return days_ago, "RECENT"
        elif days_ago <= 90:
            return days_ago, "MODERATE"
        else:
            return days_ago, "STALE"
    except Exception:
        return None, "UNKNOWN"
'''



async def search_adzuna_jobs(
    keywords: Optional[str] = None,
    location: Optional[str] = None,
    page: int = 1,
    results_per_page: int = 10,
    sort_by: Optional[str] = "date",
    max_days_old: Optional[int] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> JobSearchResponse:
    """
    Queries the official Adzuna India job search endpoint and normalizes results.
    Does NOT write records to the database.
    """
    app_id = settings.ADZUNA_APP_ID.strip()
    app_key = settings.ADZUNA_APP_KEY.strip()
    country = (settings.ADZUNA_COUNTRY.strip() or "in").lower()

    if not app_id or not app_key:
        logger.error("ADZUNA_APP_ID or ADZUNA_APP_KEY is not configured in settings.")
        raise AdzunaClientError(
            "Adzuna API credentials are not configured on the server.",
            status_code=503,
        )

    # Documented endpoint: /v1/api/jobs/{country}/search/{page}
    url = f"{ADZUNA_BASE_URL}/{country}/search/{page}"
    params: Dict[str, Any] = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": results_per_page,
        "content-type": "application/json",
    }
    if keywords and keywords.strip():
        params["what"] = keywords.strip()
    if location and location.strip():
        params["where"] = location.strip()
    if sort_by and sort_by.strip():
        params["sort_by"] = sort_by.strip()
    if max_days_old is not None and max_days_old > 0:
        params["max_days_old"] = int(max_days_old)

    should_close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS)
        should_close_client = True

    try:
        response = await client.get(url, params=params)
    except httpx.TimeoutException as exc:
        logger.error("Adzuna API request timed out after %s seconds", REQUEST_TIMEOUT_SECONDS)
        raise AdzunaClientError("Adzuna job search request timed out.", status_code=504) from exc
    except httpx.RequestError as exc:
        logger.error("Network error communicating with Adzuna API: %s", type(exc).__name__)
        raise AdzunaClientError("Unable to connect to Adzuna job search service.", status_code=502) from exc
    finally:
        if should_close_client:
            await client.aclose()

    if response.status_code == 401 or response.status_code == 403:
        logger.error("Adzuna authentication failed (HTTP %s)", response.status_code)
        raise AdzunaClientError("Adzuna API authentication failed.", status_code=502)
    elif response.status_code == 429:
        logger.warning("Adzuna rate limit exceeded (HTTP 429)")
        raise AdzunaClientError("Adzuna API rate limit reached. Please try again later.", status_code=429)
    elif response.status_code == 400:
        logger.warning("Adzuna rejected query parameters (HTTP 400)")
        raise AdzunaClientError("Invalid search query parameters.", status_code=400)
    elif response.status_code != 200:
        logger.error("Adzuna returned unexpected HTTP %s", response.status_code)
        raise AdzunaClientError("Adzuna service returned an error.", status_code=502)

    try:
        data = response.json()
    except Exception as exc:
        logger.error("Failed to parse JSON response from Adzuna API")
        raise AdzunaClientError("Invalid response received from Adzuna service.", status_code=502) from exc

    raw_results = data.get("results")
    if not isinstance(raw_results, list):
        raw_results = []

    normalized_jobs: List[JobSearchResultItem] = []
    for item in raw_results:
        if not isinstance(item, dict):
            continue

        job_id = str(item.get("id") or "")
        title = clean_html(item.get("title")) or "Untitled Position"

        company_dict = item.get("company")
        company = (
            clean_html(company_dict.get("display_name"))
            if isinstance(company_dict, dict)
            else "Undisclosed Company"
        ) or "Undisclosed Company"

        location_dict = item.get("location")
        location_str = "India"
        if isinstance(location_dict, dict):
            location_str = (
                clean_html(location_dict.get("display_name"))
                or ", ".join(location_dict.get("area") or [])
                or "India"
            )

        snippet = clean_html(item.get("description")) or "No description snippet available."

        salary_min = item.get("salary_min")
        salary_max = item.get("salary_max")
        salary_min_val = float(salary_min) if salary_min is not None else None
        salary_max_val = float(salary_max) if salary_max is not None else None

        has_salary = salary_min_val is not None or salary_max_val is not None
        salary_currency = "INR" if (has_salary and country == "in") else (None if not has_salary else "INR")
        salary_period = "annual" if has_salary else "undisclosed"

        redirect_url = item.get("redirect_url") or ""

        days_ago, freshness = calculate_freshness(item.get("created"))
        is_tech, role_cat, role_fam, role_rel = classify_role_family_and_relevance(title, snippet)

        if role_rel == "UNRELATED_ROLE":
            rel_reason = f"Excluded from primary tech recommendations: non-software career family ({role_fam.replace('_', ' ').title()})"
        elif role_rel == "DIRECT_FIT":
            rel_reason = "Direct match with Software & AI engineering roles"
        else:
            rel_reason = "Potentially related technical or general engineering role"

        normalized_jobs.append(
            JobSearchResultItem(
                id=job_id,
                title=title,
                company=company,
                location=location_str,
                description_snippet=snippet,
                salary_min=salary_min_val,
                salary_max=salary_max_val,
                salary_currency=salary_currency,
                salary_period=salary_period,
                posted_date=item.get("created"),
                closing_date=None,  # Honest: Adzuna does not capture employer application deadline
                status="UNVERIFIED_SEARCH_INDEX",  # Honest: Qualified search result status
                source_name="Adzuna India",
                source_url=redirect_url,
                direct_apply_url=None,  # Honest: Adzuna only provides redirect affiliate URL, no direct ATS
                is_technical=is_tech,
                role_category=role_cat,
                days_ago=days_ago,
                freshness=freshness,
                role_family=role_fam,
                role_relevance=role_rel,
                relevance_reason=rel_reason,
                seniority_level=detect_job_seniority(title, snippet),
            )
        )

    total_count = data.get("count")
    total_results = int(total_count) if total_count is not None else len(normalized_jobs)

    return JobSearchResponse(
        total_results=total_results,
        page=page,
        results_per_page=results_per_page,
        jobs=normalized_jobs,
    )
