import React from 'react';

export default function SkillItem({ skill }) {
  const isMatched = Boolean(skill.is_matched);
  const category = (skill.category || 'REQUIRED').toUpperCase();

  return (
    <div className="skill-item">
      <div className="skill-item-header">
        <div className="skill-name-area">
          <span className={`match-icon ${isMatched ? 'matched' : 'missing'}`}>
            {isMatched ? '✓' : '✕'}
          </span>
          <span className="skill-name">{skill.skill_name}</span>
        </div>

        <div className="skill-badges">
          <span className={`category-tag ${category.toLowerCase()}`}>
            {category}
          </span>
          <span className={`match-tag ${isMatched ? 'matched' : 'missing'}`}>
            {isMatched ? 'Matched' : 'Missing'}
          </span>
        </div>
      </div>

      {isMatched && skill.resume_evidence ? (
        <div className="evidence-box">
          <div className="evidence-label">Resume Evidence</div>
          <div>"{skill.resume_evidence}"</div>
        </div>
      ) : (
        <div className="no-evidence-text">
          No verified evidence found in candidate's resume.
        </div>
      )}
    </div>
  );
}
