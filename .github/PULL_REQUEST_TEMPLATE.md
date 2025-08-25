# Pull Request

## Description
Brief description of changes made in this PR.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality) 
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)

## Changes Made
- 
- 
- 

## Testing
- [ ] Preflight checks pass (`python scripts/preflight.py`)
- [ ] All endpoints return expected responses
- [ ] Health check returns 200 with all services healthy
- [ ] Shadow trade execution works correctly
- [ ] No mock data used anywhere in the system

## API Contract Compliance
- [ ] FastAPI app with JSON logging and `/metrics`
- [ ] Strict environment validation (fail-fast on startup)
- [ ] deps.py with httpx, SQLAlchemy, Redis clients  
- [ ] All required routes implemented: `/health`, `/holdings`, `/recommendations`, `/trades/execute`
- [ ] All required services: market, sentiment, scoring, portfolio, execution
- [ ] Database models and Alembic migrations
- [ ] scripts/preflight.py exits non-zero on any failure

## Environment Variables Required
List any new environment variables that need to be set:
- `NEW_VAR_NAME`: Description of what this variable controls

## Database Changes
- [ ] No database changes
- [ ] New migration created
- [ ] Migration tested locally

## Checklist
- [ ] Code follows project conventions
- [ ] Self-review completed
- [ ] No secrets or API keys committed  
- [ ] Structured logging used throughout
- [ ] Error handling implemented
- [ ] README updated if needed