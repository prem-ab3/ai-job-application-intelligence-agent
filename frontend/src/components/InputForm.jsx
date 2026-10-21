import React, { useRef, useState } from 'react';
import { uploadResumeFile } from '../services/api';

const MIN_LENGTH = 20;

export default function InputForm({
  resumeText,
  setResumeText,
  jobDescription,
  setJobDescription,
  onSubmit,
  onReset,
  isLoading,
  onError,
}) {
  const fileInputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState('');

  const resumeLen = resumeText.trim().length;
  const jdLen = jobDescription.trim().length;

  const isResumeValid = resumeLen >= MIN_LENGTH;
  const isJdValid = jdLen >= MIN_LENGTH;
  const canSubmit = isResumeValid && isJdValid && !isLoading && !isUploading;

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (onError) onError(null);
    setIsUploading(true);

    try {
      const result = await uploadResumeFile(file);
      setResumeText(result.extracted_text);
      setUploadedFileName(result.filename);
    } catch (err) {
      if (onError) onError(err.message || 'Failed to extract text from file.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleClearResume = () => {
    setResumeText('');
    setUploadedFileName('');
  };

  const handleFullReset = () => {
    setUploadedFileName('');
    onReset();
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (canSubmit) {
      onSubmit();
    }
  };

  return (
    <form className="form-card" onSubmit={handleSubmit}>
      <div className="form-grid">
        {/* Resume Input with File Upload Control */}
        <div className="input-group">
          <div className="input-header">
            <label htmlFor="resume-input" className="input-label">
              Resume Text
            </label>
            <div className="upload-actions">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept=".pdf,.docx"
                style={{ display: 'none' }}
                disabled={isLoading || isUploading}
                id="resume-file-input"
              />
              <button
                type="button"
                className="upload-trigger-btn"
                onClick={() => fileInputRef.current?.click()}
                disabled={isLoading || isUploading}
                title="Upload PDF or DOCX file to extract text"
              >
                {isUploading ? 'Extracting text...' : '📁 Upload PDF / DOCX'}
              </button>
            </div>
            <span className={`char-counter ${resumeLen > 0 && !isResumeValid ? 'error' : ''}`}>
              {resumeLen} chars {resumeLen < MIN_LENGTH ? `(min ${MIN_LENGTH})` : ''}
            </span>
          </div>

          {uploadedFileName && (
            <div className="uploaded-file-chip">
              <span>📄 Loaded from <strong>{uploadedFileName}</strong></span>
              <button
                type="button"
                className="clear-file-btn"
                onClick={handleClearResume}
                title="Clear loaded resume"
                disabled={isLoading || isUploading}
              >
                &times;
              </button>
            </div>
          )}

          <textarea
            id="resume-input"
            className="text-area"
            value={resumeText}
            onChange={(e) => {
              setResumeText(e.target.value);
              if (!e.target.value) setUploadedFileName('');
            }}
            placeholder="Paste raw resume text here or click 'Upload PDF / DOCX' above..."
            disabled={isLoading || isUploading}
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
            disabled={isLoading || isUploading}
            required
          />
        </div>
      </div>

      <div className="form-actions">
        {(resumeText || jobDescription || uploadedFileName) && (
          <button
            type="button"
            className="reset-btn"
            onClick={handleFullReset}
            disabled={isLoading || isUploading}
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
