import React, { useState } from 'react';

/**
 * Validates that a URL is a legitimate http or https link.
 *
 * @param {string} url
 * @returns {boolean}
 */
function isValidExternalUrl(url) {
  if (!url || typeof url !== 'string') return false;
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

/**
 * Formats numbers in Indian numbering system (e.g., 12,00,000).
 *
 * @param {number} num
 * @returns {string}
 */
function formatINR(num) {
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(num);
}

/**
 * Formats salary safely handling nulls, zeros, and one-sided ranges.
 *
 * @param {number|null} min
 * @param {number|null} max
 * @param {string|null} currency
 * @param {string} period
 * @returns {string}
 */
function formatSalary(min, max, currency = 'INR', period = 'annual') {
  const hasMin = typeof min === 'number' && min > 0;
  const hasMax = typeof max === 'number' && max > 0;

  if (!hasMin && !hasMax) {
    return 'Salary not disclosed';
  }

  const periodLabel = period === 'annual' ? '/ year' : period === 'monthly' ? '/ month' : '';
  const prefix = currency === 'INR' ? '₹' : `${currency} `;

  if (hasMin && hasMax) {
    if (min === max) {
      return `${prefix}${formatINR(min)} ${periodLabel}`.trim();
    }
    return `${prefix}${formatINR(min)} – ${prefix}${formatINR(max)} ${periodLabel}`.trim();
  }

  if (hasMin) {
    return `From ${prefix}${formatINR(min)} ${periodLabel}`.trim();
  }

  return `Up to ${prefix}${formatINR(max)} ${periodLabel}`.trim();
}

/**
 * Formats ISO date string to human-readable date.
 *
 * @param {string|null} dateString
 * @returns {string}
 */
function formatDate(dateString) {
  if (!dateString) return 'Date not specified';
  try {
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString;
    return d.toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateString;
  }
}

export default function JobCard({ job }) {
  const [showMatchDetails, setShowMatchDetails] = useState(false);

  if (!job) return null;

  const validSourceUrl = isValidExternalUrl(job.source_url);
  const validApplyUrl = isValidExternalUrl(job.direct_apply_url);
  const match = job.match;

  const getScoreColorClass = (score) => {
    if (score >= 75) return 'score-high';
    if (score >= 50) return 'score-mid';
    return 'score-low';
  };

  const roleFamily = job.role_family || match?.role_family || 'SOFTWARE_AI';
  const roleRelevance = job.role_relevance || match?.role_relevance || 'DIRECT_FIT';
  const freshness = job.freshness || match?.freshness || 'RECENT';
  const daysAgo = typeof job.days_ago === 'number' ? job.days_ago : match?.days_ago;

  return (
    <article className={`job-card ${match?.rank === 1 ? 'best-match-highlight' : ''} ${roleRelevance === 'UNRELATED_ROLE' ? 'job-card-unrelated' : ''}`}>
      <div className="job-card-top">
        <div className="job-main-info">
          <div className="job-title-row">
            {match?.rank && (
              <span className="job-rank-pill" title={`Ranked #${match.rank} by resume match`}>
                #{match.rank}
              </span>
            )}
            <h3 className="job-title">{job.title || 'Untitled Position'}</h3>
          </div>

          <div className="job-company-location">
            <span className="job-company">🏢 {job.company || 'Undisclosed Company'}</span>
            <span className="job-separator">•</span>
            <span className="job-location">📍 {job.location || 'India'}</span>
          </div>
        </div>

        <div className="job-badges-group">
          {/* 1. Role Domain Relevance Badge */}
          {roleRelevance === 'UNRELATED_ROLE' ? (
            <span
              className="badge-role-domain unrelated"
              title="Career domain differs from software engineering"
            >
              ⚠️ Unrelated: {roleFamily.replace('_', ' ').toLowerCase()}
            </span>
          ) : roleRelevance === 'DIRECT_FIT' ? (
            <span
              className="badge-role-domain tech-fit"
              title="Direct fit with Software & AI engineering roles"
            >
              💻 Tech / AI Role
            </span>
          ) : (
            <span
              className="badge-role-domain related-tech"
              title="Related technical position"
            >
              ⚙️ Technical Role
            </span>
          )}

          {/* 2. Posting Freshness Badge */}
          {freshness === 'RECENT' ? (
            <span
              className="badge-freshness recent"
              title="Posted recently (within 30 days)"
            >
              🟢 Recent {daysAgo !== null && daysAgo !== undefined ? `(${daysAgo}d ago)` : ''}
            </span>
          ) : freshness === 'MODERATE' ? (
            <span
              className="badge-freshness moderate"
              title="Posted 31-90 days ago"
            >
              🟡 {daysAgo !== null && daysAgo !== undefined ? `${daysAgo}d ago` : '1-3mo ago'}
            </span>
          ) : freshness === 'STALE' ? (
            <span
              className="badge-freshness stale"
              title="Older listing (> 90 days ago) - current vacancy may be unverified"
            >
              ⚪ Older {daysAgo !== null && daysAgo !== undefined ? `(${daysAgo}d ago)` : '(>90d)'}
            </span>
          ) : null}

          {/* 3. Seniority Fit Badge */}
          {(match?.seniority_level || job.seniority_level) && (
            <span
              className={`badge-seniority ${
                match?.seniority_alignment?.startsWith('MISMATCH') || match?.seniority_alignment?.startsWith('EXPERIENCE_GAP')
                  ? 'seniority-gap'
                  : 'seniority-aligned'
              }`}
              title={`Seniority evaluation: ${match?.seniority_level || job.seniority_level} (${match?.seniority_alignment || 'Standard'})`}
            >
              {(match?.seniority_level || job.seniority_level) === 'ARCHITECT_LEAD'
                ? '🏛️ Lead / Architect'
                : (match?.seniority_level || job.seniority_level) === 'SENIOR'
                ? '⭐ Senior Role'
                : (match?.seniority_level || job.seniority_level) === 'ENTRY_JUNIOR'
                ? '🎓 Entry / Junior'
                : '💼 Mid-Level'}
            </span>
          )}

          {/* 4. Match Score / Status Badge */}
          {match && (
            <>
              {match.match_status === 'RELIABLE_MATCH' && match.match_score !== null ? (
                <div className="match-score-container">
                  <span
                    className={`job-score-badge ${getScoreColorClass(match.match_score)}`}
                    title="Deterministic score computed from verified resume evidence"
                  >
                    🎯 {match.match_score}% Match
                  </span>
                </div>
              ) : match.match_status === 'ROLE_MISMATCH' ? (
                <div className="match-score-container">
                  <span
                    className="job-score-badge score-mismatch"
                    title="Non-software role; match evaluation withheld"
                  >
                    🚫 Role Mismatch
                  </span>
                </div>
              ) : match.match_status === 'EVALUATION_FAILED' ? (
                <div className="match-score-container">
                  <span
                    className="job-score-badge score-unranked"
                    title="Automated analysis could not be completed for this listing"
                  >
                    ⚠️ Evaluation Failed
                  </span>
                </div>
              ) : (
                <div className="match-score-container">
                  <span
                    className="job-score-badge score-unranked"
                    title="Snippet has insufficient details for reliable scoring"
                  >
                    ⚠️ Not Enough Information
                  </span>
                </div>
              )}
            </>
          )}

          {/* 5. Index Status Badge: Honest search-index qualifier */}
          <span
            className="job-status-badge unverified"
            title="Aggregated from search index. Active vacancy has not been independently verified."
          >
            ℹ️ Unverified Search Index
          </span>
        </div>
      </div>

      <p className="job-snippet">{job.description_snippet || 'No description snippet available.'}</p>

      {/* Match Breakdown Section when matching has occurred */}
      {match && (
        <div className="job-match-section">
          {/* Match Explanation Box */}
          {match.match_explanation && (
            <div className="match-explanation-box">
              <span className="explanation-label">💡 Match Analysis:</span>
              {match.match_explanation}
            </div>
          )}

          {match.match_status === 'ROLE_MISMATCH' ? (
            <div className="role-mismatch-banner">
              <strong>Domain Mismatch:</strong> This listing belongs to an unrelated professional field (
              {roleFamily.replace('_', ' ').toLowerCase()}). Competency scoring was withheld to protect score accuracy.
            </div>
          ) : match.match_status === 'INSUFFICIENT_DESCRIPTION' || match.match_status === 'INSUFFICIENT_REQUIREMENTS' ? (
            <div className="insufficient-match-banner">
              <strong>Notice:</strong> Not enough information in the search index snippet to extract required competencies reliably. To evaluate your fit, view the full posting directly on the source.
            </div>
          ) : match.match_status === 'EVALUATION_FAILED' ? (
            <div className="insufficient-match-banner error">
              <strong>Evaluation Note:</strong> Automated analysis could not be completed for this listing. Please retry.
            </div>
          ) : (
            <div className="match-summary-accordion">
              <div className="match-summary-counts">
                <span className="summary-pill matched">
                  ✅ {match.matched_skills?.length || 0} Matched Skills
                </span>
                <span className="summary-pill missing">
                  ⚠️ {match.missing_skills?.length || 0} Missing Required/Preferred
                </span>
                <button
                  type="button"
                  className="match-toggle-btn"
                  onClick={() => setShowMatchDetails(!showMatchDetails)}
                  aria-expanded={showMatchDetails}
                >
                  {showMatchDetails ? 'Hide Details ▲' : 'View Breakdown ▼'}
                </button>
              </div>

              {showMatchDetails && (
                <div className="match-breakdown-details">
                  {/* Verified Matched Skills */}
                  {match.matched_skills && match.matched_skills.length > 0 && (
                    <div className="skills-block">
                      <h4 className="block-title verified-title">
                        ✅ Demonstrated Skills (Verified by Resume Evidence)
                      </h4>
                      <div className="skills-tags-container">
                        {match.matched_skills.map((skill, i) => (
                          <div key={i} className="skill-detail-card matched">
                            <div className="skill-tag-header">
                              <span className="skill-name">{skill.skill_name}</span>
                              <span className="skill-category-badge">{skill.category}</span>
                            </div>
                            {skill.resume_evidence && (
                              <div className="evidence-quote-box">
                                <span className="evidence-label">Verified Resume Evidence:</span>
                                <blockquote className="evidence-quote">
                                  "{skill.resume_evidence}"
                                </blockquote>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Missing Skills */}
                  {match.missing_skills && match.missing_skills.length > 0 && (
                    <div className="skills-block">
                      <h4 className="block-title missing-title">
                        ⚠️ Missing or Unsubstantiated Requirements
                      </h4>
                      <div className="skills-tags-container">
                        {match.missing_skills.map((skill, i) => (
                          <div key={i} className="skill-detail-card missing">
                            <span className="skill-name">{skill.skill_name}</span>
                            <span className="skill-category-badge">{skill.category}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* AI Improvement Suggestions */}
                  {match.suggestions && (
                    <div className="suggestions-block">
                      <h4 className="block-title suggestions-title">
                        💡 AI Improvement Recommendations
                      </h4>
                      <p className="suggestions-text">{match.suggestions}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="job-meta-grid">
        <div className="meta-item">
          <span className="meta-label">Compensation:</span>
          <span className="meta-value salary-highlight">
            {formatSalary(job.salary_min, job.salary_max, job.salary_currency, job.salary_period)}
          </span>
        </div>

        <div className="meta-item">
          <span className="meta-label">Posted:</span>
          <span className="meta-value">
            {formatDate(job.posted_date)}
          </span>
        </div>

        <div className="meta-item">
          <span className="meta-label">Closing Date:</span>
          <span className="meta-value muted">
            {job.closing_date ? formatDate(job.closing_date) : 'Not provided'}
          </span>
        </div>

        <div className="meta-item">
          <span className="meta-label">Source:</span>
          <span className="meta-value">{job.source_name || 'Adzuna India'}</span>
        </div>
      </div>

      <div className="job-card-actions">
        {validSourceUrl ? (
          <a
            href={job.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="action-btn-primary"
            title="Open listing on Adzuna India in a new tab"
          >
            View on Adzuna ↗
          </a>
        ) : (
          <span className="action-btn-disabled" title="No valid source link available">
            No source link available
          </span>
        )}

        {validApplyUrl && (
          <a
            href={job.direct_apply_url}
            target="_blank"
            rel="noopener noreferrer"
            className="action-btn-secondary"
            title="Open direct application link in a new tab"
          >
            Direct Apply ↗
          </a>
        )}
      </div>
    </article>
  );
}
