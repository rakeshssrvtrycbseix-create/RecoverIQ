# RecoverIQ

**Autonomous AI Revenue Recovery Agent**

Built for the Razorpay AI Buildathon.

## Problem

Failed payments represent significant revenue leakage for businesses. Many failed transactions are recoverable, but identifying which ones, diagnosing root causes, and executing timely recovery actions requires expertise that doesn't scale.

## Proposed Solution

RecoverIQ is an autonomous AI agent that:

1. **Detects** failed payments with recovery potential
2. **Diagnoses** the root cause of each failure
3. **Predicts** the probability of successful recovery
4. **Recommends** appropriate recovery actions
5. **Validates** actions through a deterministic policy engine
6. **Executes** approved actions safely via Razorpay
7. **Measures** recovery outcomes for continuous improvement

### AI Safety Architecture

The AI agent never has direct access to financial APIs. All actions follow:

```
AI proposes action → Policy Engine validates → Action Executor → Razorpay API
```

## Planned Architecture

```
Razorpay Test Mode → Event Ingestion → PostgreSQL
        ↓
Revenue Risk Detection → ML Recovery Prediction
        ↓
AI Recovery Agent → Policy/Safety Engine
        ↓
┌─────────┴─────────┐
Approved Action    Human Review
        ↓                ↓
Razorpay Test API  Approval/Rejection
        ↓
Recovery Result → Audit Trail → Analytics Dashboard
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy |
| Database | PostgreSQL (Supabase) |
| ML | pandas, NumPy, scikit-learn, XGBoost |
| AI | LLM with structured outputs and tool calling |
| Payments | Razorpay Test Mode |
| Deployment | Vercel (frontend), Render (backend), Supabase (database) |

## Development Status

- [x] Phase 1 — Project foundation and architecture
- [ ] Phase 2 — Database schema and data layer
- [ ] Phase 3 — ML pipeline
- [ ] Phase 4 — AI agent and policy engine
- [ ] Phase 5 — Razorpay integration (Test Mode)
- [ ] Phase 6 — Dashboard and analytics

## Local Development

### Prerequisites

- Node.js >= 18
- Python >= 3.11
- PostgreSQL 16 (or Docker)

### Database

```bash
docker-compose up -d
```

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

API available at http://localhost:8000

Health check: `GET /health`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App available at http://localhost:3000

### Testing

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm run build
```

## Security

- **Never** commit secrets or API keys
- Use `.env` files for configuration (ignored by Git)
- Copy `.env.example` to `.env` and fill in values
- AI agent access to financial APIs is always mediated by the policy engine
- All recovery actions are logged in an immutable audit trail
