# AMC-Trader Infrastructure

This repository contains the deployment infrastructure for the AMC-Trader system.

## Architecture

The system is deployed on Render with three services:

- **API Service** (Docker web): Main application backend
- **UI Service** (Static site): Frontend application  
- **Cron Service** (Python): Automated discovery jobs

## Environment Variables

### API Service (`amc-api`)

| Variable | Description | Required |
|----------|-------------|----------|
| `ALPACA_API_KEY` | Alpaca trading API key | ✅ |
| `ALPACA_SECRET_KEY` | Alpaca trading secret key | ✅ |
| `ALPACA_BASE_URL` | Alpaca API base URL (paper: https://paper-api.alpaca.markets) | ✅ |
| `CLAUDE_API_KEY` | Claude AI API key for analysis | ✅ |
| `POLYGON_API_KEY` | Polygon market data API key | ✅ |
| `NODE_ENV` | Node environment (production) | ✅ |
| `PORT` | Server port (default: 10000) | ✅ |

### Cron Service (`amc-cron`)

| Variable | Description | Required |
|----------|-------------|----------|
| `ALPACA_API_KEY` | Alpaca trading API key | ✅ |
| `ALPACA_SECRET_KEY` | Alpaca trading secret key | ✅ |
| `ALPACA_BASE_URL` | Alpaca API base URL | ✅ |
| `CLAUDE_API_KEY` | Claude AI API key for analysis | ✅ |
| `POLYGON_API_KEY` | Polygon market data API key | ✅ |
| `PYTHONPATH` | Python module path (.) | ✅ |

### UI Service (`amc-ui`)

| Variable | Description | Required |
|----------|-------------|----------|
| `NODE_ENV` | Node environment (production) | ✅ |

## Copy-Paste Environment Table for Render

```
# API Service Environment Variables
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets
CLAUDE_API_KEY=your_claude_api_key_here
POLYGON_API_KEY=your_polygon_api_key_here
NODE_ENV=production
PORT=10000

# Cron Service Environment Variables  
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets
CLAUDE_API_KEY=your_claude_api_key_here
POLYGON_API_KEY=your_polygon_api_key_here
PYTHONPATH=.

# UI Service Environment Variables
NODE_ENV=production
```

## Deployment

1. **Environment Validation**: Run `python scripts/check_env.py` to validate required environment variables
2. **Manual Deploy**: Use the Render dashboard to deploy from the `main` branch
3. **Automated Deploy**: Push to `main` branch triggers automatic deployment via GitHub Actions

## Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for API service)

### Local Development

```bash
# Validate environment
python scripts/check_env.py --service api

# Run environment check with strict warnings
python scripts/check_env.py --strict
```

## Service Configuration

### Health Checks

- **API Service**: `GET /health` endpoint
- **Cron Service**: Process-based health monitoring
- **UI Service**: Static file serving health

### Scaling

- **Region**: Oregon (us-west-1)
- **Plan**: Starter tier for all services
- **Cron Schedule**: 9 AM weekdays (0 9 * * 1-5)

## CI/CD Pipeline

The GitHub Actions workflow includes:

1. **Backend Linting**: flake8, black, isort, mypy
2. **Frontend Build**: Deterministic builds with NODE_ENV and SOURCE_DATE_EPOCH
3. **Deploy**: Automatic deployment to Render on main branch

## Files Structure

```
├── infra/
│   └── render.yaml              # Render service definitions
├── .github/workflows/
│   └── deploy.yml               # CI/CD pipeline
├── scripts/
│   └── check_env.py             # Environment validation
└── README.md                    # This file
```