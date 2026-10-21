"""Single-agent orchestrator for analyzing resumes against job descriptions."""

import json
import logging
import re
from typing import Any, Dict

from app.agent.client import get_genai_client
from app.agent.prompts import (
    BATCH_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_analysis_prompt,
    build_batch_matching_prompt,
)
from app.agent.tools import calculate_deterministic_score, verify_and_adjust_skills
from app.config import settings
from app.schemas import (
    AgentAnalysisOutput,
    BatchEvaluationOutput,
    BatchJobMatchResponse,
    JobMatchRankedItem,
    JobMatchTarget,
    SkillMatchDetail,
)
from app.services.adzuna_client import (
    classify_role_family_and_relevance,
    detect_candidate_seniority,
    detect_job_seniority,
    evaluate_seniority_alignment,
)

logger = logging.getLogger(__name__)


class AgentAnalysisError(Exception):
    """Raised when the AI analysis pipeline fails."""
    pass


def _clean_json_text(raw_text: str) -> str:
    """Strips markdown code fence wrappers (```json ... ```) and extracts JSON object/array substring."""
    cleaned = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if match:
        cleaned = match.group(1).strip()
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return cleaned[first_brace : last_brace + 1]
    return cleaned


def call_gemini_interactions_with_fallback(client: Any, prompt: str, system_instruction: str) -> str:
    """
    Executes Gemini AI call with automatic model failover across candidate models
    to prevent temporary 503 high-demand or outage failures from blocking analysis.
    """
    candidate_models = [settings.GEMINI_MODEL, "gemini-3.5-flash-lite", "gemini-flash-lite-latest"]
    seen = set()
    models_to_try = [m for m in candidate_models if not (m in seen or seen.add(m))]

    last_error = None
    for model_name in models_to_try:
        try:
            logger.info("Calling Gemini with model: %s", model_name)
            response = client.interactions.create(
                model=model_name,
                input=prompt,
                system_instruction=system_instruction,
            )
            raw_output = getattr(response, "output_text", None)
            if raw_output and raw_output.strip():
                logger.info("GEMINI RESPONSE:\n%s", raw_output)
                return raw_output
            logger.warning("Empty output text from Gemini model %s, trying next...", model_name)
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Gemini model %s failed (%s: %s). Trying next available fallback model...",
                model_name,
                type(exc).__name__,
                str(exc)[:120],
            )

    logger.error("All Gemini candidate models failed to return a valid response.")
    raise AgentAnalysisError(f"AI service unavailable across all model endpoints: {type(last_error).__name__}") from last_error


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
        raw_output = call_gemini_interactions_with_fallback(
            client=client,
            prompt=prompt,
            system_instruction=SYSTEM_PROMPT,
        )
    except Exception as exc:
        logger.error("Single-application AI analysis failed: %s", type(exc).__name__)
        raise AgentAnalysisError("AI service unavailable. Please try again later.") from exc

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


