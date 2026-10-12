import React from 'react';

export default function Header() {
  return (
    <header className="app-header">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
        <h1 className="app-title">
          <span>🎯</span> AI Job Application Intelligence Agent
        </h1>
        <span className="api-badge">Target: http://127.0.0.1:8000</span>
      </div>
      <p className="app-subtitle">
        Evaluate how well your resume matches a target job description with deterministic scoring and evidence-backed skill extraction.
      </p>
    </header>
  );
}
