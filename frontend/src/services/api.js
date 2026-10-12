const API_BASE_URL = 'http://127.0.0.1:8000';

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
