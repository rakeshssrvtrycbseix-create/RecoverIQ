# RecoverIQ — Development Rules

## Coding Standards

### Python (Backend, ML, Agent)

- Python >= 3.11
- Use type hints on all function signatures
- Use Pydantic models for data validation
- Use `ruff` for linting and formatting
- Line length: 88 characters
- Follow PEP 8 naming conventions
- Write docstrings for all public functions and classes

### TypeScript (Frontend)

- Strict TypeScript — no `any` unless absolutely necessary
- Use ESLint with Next.js recommended rules
- Use functional components with hooks
- Define interfaces for all props and API responses

### General

- Prefer simple, maintainable solutions over clever abstractions
- Avoid unnecessary dependencies
- Keep functions small and focused
- Use clear, descriptive names

## Security Rules

### Secrets Management

- **NEVER** hardcode secrets in source code
- **NEVER** commit `.env` files
- Use environment variables for all credentials
- Store secrets in `.env` locally, use platform secret management in production
- `.env.example` contains placeholder keys only — never real values

### Credentials That Must NEVER Be Committed

- Razorpay key ID and secret
- LLM API keys
- Supabase service keys
- Database passwords and connection strings
- JWT secrets
- Any authentication tokens

## AI Safety Rules

### Mandatory Architecture

The AI agent must NEVER have direct access to financial APIs.

All AI-initiated actions must follow this flow:

```
AI Agent proposes action
        ↓
Policy Engine validates (deterministic)
        ↓
Action Executor calls Razorpay API
```

### Prohibited Patterns

```
# NEVER DO THIS
AI Agent → Razorpay API

# NEVER DO THIS
AI Agent with Razorpay credentials
```

### Policy Engine Requirements

- Must be fully deterministic (no ML/LLM)
- Must validate: action type, amount, frequency, business rules
- Must return: approve / reject / escalate-to-human
- Must log every decision with full context

## Git Conventions

### Branch Naming

- `main` — production-ready code
- `feature/<name>` — new features
- `fix/<name>` — bug fixes
- `chore/<name>` — maintenance tasks

### Commit Messages

Use conventional commits:

- `feat: add payment webhook handler`
- `fix: correct recovery probability calculation`
- `chore: update dependencies`
- `docs: add API documentation`
- `test: add policy engine unit tests`
- `refactor: extract risk scoring service`

### Pull Requests

- Write a clear description of changes
- Reference related issues
- Ensure all tests pass before merging

## Testing Expectations

### Backend

- Use `pytest` for all tests
- Test all API endpoints
- Test business logic in services
- Test policy engine rules
- Aim for meaningful coverage, not 100% line coverage

### Frontend

- Ensure the project builds without errors
- TypeScript type checking must pass
- Add component tests for critical UI flows

### ML

- Validate model inputs and outputs
- Test preprocessing pipelines with known data
- Log evaluation metrics for every training run

## Error Handling Principles

- Handle errors explicitly — never silently swallow exceptions
- Use appropriate HTTP status codes in API responses
- Return structured error responses with clear messages
- Log errors with sufficient context for debugging
- Distinguish between client errors (4xx) and server errors (5xx)
- Use Pydantic validation for input validation — don't write manual checks for what Pydantic handles

## Separation of Concerns

- **API routes**: HTTP handling, request/response serialization only
- **Services**: Business logic, orchestration
- **Repositories**: Data access, queries
- **Models**: Database schema definitions
- **Schemas**: Request/response validation
- **Policies**: Deterministic rule evaluation
- **AI logic**: Kept separate from payment execution at all times
