/**
 * Dynamic resume-driven profile extraction utility.
 * Extracts suggested job titles, technical skills, seniority indicators, and location preferences
 * from the active resume without hardcoding personal identities or a static role list.
 */

const TECH_ROLES_RULES = [
  {
    role: 'AI Engineer',
    regex: /\b(ai\b|artificial intelligence|genai|llm|agentic|prompt|langchain|rag\b|transformer|openai)\b/i,
  },
  {
    role: 'Machine Learning Engineer',
    regex: /\b(machine learning|deep learning|pytorch|tensorflow|scikit|nlp|computer vision|model training)\b/i,
  },
  {
    role: 'FastAPI Developer',
    regex: /\b(fastapi)\b/i,
  },
  {
    role: 'Python Developer',
    regex: /\b(python|django|flask|celery|numpy|pandas)\b/i,
  },
  {
    role: 'Backend Developer',
    regex: /\b(backend|microservice|rest api|api|sql|postgresql|postgres|database|redis|mongodb)\b/i,
  },
  {
    role: 'Frontend Developer',
    regex: /\b(frontend|react|vue|angular|typescript|javascript|html5|css3|next\.?js|vite)\b/i,
  },
  {
    role: 'Full Stack Developer',
    regex: /\b(full stack|fullstack|mern|mean)\b/i,
  },
  {
    role: 'DevOps Engineer',
    regex: /\b(devops|ci\/cd|kubernetes|docker|terraform|aws|gcp|azure|jenkins)\b/i,
  },
  {
    role: 'Data Scientist',
    regex: /\b(data scientist|data science|predictive modeling|data analytics|statistics)\b/i,
  },
  {
    role: 'Software Engineer',
    regex: /\b(software engineer|software developer|system design|algorithms|git)\b/i,
  },
];

const SENIORITY_RULES = [
  { level: 'Principal', regex: /\b(principal|staff engineer|director|chief)\b/i },
  { level: 'Lead', regex: /\b(lead|team lead|tech lead)\b/i },
  { level: 'Senior', regex: /\b(senior|sr\b|6\+?\s*years|5\+?\s*years|7\+?\s*years|8\+?\s*years|10\+?\s*years)\b/i },
  { level: 'Junior / Associate', regex: /\b(junior|jr\b|associate|entry level|fresher|intern|internship)\b/i },
];

const LOCATION_PREFERENCES = [
  { name: 'Bengaluru', regex: /\b(bengaluru|bangalore)\b/i },
  { name: 'Hyderabad', regex: /\b(hyderabad)\b/i },
  { name: 'Pune', regex: /\b(pune)\b/i },
  { name: 'Mumbai', regex: /\b(mumbai)\b/i },
  { name: 'Delhi NCR', regex: /\b(delhi|ncr|gurgaon|gurugram|noida)\b/i },
  { name: 'Chennai', regex: /\b(chennai)\b/i },
  { name: 'Remote', regex: /\b(remote|work from home|wfh)\b/i },
];

const KEY_SKILLS_KEYWORDS = [
  'Python', 'FastAPI', 'React', 'TypeScript', 'JavaScript', 'Node.js',
  'PostgreSQL', 'Docker', 'Kubernetes', 'AWS', 'GCP', 'Azure',
  'SQL', 'Git', 'CI/CD', 'REST API', 'Redis', 'Machine Learning', 'AI'
];

/**
 * Extracts a structured profile from resume text.
 *
 * @param {string} resumeText
 * @returns {{
 *   suggestedRoles: string[],
 *   primaryRole: string,
 *   experienceLevel: string|null,
 *   detectedLocation: string|null,
 *   technicalSkills: string[]
 * }}
 */
export function extractResumeProfile(resumeText) {
  if (!resumeText || typeof resumeText !== 'string' || resumeText.trim().length < 20) {
    return {
      suggestedRoles: [],
      primaryRole: '',
      experienceLevel: null,
      detectedLocation: null,
      technicalSkills: [],
    };
  }

  const text = resumeText.toLowerCase();

  // 1. Roles
  const matchedRoles = [];
  for (const rule of TECH_ROLES_RULES) {
    if (rule.regex.test(text)) {
      matchedRoles.push(rule.role);
    }
  }

  if (matchedRoles.length === 0 && text.length > 50) {
    matchedRoles.push('Software Engineer', 'Backend Developer', 'Python Developer');
  }

  const suggestedRoles = [...new Set(matchedRoles)];
  const primaryRole = suggestedRoles[0] || 'Software Engineer';

  // 2. Seniority / Experience
  let experienceLevel = null;
  for (const rule of SENIORITY_RULES) {
    if (rule.regex.test(text)) {
      experienceLevel = rule.level;
      break;
    }
  }

  // 3. Location preference
  let detectedLocation = null;
  for (const loc of LOCATION_PREFERENCES) {
    if (loc.regex.test(text)) {
      detectedLocation = loc.name;
      break;
    }
  }

  // 4. Skills
  const technicalSkills = KEY_SKILLS_KEYWORDS.filter((skill) => {
    const escaped = skill.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&');
    const regex = new RegExp(`\\b${escaped}\\b`, 'i');
    return regex.test(resumeText);
  });

  return {
    suggestedRoles,
    primaryRole,
    experienceLevel,
    detectedLocation,
    technicalSkills,
  };
}

/**
 * Backward-compatible helper returning an array of suggested role titles.
 *
 * @param {string} resumeText
 * @returns {string[]}
 */
export function extractRoleSuggestions(resumeText) {
  return extractResumeProfile(resumeText).suggestedRoles;
}
