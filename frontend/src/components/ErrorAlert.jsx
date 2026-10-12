import React from 'react';

export default function ErrorAlert({ message, onClose }) {
  if (!message) return null;

  return (
    <div className="error-alert" role="alert">
      <div>
        <strong>Error: </strong> {message}
      </div>
      {onClose && (
        <button
          className="error-close-btn"
          onClick={onClose}
          aria-label="Dismiss error"
        >
          &times;
        </button>
      )}
    </div>
  );
}
