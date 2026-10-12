import React from 'react';

const MIN_LENGTH = 20;

export default function InputForm({
  resumeText,
  setResumeText,
  jobDescription,
  setJobDescription,
  onSubmit,
  onReset,
  isLoading,
}) {
  const resumeLen = resumeText.trim().length;
  const jdLen = jobDescription.trim().length;

  const isResumeValid = resumeLen >= MIN_LENGTH;
  const isJdValid = jdLen >= MIN_LENGTH;
  const canSubmit = isResumeValid && isJdValid && !isLoading;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (canSubmit) {
      onSubmit();
    }
  };

  return (
    <form className="form-card" onSubmit={handleSubmit}>
      <div className="form-grid">
        {/* Resume Input */}
        <div className="input-group">
          <div className="input-header">
            <label htmlFor="resume-input" className="input-label">
              Resume Text
            </label>
            <span className={`char-counter ${resumeLen > 0 && !isResumeValid ? 'error' : ''}`}>
              {resumeLen} chars {resumeLen < MIN_LENGTH ? `(min ${MIN_LENGTH})` : ''}
            </span>
          </div>
          <textarea
            id="resume-input"
            className="text-area"
            value={resumeText}
            onChange={(e) => setResumeText(e.target.value)}
            placeholder="Paste raw resume text here (experience, skills, projects, education)..."
            disabled={isLoading}
            required
          />
        </div>

        {/* Job Description Input */}
        <div className="input-group">
          <div className="input-header">
            <label htmlFor="jd-input" className="input-label">
              Job Description
            </label>
            <span className={`char-counter ${jdLen > 0 && !isJdValid ? 'error' : ''}`}>
              {jdLen} chars {jdLen < MIN_LENGTH ? `(min ${MIN_LENGTH})` : ''}
            </span>
          </div>
          <textarea
            id="jd-input"
            className="text-area"
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste target job description here (requirements, qualifications, responsibilities)..."
            disabled={isLoading}
            required
          />
        </div>
      </div>

      <div className="form-actions">
        {(resumeText || jobDescription) && (
          <button
            type="button"
            className="reset-btn"
            onClick={onReset}
            disabled={isLoading}
          >
            Clear Inputs
          </button>
        )}
        <button
          type="submit"
          className="submit-btn"
          disabled={!canSubmit}
        >
          {isLoading ? (
            <>
              <span className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }}></span>
              Analyzing...
            </>
          ) : (
            'Analyze Match'
          )}
        </button>
      </div>
    </form>
  );
}
