import React, { useState } from 'react';
import SkillItem from './SkillItem';

export default function SkillsList({ skills = [] }) {
  const [activeFilter, setActiveFilter] = useState('ALL');

  if (!skills || skills.length === 0) {
    return (
      <div className="skills-card">
        <h2 className="section-title">Extracted Skills</h2>
        <div className="empty-state">No skills were extracted from this job description.</div>
      </div>
    );
  }

  const matchedCount = skills.filter((s) => s.is_matched).length;
  const missingCount = skills.filter((s) => !s.is_matched).length;
  const requiredCount = skills.filter((s) => s.category === 'REQUIRED').length;
  const preferredCount = skills.filter((s) => s.category === 'PREFERRED').length;

  const filteredSkills = skills.filter((s) => {
    if (activeFilter === 'MATCHED') return s.is_matched;
    if (activeFilter === 'MISSING') return !s.is_matched;
    if (activeFilter === 'REQUIRED') return s.category === 'REQUIRED';
    if (activeFilter === 'PREFERRED') return s.category === 'PREFERRED';
    return true;
  });

  return (
    <div className="skills-card">
      <div className="section-header">
        <h2 className="section-title">
          Extracted Skills ({skills.length})
        </h2>

        <div className="filter-tabs">
          <button
            className={`filter-btn ${activeFilter === 'ALL' ? 'active' : ''}`}
            onClick={() => setActiveFilter('ALL')}
          >
            All ({skills.length})
          </button>
          <button
            className={`filter-btn ${activeFilter === 'MATCHED' ? 'active' : ''}`}
            onClick={() => setActiveFilter('MATCHED')}
          >
            Matched ({matchedCount})
          </button>
          <button
            className={`filter-btn ${activeFilter === 'MISSING' ? 'active' : ''}`}
            onClick={() => setActiveFilter('MISSING')}
          >
            Missing ({missingCount})
          </button>
          <button
            className={`filter-btn ${activeFilter === 'REQUIRED' ? 'active' : ''}`}
            onClick={() => setActiveFilter('REQUIRED')}
          >
            Required ({requiredCount})
          </button>
          <button
            className={`filter-btn ${activeFilter === 'PREFERRED' ? 'active' : ''}`}
            onClick={() => setActiveFilter('PREFERRED')}
          >
            Preferred ({preferredCount})
          </button>
        </div>
      </div>

      <div className="skills-grid">
        {filteredSkills.length > 0 ? (
          filteredSkills.map((skill, index) => (
            <SkillItem key={skill.id || index} skill={skill} />
          ))
        ) : (
          <div className="empty-state">No skills match the selected filter.</div>
        )}
      </div>
    </div>
  );
}
