# PostgreSQL Setup for AMC-TRADER

## Option 1: Separate Database (Recommended - Zero Risk to Other Program)

### Step 1: Create New Database

```bash
# Connect to PostgreSQL (replace with your credentials)
psql -U your_username -h localhost

# Create dedicated database for AMC-TRADER
CREATE DATABASE amc_trader;

# Exit
\q
```

### Step 2: Update AMC-TRADER Environment

Edit `/Users/michaelmote/Desktop/AMC-TRADER/.env`:

```bash
# Replace the placeholder with your real connection
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/amc_trader
```

### Step 3: Run Migration

```bash
cd /Users/michaelmote/Desktop/AMC-TRADER/backend

# Create volume_averages table in amc_trader database
psql postgresql://your_username:your_password@localhost:5432/amc_trader \
  -f migrations/001_add_volume_cache.sql
```

### Step 4: Verify Setup

```bash
# Check table exists
psql postgresql://your_username:your_password@localhost:5432/amc_trader \
  -c "\dt"

# Should show:
#  Schema |      Name       | Type  |  Owner
# --------+-----------------+-------+----------
#  public | volume_averages | table | your_username
```

### Step 5: Populate Cache

```bash
cd /Users/michaelmote/Desktop/AMC-TRADER/backend

# Test mode (100 stocks)
export POLYGON_API_KEY=1ORwpSzeOV20X6uaA8G3Zuxx7hLJ0KIC
python3 -m app.jobs.refresh_volume_cache test

# Full population (8,000+ stocks) - takes ~30-45 min
# python3 -m app.jobs.refresh_volume_cache
```

---

## Option 2: Separate Schema (Same Database)

If you want to use the same database as your other program:

```bash
# Connect to your existing database
psql -U your_username -d your_existing_database

# Create separate schema for AMC-TRADER
CREATE SCHEMA amc_trader;

# Create table in AMC schema
CREATE TABLE amc_trader.volume_averages (
    symbol VARCHAR(10) PRIMARY KEY,
    avg_volume_20d BIGINT NOT NULL,
    avg_volume_30d BIGINT,
    last_updated TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT positive_volume CHECK (avg_volume_20d > 0)
);

# Update DATABASE_URL to include schema
DATABASE_URL=postgresql://user:pass@localhost:5432/your_db?options=-c%20search_path=amc_trader
```

---

## Option 3: Table Prefix (Shared Schema)

Use prefixed table names:

```bash
# Rename table to avoid conflicts
# Change volume_averages → amc_volume_averages
# Change all queries in code to use prefix
```

**Not recommended** - requires code changes.

---

## Verification Checklist

After setup, verify everything works:

### 1. Database Connection
```bash
psql $DATABASE_URL -c "SELECT 1;"
# Should return: 1
```

### 2. Table Exists
```bash
psql $DATABASE_URL -c "\d volume_averages"
# Should show table structure
```

### 3. Cache Population Works
```bash
cd /Users/michaelmote/Desktop/AMC-TRADER/backend
export POLYGON_API_KEY=1ORwpSzeOV20X6uaA8G3Zuxx7hLJ0KIC
python3 -m app.jobs.refresh_volume_cache test
```

Expected output:
```
🔄 Starting volume cache refresh job...
Fetching active symbols from bulk snapshot...
Refreshing 100 active symbols...
Batch 1: 68 processed, 32 skipped, 0 errors (24.1s)
✅ Database updated: 68 records
```

### 4. Check Cached Data
```bash
psql $DATABASE_URL -c "
SELECT
  COUNT(*) as total_cached,
  MAX(last_updated) as latest_update
FROM volume_averages;
"
```

Should show:
```
 total_cached |     latest_update
--------------+------------------------
           68 | 2025-10-06 08:45:23.123
```

---

## Safety Notes

✅ **Option 1 (Separate Database) is safest:**
- Complete isolation from other program
- No risk of table name conflicts
- Can drop entire database if needed
- Recommended for production

✅ **Option 2 (Separate Schema) is also safe:**
- Same PostgreSQL server
- Different namespace
- Good if you want logical grouping

⚠️ **Option 3 (Table Prefix) requires code changes:**
- Not recommended
- Risk of human error
- Harder to maintain

---

## Quick Setup Commands (Copy-Paste)

If you already have PostgreSQL running:

```bash
# 1. Create database
psql -U your_username -h localhost -c "CREATE DATABASE amc_trader;"

# 2. Run migration
cd /Users/michaelmote/Desktop/AMC-TRADER/backend
psql postgresql://your_username:your_password@localhost:5432/amc_trader \
  -f migrations/001_add_volume_cache.sql

# 3. Update .env
echo "DATABASE_URL=postgresql://your_username:your_password@localhost:5432/amc_trader" \
  >> /Users/michaelmote/Desktop/AMC-TRADER/.env

# 4. Test connection
psql postgresql://your_username:your_password@localhost:5432/amc_trader \
  -c "SELECT 1;"

# 5. Populate cache (test mode)
export POLYGON_API_KEY=1ORwpSzeOV20X6uaA8G3Zuxx7hLJ0KIC
cd /Users/michaelmote/Desktop/AMC-TRADER/backend
python3 -m app.jobs.refresh_volume_cache test
```

Replace `your_username` and `your_password` with your actual PostgreSQL credentials.

---

## Troubleshooting

### "FATAL: database 'amc_trader' does not exist"
```bash
# Create it first
psql -U your_username -c "CREATE DATABASE amc_trader;"
```

### "FATAL: role 'username' does not exist"
```bash
# Check your PostgreSQL username
psql -l
# Use the username from the list
```

### "permission denied for schema public"
```bash
# Grant permissions
psql -U your_username -d amc_trader -c "
GRANT ALL PRIVILEGES ON SCHEMA public TO your_username;
"
```

### "relation 'volume_averages' does not exist"
```bash
# Run migration
psql $DATABASE_URL -f backend/migrations/001_add_volume_cache.sql
```

---

**Bottom Line:** Option 1 (separate database) is the safest and cleanest. Your other program won't be affected at all.
