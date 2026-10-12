import React from 'react';

export default function LoadingIndicator() {
  return (
    <div className="loading-box">
      <div className="spinner"></div>
      <div className="loading-text">Analyzing Application...</div>
      <div className="loading-subtext">
        Gemini is evaluating requirements and extracting resume evidence. Python is verifying matches and calculating the deterministic score.
      </div>
    </div>
  );
}
