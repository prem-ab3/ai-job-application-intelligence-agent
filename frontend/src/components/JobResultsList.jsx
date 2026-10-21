import React from 'react';
import JobCard from './JobCard';

export default function JobResultsList({
  jobs,
  totalResults,
  currentPage,
  resultsPerPage,
  onPageChange,
  isLoading,
  onMatchJobs,
  isMatching,
  hasMatchResults,
  resumeLoaded,
  sortMode,
  setSortMode,
  matchStats,
}) {
  const safeTotalResults = Math.max(0, Number(totalResults) || 0);
  const totalPages = safeTotalResults > 0 ? Math.ceil(safeTotalResults / resultsPerPage) : 0;

  if (safeTotalResults === 0 || !jobs || jobs.length === 0) {
    return (
      <div className="job-empty-state">
        <div className="empty-icon">🔎</div>
        <h4 className="empty-title">No job listings found</h4>
        <p className="empty-description">
          We could not find any active postings matching your search criteria in Adzuna's India index.
          Try using broader keywords (e.g. "Software Engineer" or "Python") or clearing the location filter.
        </p>
      </div>
    );
  }

  const isFirstPage = currentPage <= 1;
  const isLastPage = currentPage >= totalPages;

  return (
    <div className="job-results-container">
      {/* Top Matching & Ranking Action Toolbar */}
      <div className="matching-controls-bar">
        <div className="matching-cta-group">
          <button
            type="button"
            className="match-all-btn"
            onClick={onMatchJobs}
            disabled={isMatching || isLoading || !resumeLoaded}
            title={
              !resumeLoaded
                ? 'Please upload or enter a resume first to enable matching'
                : 'Evaluate and rank all current listings against your resume'
            }
          >
            {isMatching
              ? '⏳ Matching & Ranking Jobs...'
              : hasMatchResults
              ? '🔄 Re-evaluate & Rank with My Resume'
              : '⚡ Match & Rank with My Resume'}
          </button>

          {!resumeLoaded && (
            <span className="resume-needed-hint">
              ℹ️ Upload or enter your resume above to rank these jobs
            </span>
          )}
        </div>

        {hasMatchResults && (
          <div className="sort-controls-group">
            <label htmlFor="sort-mode-select" className="sort-label">
              Sort by:
            </label>
            <select
              id="sort-mode-select"
              className="sort-select"
              value={sortMode}
              onChange={(e) => setSortMode(e.target.value)}
            >
              <option value="match">Highest Match Score</option>
              <option value="original">Original Search Order</option>
            </select>
          </div>
        )}
      </div>

      {hasMatchResults && matchStats && (
        <div className="match-stats-banner">
          <span>
            {matchStats.ranked > 0 ? (
              <>
                🎯 <strong>{matchStats.ranked}</strong> job{matchStats.ranked === 1 ? '' : 's'} reliably ranked
              </>
            ) : (
              <>
                ℹ️ <strong>0 jobs reliably ranked</strong>
              </>
            )}
            {matchStats.insufficient > 0 && (
              <> • <strong>{matchStats.insufficient}</strong> with insufficient details</>
            )}
            {matchStats.roleMismatch > 0 && (
              <> • <strong>{matchStats.roleMismatch}</strong> domain mismatches</>
            )}
            {matchStats.failed > 0 && (
              <> • <strong>{matchStats.failed}</strong> evaluation failed</>
            )}
            {matchStats.insufficient === undefined && matchStats.unranked > 0 && (
              <> • <strong>{matchStats.unranked}</strong> unranked</>
            )}
          </span>
        </div>
      )}

      <div className="results-summary-bar">
        <div className="results-count">
          <strong>{safeTotalResults.toLocaleString()}</strong> job{safeTotalResults === 1 ? '' : 's'} discovered in India
        </div>
        {totalPages > 0 && (
          <div className="results-page-info">
            Page {currentPage} of {totalPages}
          </div>
        )}
      </div>

      <div className="job-cards-list">
        {jobs.map((job) => (
          <JobCard key={job.id || `${job.title}-${job.source_url}`} job={job} />
        ))}
      </div>

      {totalPages > 1 && (
        <nav className="pagination-bar" aria-label="Job search results pagination">
          <button
            type="button"
            className="pagination-btn"
            onClick={() => onPageChange(currentPage - 1)}
            disabled={isFirstPage || isLoading || isMatching}
          >
            ← Previous
          </button>

          <span className="pagination-status">
            Page {currentPage} of {totalPages}
          </span>

          <button
            type="button"
            className="pagination-btn"
            onClick={() => onPageChange(currentPage + 1)}
            disabled={isLastPage || isLoading || isMatching}
          >
            Next →
          </button>
        </nav>
      )}
    </div>
  );
}
