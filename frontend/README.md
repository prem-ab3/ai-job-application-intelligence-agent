# AI Job Application Intelligence Agent - Frontend

This is the React + Vite frontend dashboard for the **AI Job Application Intelligence Agent**. It provides an interface to paste candidate resumes and target job descriptions, triggering real-time analysis against the FastAPI backend (`http://127.0.0.1:8000/api/v1/analyze`).

---

## Prerequisites

- **Node.js**: v18.0.0 or higher (v22+ recommended)
- **FastAPI Backend**: Running locally on `http://127.0.0.1:8000`

---

## Quick Setup & Run Instructions

### 1. Navigate to the Frontend Directory

```bash
cd frontend
```

### 2. Install Dependencies

```bash
npm install
```
*(On Windows systems with restricted PowerShell script policies, you can run `npm.cmd install`)*

### 3. Start the Development Server

```bash
npm run dev
```

The frontend will start at:
👉 **`http://localhost:5173`** (or `http://127.0.0.1:5173`)

---

## How to Test with the Running Backend

1. **Start the Backend** in a separate terminal:
   ```bash
   cd backend
   # Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   # macOS / Linux:
   # source venv/bin/activate
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   Verify backend health at: `http://127.0.0.1:8000/health`

2. **Open the Frontend**:
   Open your browser to `http://localhost:5173`.

3. **Perform an Analysis**:
   - **Upload a Resume** (PDF or DOCX up to 5 MB) by clicking **Upload PDF / DOCX**, or paste resume text manually (at least 20 characters).
   - Review or edit the extracted resume text in the textarea as desired.
   - Paste job description text (at least 20 characters).
   - Click **Analyze Match**.
   - Review:
     - Deterministic Match Score (%)
     - Status badge and breakdown metrics
     - Extracted skills list with verified evidence quotes
     - Filter tabs (All, Matched, Missing, Required, Preferred)
     - Actionable improvement suggestions

---

## Building for Production

To create an optimized production build:

```cmd
npm run build
```

To preview the production build locally:

```cmd
npm run preview
```
