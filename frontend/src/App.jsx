import React, { useState } from 'react';
import Header from './components/Header';
import InputForm from './components/InputForm';
import ScoreCard from './components/ScoreCard';
import SkillsList from './components/SkillsList';
import SuggestionsCard from './components/SuggestionsCard';
import ErrorAlert from './components/ErrorAlert';
import LoadingIndicator from './components/LoadingIndicator';
import { analyzeApplication } from './services/api';
import './App.css';

export default function App() {
  const [resumeText, setResumeText] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [analysis, setAnalysis] = useState(null);

  const handleAnalyze = async () => {
    setError(null);
    setIsLoading(true);

    try {
      const data = await analyzeApplication(resumeText.trim(), jobDescription.trim());
      setAnalysis(data);
    } catch (err) {
      setError(err.message || 'An unexpected error occurred during analysis.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setResumeText('');
    setJobDescription('');
    setAnalysis(null);
    setError(null);
  };

  return (
    <div className="app-container">
      <Header />

      <ErrorAlert message={error} onClose={() => setError(null)} />

      <InputForm
        resumeText={resumeText}
        setResumeText={setResumeText}
        jobDescription={jobDescription}
        setJobDescription={setJobDescription}
        onSubmit={handleAnalyze}
        onReset={handleReset}
        isLoading={isLoading}
      />

      {isLoading && <LoadingIndicator />}

      {analysis && !isLoading && (
        <main className="results-container">
          <ScoreCard analysis={analysis} />
          <SkillsList skills={analysis.skills} />
          <SuggestionsCard suggestions={analysis.suggestions} />
        </main>
      )}
    </div>
  );
}