def match_multiple_jobs(
    resume_text: str,
    jobs: list[JobMatchTarget],
) -> BatchJobMatchResponse:
    """
    Evaluates candidate resume against multiple target jobs and ranks reliable matches.
    1. Segregates unrelated roles (e.g. Healthcare, Logistics, Non-Tech Sales) to unranked_jobs
       with ROLE_MISMATCH status and score=None without calling Gemini, protecting API quota and score integrity.
    2. Segregates jobs with insufficient descriptions (< 40 chars) to unranked_jobs without calling Gemini.
    3. Sends remaining eligible jobs to Gemini in a single batch prompt.
    4. Verifies evidence quotes against candidate resume using Python (reusing verify_and_adjust_skills).
    5. Computes deterministic scores (reusing calculate_deterministic_score).
    6. Fully separates reliable jobs (ranked descending 1..N) from insufficient/mismatched/unreliable jobs (unranked, score=None).
    """
    if not jobs:
        return BatchJobMatchResponse(total_jobs=0, ranked_jobs=[], unranked_jobs=[])

    MIN_DESCRIPTION_CHARS = 40
    eligible_jobs: list[JobMatchTarget] = []
    unranked_jobs: list[JobMatchRankedItem] = []

    for job in jobs:
        desc = (job.description or "").strip()

        # Check role-family relevance deterministically
        is_tech, role_cat, role_fam, role_rel = classify_role_family_and_relevance(job.title, desc)
        is_unrelated = (
            (job.role_relevance == "UNRELATED_ROLE")
            or (role_rel == "UNRELATED_ROLE")
            or (job.is_technical is False)
            or (not is_tech)
        )

        if is_unrelated:
            effective_fam = role_fam if role_fam != "SOFTWARE_AI" else (job.role_family or role_fam)
            unranked_jobs.append(
                JobMatchRankedItem(
                    job_id=job.id,
                    title=job.title,
                    company=job.company or "Undisclosed Company",
                    location=job.location or "India",
                    source_url=job.source_url or "",
                    match_score=None,
                    is_reliable=False,
                    match_status="ROLE_MISMATCH",
                    matched_skills=[],
                    missing_skills=[],
                    suggestions=(
                        f"Listing belongs to the {effective_fam.replace('_', ' ').title()} career domain, "
                        "which does not match software engineering profiles. Skills matching was not conducted to protect score integrity."
                    ),
                    rank=None,
                    is_technical=False,
                    role_category="NON_TECHNICAL",
                    days_ago=job.days_ago,
                    freshness=job.freshness or "RECENT",
                    role_family=effective_fam,
                    role_relevance="UNRELATED_ROLE",
                    relevance_reason=(
                        f"Excluded from match ranking because the position belongs to the {effective_fam.replace('_', ' ').title()} career domain."
                    ),
                )
            )
        elif len(desc) < MIN_DESCRIPTION_CHARS:
            unranked_jobs.append(
                JobMatchRankedItem(
                    job_id=job.id,
                    title=job.title,
                    company=job.company or "Undisclosed Company",
                    location=job.location or "India",
                    source_url=job.source_url or "",
                    match_score=None,
                    is_reliable=False,
                    match_status="INSUFFICIENT_DESCRIPTION",
                    matched_skills=[],
                    missing_skills=[],
                    suggestions="The job description snippet is too brief to extract required competencies reliably. Please refer to the direct source listing.",
                    rank=None,
                    is_technical=job.is_technical if job.is_technical is not None else is_tech,
                    role_category=job.role_category or role_cat,
                    days_ago=job.days_ago,
                    freshness=job.freshness or "RECENT",
                    role_family=job.role_family or role_fam,
                    role_relevance=job.role_relevance or role_rel,
                    relevance_reason="Description snippet is insufficient for reliable extraction.",
                )
            )
        else:
            eligible_jobs.append(job)

    if not eligible_jobs:
        return BatchJobMatchResponse(
            total_jobs=len(jobs),
            ranked_jobs=[],
            unranked_jobs=unranked_jobs,
        )

    # Process eligible jobs via Gemini batch prompt with model failover
    client = get_genai_client()
    prompt = build_batch_matching_prompt(resume_text=resume_text, jobs=eligible_jobs)
    cand_seniority = detect_candidate_seniority(resume_text)

    try:
        raw_output = call_gemini_interactions_with_fallback(
            client=client,
            prompt=prompt,
            system_instruction=BATCH_SYSTEM_PROMPT,
        )
        cleaned_json = _clean_json_text(raw_output)
        data = json.loads(cleaned_json)
        batch_output = BatchEvaluationOutput.model_validate(data)
    except Exception as exc:
        logger.error("Batch evaluation failed: %s (%s)", type(exc).__name__, str(exc)[:150])
        # Fallback for eligible jobs: do not invent skills or crash
        for job in eligible_jobs:
            job_sen = job.seniority_level or detect_job_seniority(job.title, job.description or "")
            unranked_jobs.append(
                JobMatchRankedItem(
                    job_id=job.id,
                    title=job.title,
                    company=job.company or "Undisclosed Company",
                    location=job.location or "India",
                    source_url=job.source_url or "",
                    match_score=None,
                    is_reliable=False,
                    match_status="EVALUATION_FAILED",
                    matched_skills=[],
                    missing_skills=[],
                    suggestions="Evaluation could not be completed due to a temporary service issue. Please try again.",
                    rank=None,
                    is_technical=job.is_technical if job.is_technical is not None else True,
                    role_category=job.role_category or "TECHNICAL",
                    days_ago=job.days_ago,
                    freshness=job.freshness or "RECENT",
                    role_family=job.role_family or "SOFTWARE_AI",
                    role_relevance=job.role_relevance or "DIRECT_FIT",
                    relevance_reason=job.role_relevance or "Evaluated technical role",
                    match_explanation="Evaluation could not be completed due to a temporary service issue. Please click retry.",
                    seniority_level=job_sen,
                    seniority_alignment="UNKNOWN",
                )
            )
        return BatchJobMatchResponse(
            total_jobs=len(jobs),
            ranked_jobs=[],
            unranked_jobs=unranked_jobs,
        )

    eval_by_id = {eval_item.job_id: eval_item for eval_item in batch_output.evaluations}

    reliable_matches: list[JobMatchRankedItem] = []

    for job in eligible_jobs:
        job_sen = job.seniority_level or detect_job_seniority(job.title, job.description or "")
        sen_alignment, sen_multiplier = evaluate_seniority_alignment(cand_seniority, job_sen)

        job_eval = eval_by_id.get(job.id)
        if not job_eval:
            unranked_jobs.append(
                JobMatchRankedItem(
                    job_id=job.id,
                    title=job.title,
                    company=job.company or "Undisclosed Company",
                    location=job.location or "India",
                    source_url=job.source_url or "",
                    match_score=None,
                    is_reliable=False,
                    match_status="EVALUATION_FAILED",
                    matched_skills=[],
                    missing_skills=[],
                    suggestions="Job was not included in model evaluation response.",
                    rank=None,
                    is_technical=job.is_technical if job.is_technical is not None else True,
                    role_category=job.role_category or "TECHNICAL",
                    days_ago=job.days_ago,
                    freshness=job.freshness or "RECENT",
                    role_family=job.role_family or "SOFTWARE_AI",
                    role_relevance=job.role_relevance or "DIRECT_FIT",
                    relevance_reason="Evaluated technical role",
                    match_explanation="Job omitted from model output; manual evaluation required.",
                    seniority_level=job_sen,
                    seniority_alignment=sen_alignment,
                )
            )
            continue

        # 1. Enforce evidence verification in Python
        verified_skills = verify_and_adjust_skills(
            skills=job_eval.skills,
            resume_text=resume_text,
        )

        # 2. Deterministic scoring in Python
        base_score, is_reliable = calculate_deterministic_score(verified_skills)

        matched_skills_list: list[SkillMatchDetail] = []
        missing_skills_list: list[SkillMatchDetail] = []

        for s in verified_skills:
            detail = SkillMatchDetail(
                skill_name=s.skill_name,
                category=s.category,
                is_matched=s.is_matched,
                resume_evidence=s.resume_evidence,
                is_verified_evidence=bool(s.is_matched and s.resume_evidence),
            )
            if s.is_matched:
                matched_skills_list.append(detail)
            else:
                missing_skills_list.append(detail)

        suggestions_text = (job_eval.suggestions or "").strip()

        # Build clear match explanation
        explanation = (job_eval.match_explanation or "").strip()
        if not explanation:
            matched_names = [s.skill_name for s in matched_skills_list[:3]]
            matched_snippet = f"Matches verified competencies ({', '.join(matched_names)})" if matched_names else "Limited matching competencies identified"
            if sen_multiplier < 1.0:
                sen_note = f"Position targets {job_sen.replace('_', ' ').title()} candidates (seniority adjustment applied for {cand_seniority.replace('_', ' ').title()} profile)."
            else:
                sen_note = f"Experience requirements align well with your {cand_seniority.replace('_', ' ').title()} profile."
            explanation = f"{matched_snippet}. {sen_note}"

        if is_reliable:
            # Apply seniority multiplier to balance entry/junior vs senior/architect roles
            adjusted_score = round(min(100.0, base_score * sen_multiplier), 1)

            reliable_matches.append(
                JobMatchRankedItem(
                    job_id=job.id,
                    title=job.title,
                    company=job.company or "Undisclosed Company",
                    location=job.location or "India",
                    source_url=job.source_url or "",
                    match_score=adjusted_score,
                    is_reliable=True,
                    match_status="RELIABLE_MATCH",
                    matched_skills=matched_skills_list,
                    missing_skills=missing_skills_list,
                    suggestions=suggestions_text,
                    rank=None,
                    is_technical=job.is_technical if job.is_technical is not None else True,
                    role_category=job.role_category or "TECHNICAL",
                    days_ago=job.days_ago,
                    freshness=job.freshness or "RECENT",
                    role_family=job.role_family or "SOFTWARE_AI",
                    role_relevance=job.role_relevance or "DIRECT_FIT",
                    relevance_reason="Verified technical match",
                    match_explanation=explanation,
                    seniority_level=job_sen,
                    seniority_alignment=sen_alignment,
                )
            )
        else:
            unranked_jobs.append(
                JobMatchRankedItem(
                    job_id=job.id,
                    title=job.title,
                    company=job.company or "Undisclosed Company",
                    location=job.location or "India",
                    source_url=job.source_url or "",
                    match_score=None,
                    is_reliable=False,
                    match_status="INSUFFICIENT_REQUIREMENTS",
                    matched_skills=matched_skills_list,
                    missing_skills=missing_skills_list,
                    suggestions=(
                        "[Notice: Insufficient required skills identified in the job description "
                        "for reliable deterministic scoring.]\n\n" + suggestions_text
                    ).strip(),
                    rank=None,
                    is_technical=job.is_technical if job.is_technical is not None else True,
                    role_category=job.role_category or "TECHNICAL",
                    days_ago=job.days_ago,
                    freshness=job.freshness or "RECENT",
                    role_family=job.role_family or "SOFTWARE_AI",
                    role_relevance=job.role_relevance or "DIRECT_FIT",
                    relevance_reason="Inadequate required competencies for scoring",
                    match_explanation="Not enough specific technical requirements in listing for reliable competency scoring.",
                    seniority_level=job_sen,
                    seniority_alignment=sen_alignment,
                )
            )

    # Sort reliable matches descending by match_score
    reliable_matches.sort(key=lambda j: j.match_score if j.match_score is not None else -1.0, reverse=True)

    # Assign ranks 1..N to reliably evaluated jobs
    for idx, item in enumerate(reliable_matches, start=1):
        item.rank = idx

    return BatchJobMatchResponse(
        total_jobs=len(jobs),
        ranked_jobs=reliable_matches,
        unranked_jobs=unranked_jobs,
    )
