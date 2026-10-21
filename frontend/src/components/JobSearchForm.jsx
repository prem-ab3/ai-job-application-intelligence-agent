import React, { useState } from 'react';

export default function JobSearchForm({
  keywords,
  setKeywords,
  location,
  setLocation,
  resultsPerPage,
  setResultsPerPage,
  roleFilter = 'technical',
  setRoleFilter,
  freshnessFilter = 'recent_90',
  setFreshnessFilter,
  sortBy = 'date',
  setSortBy,
  resumeProfile = {},
  onSearch,
  onReset,
  isLoading,
}) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (isLoading) return;
    onSearch();
  };

  const handleSelectRoleChip = (role) => {
    setKeywords(role);
  };

  const { suggestedRoles = [], primaryRole = '', detectedLocation = '', experienceLevel = '' } = resumeProfile;

  return (
    <form className="job-search-form" onSubmit={handleSubmit}>
      {/* Primary Search Controls */}
      <div className="search-form-primary-grid">
        <div className="search-field flex-2">
          <label htmlFor="search-keywords" className="search-label">
            Target Role / Keywords <span className="label-tag-optional">(Optional)</span>
          </label>
          <input
            id="search-keywords"
            type="text"
            className="search-input"
            placeholder={
              primaryRole
                ? `e.g. ${primaryRole} (Leave empty to use resume suggestion)`
                : 'e.g. AI Engineer, Python Developer (Optional)'
            }
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            disabled={isLoading}
          />
        </div>

        <div className="search-field flex-2">
          <label htmlFor="search-location" className="search-label">
            Location in India <span className="label-tag-optional">(Optional)</span>
          </label>
          <input
            id="search-location"
            type="text"
            className="search-input"
            placeholder={
              detectedLocation
                ? `e.g. ${detectedLocation} or Remote`
                : 'e.g. Bengaluru, Pune, Hyderabad, Remote'
            }
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            disabled={isLoading}
          />
        </div>

        <div className="search-actions-inline">
          <button
            type="submit"
            className="search-submit-btn"
            disabled={isLoading}
            id="search-jobs-btn"
          >
            {isLoading ? 'Searching...' : '🔍 Search Jobs'}
          </button>

          <button
            type="button"
            className="search-reset-btn"
            onClick={onReset}
            disabled={isLoading}
          >
            Clear
          </button>
        </div>
      </div>

      {/* Dynamic Role Suggestions Row */}
      {suggestedRoles && suggestedRoles.length > 0 && (
        <div className="role-suggestions-row">
          <span className="suggestions-prompt-label">
            🎯 Resume Suggestions:
            {primaryRole && !keywords && (
              <span className="active-default-pill" title="Default search query if keywords left empty">
                Using: {primaryRole}
              </span>
            )}
            {experienceLevel && (
              <span className="experience-level-pill">Level: {experienceLevel}</span>
            )}
          </span>

          <div className="role-chips-list">
            {suggestedRoles.map((role, idx) => (
              <button
                key={idx}
                type="button"
                className={`role-chip-btn ${keywords.toLowerCase() === role.toLowerCase() ? 'active' : ''}`}
                onClick={() => handleSelectRoleChip(role)}
                disabled={isLoading}
                title={`Click to search for "${role}"`}
              >
                {role}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Expandable Advanced Filters & Freshness Controls */}
      <div className="advanced-filters-section">
        <button
          type="button"
          className="advanced-toggle-btn"
          onClick={() => setShowAdvanced(!showAdvanced)}
          aria-expanded={showAdvanced}
        >
          {showAdvanced ? '▲ Hide Advanced Filters' : '⚙️ Advanced Filters & Freshness ▼'}
        </button>

        {showAdvanced && (
          <div className="advanced-filters-panel">
            <div className="advanced-grid">
              <div className="search-field">
                <label htmlFor="search-role-filter" className="search-label">
                  Role Family Gate
                </label>
                <select
                  id="search-role-filter"
                  className="search-select"
                  value={roleFilter}
                  onChange={(e) => setRoleFilter(e.target.value)}
                  disabled={isLoading}
                  title="Filter discovered listings to technical engineering positions"
                >
                  <option value="technical">Technical Roles Only (Excludes Healthcare, Logistics, Sales)</option>
                  <option value="all">All Roles (Show All Domains)</option>
                </select>
              </div>

              <div className="search-field">
                <label htmlFor="search-freshness-filter" className="search-label">
                  Freshness Policy
                </label>
                <select
                  id="search-freshness-filter"
                  className="search-select"
                  value={freshnessFilter}
                  onChange={(e) => setFreshnessFilter(e.target.value)}
                  disabled={isLoading}
                  title="Filter out stale listings"
                >
                  <option value="recent_90">Recent Listings Only (&le; 90 Days) (Default)</option>
                  <option value="all">All Postings (Include Historical/Stale)</option>
                </select>
              </div>

              <div className="search-field">
                <label htmlFor="search-sort-by" className="search-label">
                  Sort Order
                </label>
                <select
                  id="search-sort-by"
                  className="search-select"
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  disabled={isLoading}
                >
                  <option value="date">Posting Date (Most Recent First)</option>
                  <option value="relevance">Adzuna Relevance</option>
                </select>
              </div>

              <div className="search-field">
                <label htmlFor="search-per-page" className="search-label">
                  Results Per Page
                </label>
                <select
                  id="search-per-page"
                  className="search-select"
                  value={resultsPerPage}
                  onChange={(e) => setResultsPerPage(Number(e.target.value))}
                  disabled={isLoading}
                >
                  <option value={10}>10 results</option>
                  <option value={20}>20 results</option>
                  <option value={50}>50 results</option>
                </select>
              </div>
            </div>
          </div>
        )}
      </div>
    </form>
  );
}
