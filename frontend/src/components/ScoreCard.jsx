import React from 'react';

export default function ScoreCard({ analysis }) {
  if (!analysis) return null;

  const score = analysis.total_score !== null && analysis.total_score !== undefined
    ? Number(analysis.total_score).toFixed(1)
    : 'N/A';

  const numScore = Number(analysis.total_score) || 0;
  let scoreClass = 'low';
  if (numScore >= 75) scoreClass = 'high';
  else if (numScore >= 50) scoreClass = 'medium';

  const skills = analysis.skills || [];
  const required = skills.filter((s) => s.category === 'REQUIRED');
  const preferred = skills.filter((s) => s.category === 'PREFERRED');

  const reqMatched = required.filter((s) => s.is_matched).length;
  const prefMatched = preferred.filter((s) => s.is_matched).length;

  const formattedDate = analysis.created_at
    ? new Date(analysis.created_at).toLocaleString()
    : 'Just now';

  return (
    <div className="score-card">
      <div className={`score-display ${scoreClass}`}>
        <span className="score-number">{score}%</span>
        <span className="score-label">Match Score</span>
      </div>

      <div className="score-meta">
        <div className="score-status-row">
          <span className={`status-badge ${(analysis.status || 'completed').toLowerCase()}`}>
            Status: {analysis.status || 'COMPLETED'}
          </span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Analyzed: {formattedDate}
          </span>
        </div>

        <div className="stats-grid">
          <div className="stat-chip">
            <span className="stat-label">Total Skills</span>
            <span className="stat-val">{skills.length}</span>
          </div>
          <div className="stat-chip">
            <span className="stat-label">Required Matched</span>
            <span className="stat-val">
              {reqMatched} / {required.length}
            </span>
          </div>
          <div className="stat-chip">
            <span className="stat-label">Preferred Matched</span>
            <span className="stat-val">
              {prefMatched} / {preferred.length}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
