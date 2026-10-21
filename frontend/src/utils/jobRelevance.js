/**
 * Job relevance, role-family classification, and freshness filtering utility.
 * Deterministically filters jobs and classifies non-technical or stale listings
 * without relying on LLM match scores.
 */

const HEALTHCARE_REGEX = /\b(orthopedic|orthopaedics|surgeon|doctor|physician|nurse|nursing|dentist|dental|clinic|clinical|hospital|radiology|pharmacist|pathology|cardiologist|pediatrician|consultant\s+orthopedics)\b/i;

const LOGISTICS_REGEX = /\b(inventory\s+manager|inventory\s+executive|warehouse|storekeeper|supply\s+chain|procurement|materials\s+manager|dispatch\s+executive|fleet\s+manager)\b/i;

const MANUFACTURING_HARDWARE_REGEX = /\b(supplier\s+quality\s+assurance|supplier\s+qa|sqa\s+engineer|mechanical\s+engineer|civil\s+engineer|site\s+engineer|welding|plant\s+supervisor|hvac)\b/i;

const SALES_RETAIL_REGEX = /\b(inside\s+sales|sales\s+associate|sales\s+executive|sales\s+manager|telecaller|tele-sales|telesales|business\s+development\s+executive|bde\b|bpo\b|retail\s+associate|real\s+estate|realtor|store\s+manager|cashier|insurance\s+agent|front\s+desk|receptionist)\b/i;

const FINANCE_REGEX = /\b(chartered\s+accountant|teller|loan\s+officer|bookkeeper|audit\s+associate|tax\s+consultant)\b/i;

const TECHNICAL_REGEX = /\b(developer|software|engineer|architect|programmer|coder|data\s+scientist|machine\s+learning|ai\b|artificial\s+intelligence|backend|frontend|full\s+stack|fullstack|devops|sre\b|cloud|python|java\b|react|fastapi|golang|c\+\+|node\.?js|sdet|test\s+automation)\b/i;

/**
 * Classifies whether a job posting is a technical / software engineering role.
 *
 * @param {object} job
 * @returns {{ isTechnical: boolean, category: string, family: string, relevance: string, reason: string }}
 */
export function checkJobRelevance(job) {
  if (!job) {
    return {
      isTechnical: true,
      category: 'TECHNICAL',
      family: 'SOFTWARE_AI',
      relevance: 'DIRECT_FIT',
      reason: 'Default',
    };
  }

  // Honor backend pre-classification if present
  if (job.role_relevance === 'UNRELATED_ROLE' || job.is_technical === false || job.role_category === 'NON_TECHNICAL') {
    return {
      isTechnical: false,
      category: 'NON_TECHNICAL',
      family: job.role_family || 'OTHER',
      relevance: 'UNRELATED_ROLE',
      reason: job.relevance_reason || 'Classified as non-technical career family',
    };
  }

  const title = (job.title || '').trim();
  const snippet = (job.description_snippet || job.description || '').trim();

  if (HEALTHCARE_REGEX.test(title)) {
    return { isTechnical: false, category: 'NON_TECHNICAL', family: 'HEALTHCARE', relevance: 'UNRELATED_ROLE', reason: 'Healthcare role' };
  }
  if (LOGISTICS_REGEX.test(title)) {
    return { isTechnical: false, category: 'NON_TECHNICAL', family: 'LOGISTICS', relevance: 'UNRELATED_ROLE', reason: 'Logistics / Warehouse role' };
  }
  if (MANUFACTURING_HARDWARE_REGEX.test(title)) {
    return { isTechnical: false, category: 'NON_TECHNICAL', family: 'MANUFACTURING_HARDWARE', relevance: 'UNRELATED_ROLE', reason: 'Hardware / Manufacturing QA role' };
  }
  if (SALES_RETAIL_REGEX.test(title)) {
    return { isTechnical: false, category: 'NON_TECHNICAL', family: 'SALES_BPO', relevance: 'UNRELATED_ROLE', reason: 'Sales / BPO role' };
  }
  if (FINANCE_REGEX.test(title)) {
    return { isTechnical: false, category: 'NON_TECHNICAL', family: 'FINANCE', relevance: 'UNRELATED_ROLE', reason: 'Finance / Accounting role' };
  }

  const hasTechInTitle = TECHNICAL_REGEX.test(title);
  const hasTechInSnippet = TECHNICAL_REGEX.test(snippet);

  if (hasTechInTitle) {
    return { isTechnical: true, category: 'TECHNICAL', family: 'SOFTWARE_AI', relevance: 'DIRECT_FIT', reason: 'Software & AI engineering position' };
  }
  if (hasTechInSnippet) {
    return { isTechnical: true, category: 'TECHNICAL', family: 'SOFTWARE_AI', relevance: 'RELATED_TECH', reason: 'Technical engineering position' };
  }

  return { isTechnical: true, category: 'GENERAL', family: 'OTHER', relevance: 'RELATED_TECH', reason: 'General position' };
}

/**
 * Checks if a listing is stale based on days_ago or created date.
 *
 * @param {object} job
 * @param {number} [maxDays=90]
 * @returns {boolean} True if older than maxDays
 */
export function isListingStale(job, maxDays = 90) {
  if (!job) return false;
  if (typeof job.days_ago === 'number') {
    return job.days_ago > maxDays;
  }
  if (job.freshness === 'STALE') {
    return true;
  }
  if (job.posted_date) {
    try {
      const createdDt = new Date(job.posted_date);
      const now = new Date();
      const diffDays = Math.max(0, Math.floor((now - createdDt) / (1000 * 60 * 60 * 24)));
      return diffDays > maxDays;
    } catch {
      return false;
    }
  }
  return false;
}

/**
 * Filters a list of jobs based on active role filter and freshness policy.
 *
 * @param {Array} jobs
 * @param {string} [roleFilter='technical'] - 'technical' | 'all'
 * @param {string} [freshnessFilter='recent_90'] - 'recent_90' | 'all'
 * @returns {{
 *   visibleJobs: Array,
 *   excludedCount: number,
 *   excludedNonTechCount: number,
 *   excludedStaleCount: number,
 *   excludedJobs: Array
 * }}
 */
export function filterJobsByRelevance(jobs, roleFilter = 'technical', freshnessFilter = 'recent_90') {
  if (!Array.isArray(jobs) || jobs.length === 0) {
    return {
      visibleJobs: [],
      excludedCount: 0,
      excludedNonTechCount: 0,
      excludedStaleCount: 0,
      excludedJobs: [],
    };
  }

  const visibleJobs = [];
  const excludedJobs = [];
  let excludedNonTechCount = 0;
  let excludedStaleCount = 0;

  for (const job of jobs) {
    const classification = checkJobRelevance(job);
    const isStale = freshnessFilter === 'recent_90' && isListingStale(job, 90);
    const isExcludedByRole = roleFilter === 'technical' && !classification.isTechnical;

    if (isExcludedByRole) {
      excludedNonTechCount += 1;
      excludedJobs.push({ ...job, exclusionReason: 'Non-technical role family' });
    } else if (isStale) {
      excludedStaleCount += 1;
      excludedJobs.push({ ...job, exclusionReason: 'Stale listing (> 90 days old)' });
    } else {
      visibleJobs.push(job);
    }
  }

  return {
    visibleJobs,
    excludedCount: excludedJobs.length,
    excludedNonTechCount,
    excludedStaleCount,
    excludedJobs,
  };
}
