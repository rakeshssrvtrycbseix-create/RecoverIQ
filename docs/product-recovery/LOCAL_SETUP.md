# RecoverIQ — Local Setup Guide

Follow these steps to set up, seed, run, and test RecoverIQ locally.

---

## 1. Prerequisites

- **Node.js**: >= 18 (Tested on v24.15.0)
- **Python**: >= 3.11 (Tested on Python 3.12.10)
- **Git**

---

## 2. Quick Start (Step-by-Step)

### A. Backend Setup
```bash
# 1. Navigate to backend directory
cd backend

# 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell / CMD
# source .venv/bin/activate     # macOS / Linux

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Seed development demo database
python scripts/seed_demo_data.py --reset

# 5. Start the FastAPI backend server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
* Backend API: `http://127.0.0.1:8000`
* Swagger Interactive Docs: `http://127.0.0.1:8000/docs`
* Health Check: `http://127.0.0.1:8000/health`

---

### B. Frontend Setup
```bash
# 1. Open a new terminal and navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Start Next.js development server
npm run dev
```
* Frontend Dashboard: `http://localhost:3000`

---

## 3. Verifying Local Installation

1. Open `http://localhost:3000` in your browser.
2. Verify that top KPI cards display real seeded data (e.g., Recovered Revenue ₹5.87L, Amount at Risk ₹8.72L).
3. Navigate to `/review` to inspect the 5-6 pending Human Review cases.
4. Click "Authorize Action" on any pending case and confirm to verify real-time backend state changes and audit trail logging.
5. Check `/audit` to verify the new `HUMAN_REVIEW_APPROVED` entry.
