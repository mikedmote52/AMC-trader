# AMC Trading System QA

Black-box acceptance tests for the AMC Trading System.

## Quick Start

```bash
# Run all tests
./scripts/smoke.sh && ./scripts/failcases.sh

# Run against remote deployment
BASE_URL=https://your-app.onrender.com ./scripts/smoke.sh
BASE_URL=https://your-app.onrender.com ./scripts/failcases.sh
```

## Test Scripts

- **`scripts/smoke.sh`** - Basic functionality tests (health, discovery, recommendations, holdings, shadow trades)
- **`scripts/failcases.sh`** - Environment variable failure tests (validates proper 503 responses)

## Requirements

- `curl` and `jq` command-line tools
- Running AMC Trading System (local or remote)
- Required environment variables set for failure testing

## Documentation

See `docs/AC.md` for detailed acceptance criteria and API specifications.