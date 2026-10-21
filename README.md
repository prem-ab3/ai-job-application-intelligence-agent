# AI Job Application Intelligence Agent

An intelligent, full-stack AI pair-recruiter and job search intelligence system. The application evaluates candidate resumes against job descriptions, deterministically verifies skills against resume evidence, automatically discovers opportunities from Adzuna's India index, and ranks listings using candidate-aligned seniority weighting.

---

## Key Features

- **Analyze Match Dashboard**: Upload or paste a resume alongside a target job description to compute a deterministic competency score (0–100%), extract required vs. preferred skills, verify exact verbatim quotes from the resume, and receive actionable resume improvement advice.
- **Resume-Driven Job Discovery**: Automatically infers target job roles, seniority level, and location preferences directly from the uploaded resume. Manual keyword and location fields remain available as optional overrides.
- **Automated Competency Matching & Ranking**: Discovered job postings are automatically evaluated in batch against the candidate's active resume. Listings are ranked descending by calculated match score.
- **Seniority & Role-Relevance Gating**: Classifies candidate and job seniorities independently. Applies alignment weighting to ensure entry-level and junior candidates see suitable roles outranking senior architect roles, even when technical keywords overlap.
- **Honest Scoring & Evidence Integrity**: Brief job description snippets (< 40 characters) or unverified roles are honestly marked as `⚠️ Not Enough Information` and excluded from ranked scoring to prevent hallucinated match metrics.
- **Multi-Model AI Failover**: Built-in fallback mechanism (`gemini-3.5-flash-lite` → `gemini-flash-lite-latest`) prevents temporary 503 high-demand errors from failing batch evaluations.
- **Resume File Upload**: Secure PDF and DOCX parsing with file magic-byte validation, file size enforcement (5 MB limit), and text length checks.
- **State Preservation**: Tab navigation preserves search results, scores, active filters, and pagination state without triggering duplicate API calls. In-memory caching guards external rate limits.

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy, Neon PostgreSQL, Pydantic v2 |
| **AI / LLM** | Google Gemini API (`google-genai` SDK), structured JSON output |
| **Job Source** | Official Adzuna India Search API (`api.adzuna.com`) |
| **Document Processing** | `pypdf`, `python-docx` |
| **Frontend** | React 18, Vite, Vanilla CSS design system (dark mode, glassmorphism) |
| **Testing** | `pytest`, `pytest-mock`, `httpx` (40 comprehensive unit & integration tests) |

---

## Project Structure

```text
AI JOB APPLICATION INTELLIGENCE AGENT/
├── backend/
│   ├── app/
│   │   ├── agent/          # GenAI client, single/batch orchestrator, tools, prompts
│   │   ├── routers/        # FastAPI routes (analysis, health, jobs, resumes)
│   │   ├── services/       # Adzuna API client, resume file parser
│   │   ├── config.py       # Pydantic environment configuration
│   │   ├── database.py     # SQLAlchemy Neon PostgreSQL connection
│   │   ├── models.py       # PostgreSQL database models
│   │   ├── schemas.py      # Request/response validation schemas
│   │   └── main.py         # FastAPI application entrypoint & lifespan
│   ├── tests/              # 40 automated backend tests (mocked, no live API spend)
│   ├── .env.example        # Backend environment variables template
│   ├── pytest.ini          # Pytest configuration
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/     # React UI components (Dashboard, Forms, Cards, Lists)
│   │   ├── services/       # API client with in-memory request caching
│   │   ├── utils/          # Role relevance filter & resume profile extractors
│   │   ├── App.css         # Component styling and layout
│   │   ├── App.jsx         # Root dashboard container and tab router
│   │   └── index.css       # Design tokens, color palette, and typography
│   ├── .env.example        # Frontend environment variables template
│   ├── index.html          # HTML entrypoint
│   ├── package.json        # Node dependencies and scripts
│   └── vite.config.js      # Vite build configuration
├── .gitignore              # Git ignore rules for secrets, venv, and build artifacts
└── README.md               # Repository documentation
```

---

## Getting Started

### Prerequisites

- **Python**: 3.11 or higher
- **Node.js**: v18.0.0 or higher (v20+ recommended)
- **Neon PostgreSQL**: Free cloud database instance
- **Google Gemini API Key**: From Google AI Studio
- **Adzuna Developer Account**: API credentials for job discovery

---

### Backend Setup

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Windows PowerShell:
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # macOS / Linux:
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   # Copy the example environment template
   cp .env.example .env
   ```

   Edit `backend/.env` with your credentials:
   ```env
   # Database (Neon PostgreSQL)
   DATABASE_URL="postgresql://user:password@endpoint.neon.tech/neondb?sslmode=require"

   # Google Gemini API
   GEMINI_API_KEY="your_gemini_api_key_here"
   GEMINI_MODEL="gemini-3.5-flash-lite"

   # Adzuna Job Search API (India)
   ADZUNA_APP_ID="your_adzuna_app_id_here"
   ADZUNA_APP_KEY="your_adzuna_app_key_here"
   ADZUNA_COUNTRY="in"
   ```

5. **Start the backend server**:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   Verify backend health at: `http://127.0.0.1:8000/health`
   Interactive Swagger docs at: `http://127.0.0.1:8000/docs`

---

### Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **(Optional) Configure environment variables**:
   ```bash
   cp .env.example .env
   ```
   *Defaults to `http://127.0.0.1:8000` if omitted.*

4. **Start the frontend development server**:
   ```bash
   npm run dev
   ```
   Open your browser to: **`http://localhost:5173`**

---

## Running Automated Tests

The test suite uses mocked external services, consuming **zero** live API credits during test execution:

```bash
# Run all backend tests (from backend directory)
cd backend
python -m pytest -v
```

```bash
# Validate frontend production build (from frontend directory)
cd frontend
npm run build
```

---

## API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check verifying Neon DB connectivity |
| `POST` | `/api/v1/analyze` | Single application resume-to-job analysis |
| `POST` | `/api/v1/resumes/upload` | Multipart file upload for PDF/DOCX text extraction |
| `GET` | `/api/v1/jobs/search` | Queries Adzuna India job search index |
| `POST` | `/api/v1/jobs/match` | Evaluates and ranks multiple job listings against resume |

---

## License

This project is licensed under the MIT License.
