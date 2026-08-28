# RecoverIQ — Initial Architecture

## Project Purpose

RecoverIQ is an autonomous AI agent designed to recover failed payments by analyzing transaction data, predicting recovery likelihood, and executing safe recovery actions through Razorpay's API. The system prioritizes safety, auditability, and deterministic policy enforcement over speed.

## Planned System Architecture

### Overview

```
┌──────────────────────────────────────────────────────────────┐
│                      Razorpay Test Mode                       │
│                   (Payments & Webhooks)                        │
└──────────────────┬───────────────────────┬────────────────────┘
                   │                       ▲
                   ▼                       │
┌──────────────────────────┐  ┌────────────────────────────────┐
│    Event Ingestion       │  │     Action Executor            │
│  (Webhooks / Polling)    │  │  (Razorpay API calls)          │
└──────────┬───────────────┘  └────────────▲───────────────────┘
           │                               │
           ▼                               │
┌──────────────────────────┐  ┌────────────────────────────────┐
│      PostgreSQL          │  │     Policy / Safety Engine     │
│  (Transactions, Audit)   │  │  (Deterministic validation)    │
└──────────┬───────────────┘  └────────────▲───────────────────┘
           │                               │
           ▼                               │
┌──────────────────────────┐  ┌────────────────────────────────┐
│  Revenue Risk Detection  │  │     AI Recovery Agent          │
│  (Rule-based triggers)   │  │  (LLM with tool calling)       │
└──────────┬───────────────┘  └────────────▲───────────────────┘
           │                               │
           ▼                               │
┌──────────────────────────────────────────────────────────────┐
│              ML Recovery Prediction                           │
│        (Classification + probability scoring)                 │
└──────────────────────────────────────────────────────────────┘
```

### Frontend

- **Technology**: Next.js with App Router, TypeScript, Tailwind CSS, shadcn/ui
- **Purpose**: Analytics dashboard displaying recovery metrics, active cases, audit trail, and agent activity
- **Communication**: REST API calls to the backend
- **Deployment**: Vercel

### Backend

- **Technology**: Python, FastAPI, Pydantic
- **Purpose**: API layer, webhook ingestion, orchestration of ML and AI components
- **Structure**:
  - `api/` — HTTP route handlers
  - `core/` — Configuration, database setup, shared utilities
  - `models/` — SQLAlchemy ORM models
  - `schemas/` — Pydantic validation schemas
  - `services/` — Business logic (risk detection, recovery orchestration)
  - `repositories/` — Data access layer (queries, persistence)
  - `webhooks/` — Razorpay webhook event handlers
  - `policies/` — Deterministic policy engine
- **Deployment**: Render

### Database

- **Technology**: PostgreSQL hosted on Supabase
- **ORM**: SQLAlchemy 2.0 with Alembic migrations
- **Key tables** (planned):
  - Transactions — raw payment data
  - Recovery cases — identified recovery opportunities
  - Recovery actions — proposed and executed actions
  - Audit log — immutable record of all agent decisions
  - Policy rules — configurable policy constraints

### ML Layer

- **Technology**: pandas, NumPy, scikit-learn, XGBoost
- **Purpose**: Predict probability of successful recovery for a given failed payment
- **Structure**:
  - `data/` — raw and processed datasets
  - `preprocessing/` — feature engineering, data cleaning
  - `training/` — model training scripts
  - `models/` — serialized trained models
  - `inference/` — prediction serving
  - `evaluation/` — model evaluation metrics

### AI Agent

- **Technology**: LLM API with structured outputs and tool calling
- **Purpose**: Analyze failed payment context, diagnose root cause, recommend recovery action
- **Critical constraint**: The agent proposes actions but NEVER executes them directly
- **Structure**:
  - `tools/` — tool definitions the LLM can call
  - `prompts/` — system and task prompts
  - `workflows/` — multi-step agent workflows
  - `policies/` — agent-level policy definitions

### Policy Engine

- **Purpose**: Deterministic validation of all agent-proposed actions
- **Properties**:
  - Fully deterministic (no ML/LLM involvement)
  - Validates action type, amount limits, frequency limits, business rules
  - Returns approve/reject/escalate decisions
  - All decisions are logged

### Execution Layer

- **Purpose**: Execute approved recovery actions through Razorpay API
- **Properties**:
  - Only processes policy-approved actions
  - Razorpay Test Mode only during development
  - Idempotent execution
  - Full error handling and retry logic

### Audit Layer

- **Purpose**: Immutable record of all system activity
- **Captures**: Every agent decision, policy evaluation, API call, and recovery outcome
- **Properties**: Append-only, timestamped, includes full context

## Deployment Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Vercel     │     │    Render     │     │   Supabase    │
│  (Frontend)  │────▶│  (Backend)    │────▶│  (PostgreSQL) │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Razorpay    │
                    │  (Test Mode)  │
                    └──────────────┘
```

- **Frontend**: Vercel — automatic deployments from Git
- **Backend**: Render — containerized Python service
- **Database**: Supabase — managed PostgreSQL with built-in auth
- **Payments**: Razorpay Test Mode — sandboxed payment operations
