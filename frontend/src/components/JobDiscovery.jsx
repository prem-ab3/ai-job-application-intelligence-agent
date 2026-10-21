import React, { useState, useRef, useMemo } from 'react';
import JobSearchForm from './JobSearchForm';
import JobResultsList from './JobResultsList';
import LoadingIndicator from './LoadingIndicator';
import ErrorAlert from './ErrorAlert';
import { searchJobs, matchJobsWithResume, uploadResumeFile } from '../services/api';
import { extractResumeProfile } from '../utils/roleSuggestions';
import { filterJobsByRelevance } from '../utils/jobRelevance';

export default function JobDiscovery({ resumeText, setResumeText }) {
  const [keywords, setKeywords] = useState('');
  const [location, setLocation] = useState('');
  const [resultsPerPage, setResultsPerPage] = useState(10);
  const [currentPage, setCurrentPage] = useState(1);
  const [roleFilter, setRoleFilter] = useState('technical'); // 'technical' | 'all'
  const [freshnessFilter, setFreshnessFilter] = useState('recent_90'); // 'recent_90' | 'all'
  const [sortBy, setSortBy] = useState('date'); // 'date' | 'relevance'

  const [jobsData, setJobsData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [searchError, setSearchError] = useState(null);

  // Resume Drawer & Upload State
  const [showResumeInput, setShowResumeInput] = useState(false);
  const [isUploadingResume, setIsUploadingResume] = useState(false);
  const fileInputRef = useRef(null);

  // Matching State
  const [matchResponse, setMatchResponse] = useState(null);
  const [isMatching, setIsMatching] = useState(false);
  const [matchError, setMatchError] = useState(null);
  const [sortMode, setSortMode] = useState('match'); // 'match' | 'original'

  // Ref to track last matched signature for API protection (avoids redundant Gemini calls)
  const lastMatchedSignatureRef = useRef('');

  // Ref to prevent duplicate concurrent searches
  const isSearchingRef = useRef(false);

  // Dynamic resume profile extracted from active resume text
  const resumeProfile = useMemo(() => {
    return extractResumeProfile(resumeText);
  }, [resumeText]);

  const performSearch = async (targetPage = 1) => {
    if (isSearchingRef.current) {
      return;
    }

    isSearchingRef.current = true;
    setIsLoading(true);
    setSearchError(null);
    setMatchResponse(null); // Clear previous matches when searching a new query/page
    setMatchError(null);
    lastMatchedSignatureRef.current = '';

    // Auto-discover role and location if fields left empty by user
    const effectiveKeywords = keywords.trim() || resumeProfile.primaryRole || '';
    const effectiveLocation = location.trim() || (resumeProfile.detectedLocation ? resumeProfile.detectedLocation : '');
    const maxDaysOld = freshnessFilter === 'recent_90' ? 90 : null;

    try {
      const data = await searchJobs({
        keywords: effectiveKeywords,
        location: effectiveLocation,
        page: targetPage,
        resultsPerPage,
        sortBy,
        maxDaysOld,
      });
      setJobsData(data);
      setCurrentPage(targetPage);

      // Requirement 3: Automatically match & rank discovered jobs if active resume is present
      if (resumeText && resumeText.trim().length >= 20 && data?.jobs?.length > 0) {
        setIsMatching(true);
        try {
          const matchResult = await matchJobsWithResume({
            resumeText: resumeText.trim(),
            jobs: data.jobs,
          });
          setMatchResponse(matchResult);
          setSortMode('match');
          lastMatchedSignatureRef.current = `${resumeText.trim()}::${data.jobs.map((j) => j.id).join(',')}`;
        } catch (mErr) {
          console.error('Auto-match error:', mErr);
          setMatchError(mErr.message || 'Automated match evaluation could not be completed.');
        } finally {
          setIsMatching(false);
        }
      }
    } catch (err) {
      setSearchError(err.message || 'An unexpected error occurred while searching jobs.');
    } finally {
      setIsLoading(false);
      isSearchingRef.current = false;
    }
  };

  const handleSearchSubmit = () => {
    performSearch(1);
  };

  const handlePageChange = (newPage) => {
    if (newPage < 1 || (jobsData && newPage > Math.ceil(jobsData.total_results / resultsPerPage))) {
      return;
    }
    performSearch(newPage);
  };

  const handleReset = () => {
    setKeywords('');
    setLocation('');
    setResultsPerPage(10);
    setCurrentPage(1);
    setRoleFilter('technical');
    setFreshnessFilter('recent_90');
    setSortBy('date');
    setJobsData(null);
    setMatchResponse(null);
    setSearchError(null);
    setMatchError(null);
    lastMatchedSignatureRef.current = '';
  };

  // Resume File Upload handler
  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploadingResume(true);
    setSearchError(null);

    try {
      const result = await uploadResumeFile(file);
      const newText = result.extracted_text || '';
      setResumeText(newText);

      // Auto-match currently displayed jobs against newly uploaded resume
      if (jobsData?.jobs?.length > 0 && newText.trim().length >= 20) {
        setIsMatching(true);
        try {
          const matchResult = await matchJobsWithResume({
            resumeText: newText.trim(),
            jobs: jobsData.jobs,
          });
          setMatchResponse(matchResult);
          setSortMode('match');
          lastMatchedSignatureRef.current = `${newText.trim()}::${jobsData.jobs.map((j) => j.id).join(',')}`;
        } catch (mErr) {
          console.error('Auto-match error after upload:', mErr);
          setMatchError(mErr.message || 'Automated match evaluation could not be completed.');
        } finally {
          setIsMatching(false);
        }
      }
    } catch (err) {
      setSearchError(err.message || 'Failed to extract text from the resume file.');
    } finally {
      setIsUploadingResume(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // Batch Matching Handler with Cache & API Protection (manual trigger or re-evaluation)
  const handleMatchJobs = async () => {
    if (!resumeText || !resumeText.trim()) {
      setMatchError('Please provide a resume before running match evaluation.');
      return;
    }
    if (!jobsData || !jobsData.jobs || jobsData.jobs.length === 0) {
      return;
    }

    // Generate signature of current resume and jobs
    const currentSignature = `${resumeText.trim()}::${jobsData.jobs.map((j) => j.id).join(',')}`;
    if (matchResponse && lastMatchedSignatureRef.current === currentSignature) {
      // Re-use existing results if neither resume nor job list has changed
      return;
    }

    setIsMatching(true);
    setMatchError(null);

    try {
      const response = await matchJobsWithResume({
        resumeText: resumeText.trim(),
        jobs: jobsData.jobs,
      });
      setMatchResponse(response);
      setSortMode('match');
      lastMatchedSignatureRef.current = currentSignature;
    } catch (err) {
      setMatchError(err.message || 'Failed to complete job matching evaluation.');
    } finally {
      setIsMatching(false);
    }
  };

  // Compute displayed jobs list with attached match info and deterministic role & freshness filtering
  const { displayedJobs, excludedNonTechCount, excludedStaleCount, totalExcludedCount } = useMemo(() => {
    if (!jobsData || !jobsData.jobs) {
      return { displayedJobs: [], excludedNonTechCount: 0, excludedStaleCount: 0, totalExcludedCount: 0 };
    }

    let combinedList = [];

    if (!matchResponse) {
      combinedList = jobsData.jobs;
    } else {
      const rankedMap = new Map();
      matchResponse.ranked_jobs?.forEach((rj) => rankedMap.set(rj.job_id, rj));

      const unrankedMap = new Map();
      matchResponse.unranked_jobs?.forEach((uj) => unrankedMap.set(uj.job_id, uj));

      if (sortMode === 'match') {
        const rankedItems = (matchResponse.ranked_jobs || []).map((rj) => {
          const originalJob = jobsData.jobs.find((j) => String(j.id) === String(rj.job_id)) || {};
          return {
            ...originalJob,
            match: rj,
          };
        });

        // Ensure rankedItems are sorted strictly by match_score descending
        rankedItems.sort((a, b) => {
          const scoreA = typeof a.match?.match_score === 'number' ? a.match.match_score : -1;
          const scoreB = typeof b.match?.match_score === 'number' ? b.match.match_score : -1;
          if (scoreB !== scoreA) {
            return scoreB - scoreA;
          }
          return (a.match?.rank || 999) - (b.match?.rank || 999);
        });

        const unrankedItems = (matchResponse.unranked_jobs || []).map((uj) => {
          const originalJob = jobsData.jobs.find((j) => String(j.id) === String(uj.job_id)) || {};
          return {
            ...originalJob,
            match: uj,
          };
        });

        combinedList = [...rankedItems, ...unrankedItems];
      } else {
        combinedList = jobsData.jobs.map((job) => {
          const jobId = String(job.id);
          const match = rankedMap.get(jobId) || unrankedMap.get(jobId) || null;
          return {
            ...job,
            match,
          };
        });
      }
    }

    // Apply deterministic relevance and freshness filtering
    const { visibleJobs, excludedNonTechCount: nonTechCount, excludedStaleCount: staleCount, excludedCount } = filterJobsByRelevance(
      combinedList,
      roleFilter,
      freshnessFilter
    );

    return {
      displayedJobs: visibleJobs,
      excludedNonTechCount: nonTechCount,
      excludedStaleCount: staleCount,
      totalExcludedCount: excludedCount,
    };
  }, [jobsData, matchResponse, sortMode, roleFilter, freshnessFilter]);

  const hasResume = Boolean(resumeText && resumeText.trim().length >= 20);

  return (
    <section className="job-discovery-section">
      <div className="section-intro">
        <h2 className="section-title">🔍 Discover & Rank Jobs in India</h2>
        <p className="section-subtitle">
          Search recent job opportunities automatically guided by your resume. Compare your profile across multiple listings
          using verified evidence extraction and deterministic scoring.
        </p>
      </div>

      {/* Resume Integration Status Card */}
      <div className="resume-status-card">
        <div className="resume-status-main">
          <div className="resume-status-info">
            <span className="resume-icon">📄</span>
            <div>
              <div className="resume-title">
                {hasResume ? (
                  <strong>Active Resume Loaded</strong>
                ) : (
                  <strong>No Resume Loaded</strong>
                )}
              </div>
              <div className="resume-desc">
                {hasResume ? (
                  <span>
                    {resumeText.length.toLocaleString()} characters loaded.
                    {resumeProfile.primaryRole && (
                      <span className="resume-detected-badge">
                        Target: {resumeProfile.primaryRole}
                        {resumeProfile.experienceLevel ? ` (${resumeProfile.experienceLevel})` : ''}
                      </span>
                    )}
                  </span>
                ) : (
                  <span>Upload a PDF/DOCX resume to auto-discover roles and enable competency ranking.</span>
                )}
              </div>
            </div>
          </div>

          <div className="resume-actions-group">
            <input
              type="file"
              ref={fileInputRef}
              accept=".pdf,.docx"
              style={{ display: 'none' }}
              onChange={handleFileUpload}
            />
            <button
              type="button"
              className="resume-action-btn"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploadingResume}
            >
              {isUploadingResume ? 'Uploading...' : hasResume ? '🔄 Replace File' : '📤 Upload Resume (PDF/DOCX)'}
            </button>
            <button
              type="button"
              className="resume-text-toggle-btn"
              onClick={() => setShowResumeInput(!showResumeInput)}
            >
              {showResumeInput ? 'Hide Text' : hasResume ? 'Edit Text' : 'Paste Text'}
            </button>
          </div>
        </div>

        {showResumeInput && (
          <div className="resume-textarea-container">
            <textarea
              className="resume-inline-textarea"
              placeholder="Paste your resume text here (minimum 20 characters)..."
              rows={5}
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
            />
          </div>
        )}
      </div>

      <ErrorAlert message={searchError} onClose={() => setSearchError(null)} />
      <ErrorAlert message={matchError} onClose={() => setMatchError(null)} />

      <JobSearchForm
        keywords={keywords}
        setKeywords={setKeywords}
        location={location}
        setLocation={setLocation}
        resultsPerPage={resultsPerPage}
        setResultsPerPage={setResultsPerPage}
        roleFilter={roleFilter}
        setRoleFilter={setRoleFilter}
        freshnessFilter={freshnessFilter}
        setFreshnessFilter={setFreshnessFilter}
        sortBy={sortBy}
        setSortBy={setSortBy}
        resumeProfile={resumeProfile}
        onSearch={handleSearchSubmit}
        onReset={handleReset}
        isLoading={isLoading || isMatching}
      />

      {/* Exclusion Banner when items are hidden by filters */}
      {totalExcludedCount > 0 && (
        <div className="role-filter-notice-banner">
          <span>
            🛡️ Filtered out <strong>{totalExcludedCount}</strong> listing{totalExcludedCount === 1 ? '' : 's'} (
            {excludedNonTechCount > 0 ? `${excludedNonTechCount} non-technical domain${excludedNonTechCount === 1 ? '' : 's'}` : ''}
            {excludedNonTechCount > 0 && excludedStaleCount > 0 ? ', ' : ''}
            {excludedStaleCount > 0 ? `${excludedStaleCount} older than 90 days` : ''}
            ).
          </span>
          <button
            type="button"
            className="filter-toggle-inline-btn"
            onClick={() => {
              setRoleFilter('all');
              setFreshnessFilter('all');
            }}
          >
            Show All Results
          </button>
        </div>
      )}

      {isLoading && <LoadingIndicator />}
      {isMatching && (
        <div className="matching-in-progress-indicator">
          <LoadingIndicator />
          <p className="matching-progress-text">
            Evaluating competency evidence across discovered jobs using deterministic scoring...
          </p>
        </div>
      )}

      {!isLoading && jobsData && (
        <JobResultsList
          jobs={displayedJobs}
          totalResults={jobsData.total_results}
          currentPage={currentPage}
          resultsPerPage={resultsPerPage}
          onPageChange={handlePageChange}
          isLoading={isLoading}
          onMatchJobs={handleMatchJobs}
          isMatching={isMatching}
          hasMatchResults={Boolean(matchResponse)}
          resumeLoaded={hasResume}
          sortMode={sortMode}
          setSortMode={setSortMode}
          matchStats={
            matchResponse
              ? {
                  ranked: matchResponse.ranked_jobs?.length || 0,
                  unranked: matchResponse.unranked_jobs?.length || 0,
                  insufficient: (matchResponse.unranked_jobs || []).filter(
                    (j) => j.match_status === 'INSUFFICIENT_DESCRIPTION' || j.match_status === 'INSUFFICIENT_REQUIREMENTS'
                  ).length,
                  roleMismatch: (matchResponse.unranked_jobs || []).filter(
                    (j) => j.match_status === 'ROLE_MISMATCH'
                  ).length,
                  failed: (matchResponse.unranked_jobs || []).filter(
                    (j) => j.match_status === 'EVALUATION_FAILED'
                  ).length,
                }
              : null
          }
        />
      )}

      {!isLoading && !jobsData && !searchError && (
        <div className="discovery-placeholder">
          <div className="placeholder-icon">💼</div>
          <h3>Ready to discover and rank jobs?</h3>
          <p>
            {hasResume
              ? `Click "Search Jobs" to find opportunities matched to your resume profile (${resumeProfile.primaryRole || 'Software Engineering'}).`
              : 'Upload a resume or enter keywords to find relevant openings.'}
          </p>
        </div>
      )}
    </section>
  );
}
