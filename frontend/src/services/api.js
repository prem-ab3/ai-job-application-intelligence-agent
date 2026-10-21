const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

/**
 * Sends resume and job description to the backend analysis endpoint.
 *
 * @param {string} resumeText
 * @param {string} jobDescription
 * @returns {Promise<object>} AnalysisJobResponse matching backend schema
 */
export async function analyzeApplication(resumeText, jobDescription) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        resume_text: resumeText,
        job_description: jobDescription,
      }),
    });
  } catch (networkErr) {
    throw new Error(
      'Unable to connect to the backend server at ' +
      API_BASE_URL +
      '. Please make sure the FastAPI server is running.'
    );
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    let errorMessage = 'Failed to analyze application.';
    if (data && data.detail) {
      if (Array.isArray(data.detail)) {
        // Handle FastAPI validation error list
        errorMessage = data.detail
          .map((err) => `${err.loc ? err.loc.join('.') + ': ' : ''}${err.msg || 'Invalid field'}`)
          .join(' | ');
      } else if (typeof data.detail === 'string') {
        errorMessage = data.detail;
      }
    } else {
      errorMessage = `Server returned error (${response.status}: ${response.statusText})`;
    }
    throw new Error(errorMessage);
  }

  return data;
}

/**
 * Uploads a PDF or DOCX file to /api/v1/resumes/upload and returns extracted text.
 *
 * @param {File} file
 * @returns {Promise<{ filename: string, extracted_text: string, character_count: number }>}
 */
export async function uploadResumeFile(file) {
  let response;
  const formData = new FormData();
  formData.append('file', file);

  try {
    response = await fetch(`${API_BASE_URL}/api/v1/resumes/upload`, {
      method: 'POST',
      body: formData,
    });
  } catch (networkErr) {
    throw new Error(
      'Unable to connect to the backend server at ' +
      API_BASE_URL +
      '. Please make sure the FastAPI server is running.'
    );
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    let errorMessage = 'Failed to extract text from resume file.';
    if (data && data.detail) {
      if (Array.isArray(data.detail)) {
        errorMessage = data.detail.map((err) => err.msg || 'Invalid upload').join(' | ');
      } else if (typeof data.detail === 'string') {
        errorMessage = data.detail;
      }
    } else {
      errorMessage = `Upload error (${response.status}: ${response.statusText})`;
    }
    throw new Error(errorMessage);
  }

  return data;
}

// In-memory caches to protect API quotas and avoid redundant requests
const searchCache = new Map();
const matchCache = new Map();

/**
 * Searches jobs via the backend /api/v1/jobs/search endpoint.
 * Utilizes an in-memory cache to prevent duplicate requests with unchanged parameters.
 *
 * @param {object} [params]
 * @param {string} [params.keywords]
 * @param {string} [params.location]
 * @param {number} [params.page=1]
 * @param {number} [params.resultsPerPage=10]
 * @param {string} [params.sortBy='date']
 * @param {number|null} [params.maxDaysOld=null]
 * @returns {Promise<{ total_results: number, page: number, results_per_page: number, jobs: Array }>}
 */
export async function searchJobs({
  keywords = '',
  location = '',
  page = 1,
  resultsPerPage = 10,
  sortBy = 'date',
  maxDaysOld = null,
} = {}) {
  const cacheKey = `${keywords.trim().toLowerCase()}::${location.trim().toLowerCase()}::${page}::${resultsPerPage}::${sortBy}::${maxDaysOld}`;
  if (searchCache.has(cacheKey)) {
    return searchCache.get(cacheKey);
  }

  const queryParams = new URLSearchParams();
  if (keywords && keywords.trim()) {
    queryParams.append('keywords', keywords.trim());
  }
  if (location && location.trim()) {
    queryParams.append('location', location.trim());
  }
  queryParams.append('page', String(page));
  queryParams.append('results_per_page', String(resultsPerPage));
  if (sortBy && sortBy.trim()) {
    queryParams.append('sort_by', sortBy.trim());
  }
  if (typeof maxDaysOld === 'number' && maxDaysOld > 0) {
    queryParams.append('max_days_old', String(maxDaysOld));
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/jobs/search?${queryParams.toString()}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });
  } catch (networkErr) {
    throw new Error(
      'Unable to connect to the backend server at ' +
      API_BASE_URL +
      '. Please make sure the FastAPI server is running.'
    );
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    let errorMessage = 'Failed to fetch jobs.';
    if (data && data.detail) {
      if (Array.isArray(data.detail)) {
        errorMessage = data.detail
          .map((err) => `${err.loc ? err.loc.join('.') + ': ' : ''}${err.msg || 'Invalid parameter'}`)
          .join(' | ');
      } else if (typeof data.detail === 'string') {
        errorMessage = data.detail;
      }
    } else {
      errorMessage = `Server returned error (${response.status}: ${response.statusText})`;
    }
    throw new Error(errorMessage);
  }

  searchCache.set(cacheKey, data);
  return data;
}

/**
 * Matches and ranks multiple target jobs against candidate resume.
 * Utilizes an in-memory cache to prevent duplicate Gemini evaluation calls.
 *
 * @param {object} params
 * @param {string} params.resumeText
 * @param {Array<object>} params.jobs
 * @returns {Promise<{ total_jobs: number, ranked_jobs: Array, unranked_jobs: Array }>}
 */
export async function matchJobsWithResume({ resumeText, jobs }) {
  const resumeFingerprint = resumeText.trim().slice(0, 200) + '::' + resumeText.trim().length;
  const jobIds = jobs.map((j) => String(j.id)).sort().join(',');
  const matchCacheKey = `${resumeFingerprint}::${jobIds}`;

  if (matchCache.has(matchCacheKey)) {
    return matchCache.get(matchCacheKey);
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/jobs/match`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        resume_text: resumeText,
        jobs: jobs.map((j) => ({
          id: String(j.id),
          title: j.title || 'Untitled Position',
          company: j.company || 'Undisclosed Company',
          description: j.description_snippet || j.description || '',
          location: j.location || 'India',
          source_url: j.source_url || '',
          is_technical: j.is_technical !== undefined ? j.is_technical : true,
          role_category: j.role_category || 'TECHNICAL',
          days_ago: j.days_ago !== undefined ? j.days_ago : null,
          freshness: j.freshness || 'RECENT',
          role_family: j.role_family || 'SOFTWARE_AI',
          role_relevance: j.role_relevance || 'DIRECT_FIT',
          seniority_level: j.seniority_level || null,
        })),
      }),
    });
  } catch (networkErr) {
    throw new Error(
      'Unable to connect to the backend server at ' +
      API_BASE_URL +
      '. Please make sure the FastAPI server is running.'
    );
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    let errorMessage = 'Failed to evaluate job matches.';
    if (data && data.detail) {
      if (Array.isArray(data.detail)) {
        errorMessage = data.detail
          .map((err) => `${err.loc ? err.loc.join('.') + ': ' : ''}${err.msg || 'Invalid parameter'}`)
          .join(' | ');
      } else if (typeof data.detail === 'string') {
        errorMessage = data.detail;
      }
    } else {
      errorMessage = `Server returned error (${response.status}: ${response.statusText})`;
    }
    throw new Error(errorMessage);
  }

  matchCache.set(matchCacheKey, data);
  return data;
}
