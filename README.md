# AMC Discovery Pipeline

Discovery job pipeline for finding and scoring stock opportunities using Polygon API data and sentiment analysis.

## Features

- **Market Hours Aware**: Automatically adjusts behavior based on market status
- **Redis Locking**: Prevents job overlap with 4-minute TTL
- **Sentiment Analysis**: Computes sentiment scores during market hours only
- **Technical Analysis**: Always computes technical scores based on price/volume data
- **Database Storage**: Writes recommendations to PostgreSQL database
- **Clean Off-Hours Exit**: Returns zero exit code with "insufficient live sentiment" during market close

## Quick Start

### Prerequisites

1. **PostgreSQL Database**: Running instance with database created
2. **Redis Server**: Running instance for job locking
3. **Polygon API Key**: Sign up at [Polygon.io](https://polygon.io)

### Installation

```bash
# Clone the repository and navigate to project
cd AMC-discovery

# Install Python dependencies
pip install -r backend/requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
DATABASE_URL=postgresql://username:password@localhost:5432/amc_trader
REDIS_URL=redis://localhost:6379/0
POLYGON_API_KEY=your_polygon_api_key_here
UNIVERSE_FILE=data/universe.txt
```

### Running Locally

#### Test Run (Recommended)
```bash
# Run once and see JSON output
cd backend/src/jobs
python run_once.py
```

This will:
- Execute the full discovery pipeline once
- Show detailed execution summary
- Print JSON results for analysis
- Use appropriate exit codes

#### Production Run
```bash
# Run the scheduled job (same as cron would execute)
cd backend/src/jobs  
python discover.py
```

#### Example Output

During **market hours**:
```json
{
  "success": true,
  "recommendations_count": 12,
  "symbols_processed": 14,
  "symbols_with_sentiment": 12,
  "market_status": {
    "is_open": true,
    "current_time_et": "2024-08-25 14:30:45 EDT",
    "is_weekend": false,
    "day_of_week": "Sunday"
  },
  "duration_seconds": 8.42
}
```

During **off-hours**:
```json
{
  "success": true,
  "reason": "insufficient live sentiment", 
  "recommendations_count": 0,
  "market_status": {
    "is_open": false,
    "current_time_et": "2024-08-25 18:15:30 EDT",
    "is_weekend": false,
    "day_of_week": "Sunday"
  },
  "duration_seconds": 3.21
}
```

## Architecture

### Directory Structure
```
AMC-discovery/
├── backend/
│   ├── src/
│   │   ├── jobs/
│   │   │   ├── discover.py      # Main discovery job
│   │   │   └── run_once.py      # Local testing script
│   │   └── shared/
│   │       ├── database.py      # Database models and connection
│   │       ├── redis_client.py  # Redis locking utilities
│   │       └── market_hours.py  # Market status utilities
│   └── requirements.txt
├── data/
│   └── universe.txt            # Stock symbols to analyze
└── .env.example               # Environment template
```

### Pipeline Flow

1. **Lock Acquisition**: Redis lock prevents overlapping jobs (4-minute TTL)
2. **Universe Loading**: Read symbols from `data/universe.txt`
3. **Price Fetching**: Get latest prices/volume from Polygon API
4. **Sentiment Analysis**: Compute scores only during market hours
5. **Technical Analysis**: Always compute technical scores
6. **Score Composition**: Combine sentiment + technical into composite score
7. **Database Write**: Store recommendations with timestamps

### Market Hours Behavior

- **Market Open (9:30 AM - 4:00 PM ET)**:
  - Full sentiment + technical analysis
  - Writes recommendations to database
  - Normal exit code (0) on success

- **Market Closed**:
  - Technical analysis only (no sentiment)
  - Clean exit with "insufficient live sentiment" reason
  - Zero exit code (not an error condition)

### Scoring Algorithm

```python
# During market hours
composite_score = (sentiment_score * 0.6) + (technical_score * 0.4)

# During off-hours  
composite_score = technical_score  # Sentiment = None
```

## Database Schema

### `recommendations` Table
```sql
CREATE TABLE recommendations (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    sentiment_score FLOAT,           -- NULL during off-hours
    technical_score FLOAT NOT NULL,
    composite_score FLOAT NOT NULL,
    price FLOAT NOT NULL,
    volume INTEGER,
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Troubleshooting

### Common Issues

1. **Lock Already Exists**
   - Another job is running
   - Wait for completion or check Redis: `redis-cli GET discovery_job_lock`

2. **No Price Data**
   - Check Polygon API key and network connectivity
   - Verify symbols in universe.txt are valid

3. **Database Connection Failed**
   - Verify PostgreSQL is running and DATABASE_URL is correct
   - Check database permissions

4. **Redis Connection Failed**
   - Ensure Redis server is running
   - Verify REDIS_URL configuration

### Debugging

Enable debug logging:
```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

Check job status in Redis:
```bash
redis-cli GET discovery_job_lock
```

## Deployment

For production deployment, run as cron job:

```cron
# Run every 5 minutes during market hours
*/5 9-16 * * 1-5 cd /path/to/AMC-discovery/backend/src/jobs && python discover.py
```

The job will automatically handle off-hours with clean exits.<!-- API redeploy trigger Mon Aug 25 18:20:26 PDT 2025 -->
<!-- Debug deploy trigger Mon Aug 25 18:40:00 PDT 2025 -->
