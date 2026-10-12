import React from 'react';

export default function SuggestionsCard({ suggestions }) {
  if (!suggestions) return null;

  return (
    <div className="suggestions-card">
      <h2 className="section-title">Improvement Suggestions</h2>
      <div className="suggestions-content">
        {suggestions}
      </div>
    </div>
  );
}
