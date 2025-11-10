# Cryptocurrency Data Pipeline - Assessment Submission

A production-ready data engineering pipeline demonstrating ingestion, transformation, and modeling of cryptocurrency market data.

## Table of Contents
- [Quick Start](#quick-start)
- [Dependencies and Setup](#dependencies-and-setup)
- [Data Source](#data-source)
- [Running the Pipeline End-to-End](#running-the-pipeline-end-to-end)
- [Validating Data Movement](#validating-data-movement)

---

## Quick Start

### Prerequisites
- Docker Desktop installed
- 4GB RAM available  
- Internet connection

### Start Pipeline
```bash
git clone https://github.com/julesSAWAdev/assesment-solution.git  
cd assesment-solution
docker-compose up -d --build

# Wait 30 seconds, then run:
docker exec -it crypto_pipeline_runner python scripts/run_pipeline.py
```

---

## Dependencies and Setup

### System Requirements
- Docker 20.10+
- Docker Compose 2.0+
- Ports available: 3000 (Dagster), 5432 (PostgreSQL)

### Python Dependencies (Auto-installed in containers)
- `requests` - API calls
- `pandas` - Data manipulation  
- `sqlalchemy` - Database ORM
- `psycopg2` - PostgreSQL driver
- `pyarrow` - Parquet support
- `dagster` - Orchestration

### Setup Steps
1. Extract project files
2. Run `docker-compose up -d --build`
3. Verify: `docker-compose ps` shows 3 running containers

---

## Data Source

### CoinGecko API
**URL**: https://www.coingecko.com/en/api  
**Endpoint**: `GET /api/v3/coins/markets`

**Why CoinGecko:**
- Free, no authentication required
- 10-50 requests/minute rate limit
- 30+ attributes per cryptocurrency
- Real-time market data

**Data Fetched** (100 cryptocurrencies):
- Price & market cap
- 24h trading volume
- Price changes (24h, 7d, 30d)
- All-time high/low
- Circulating supply
- Market cap ranking

**Sample Request:**
```
GET https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100
```

---

## Running the Pipeline End-to-End

### Method 1: Complete Pipeline (Recommended)
```bash
docker exec -it crypto_pipeline_runner python scripts/run_pipeline.py
```

**Expected Output:**
```
======================================================================
 CRYPTO DATA PIPELINE - FULL EXECUTION
======================================================================
 STAGE 1: DATA INGESTION (Bronze Layer)
----------------------------------------------------------------------
Fetching data from CoinGecko API...
✓ Ingested 100 records
✓ Stored JSON & Parquet files

 STAGE 2: TRANSFORMATION & LOADING (Silver Layer)  
----------------------------------------------------------------------
✓ Transformed 100 records
✓ Loaded to staging_crypto_market

 STAGE 3: DATA MODELING (Gold Layer)
----------------------------------------------------------------------
✓ Analytics mart created with 50 records
✓ Market segment analysis completed
✓ Total time: 5-10 seconds
```

### Method 2: Via Dagster UI
1. Open http://localhost:3000
2. Click "Assets" 
3. Click "Materialize all"
4. Monitor progress

### Method 3: Individual Stages
```bash
# Stage 1: Ingestion
docker exec -it crypto_pipeline_runner python scripts/ingest.py

# Stage 2: Transformation  
docker exec -it crypto_pipeline_runner python scripts/transform.py

# Stage 3: Modeling
docker exec -it crypto_pipeline_runner python scripts/models.py
```

---

## Validating Data Movement

### Stage 1: Bronze Layer (Raw Files)

**Validate files created:**
```bash
docker exec crypto_pipeline_runner ls -lh /opt/dagster/app/data/raw/$(date +%Y-%m-%d)/
```

**Expected:**
```
crypto_raw_YYYYMMDD_HHMMSS.json     (~110 KB)
crypto_raw_YYYYMMDD_HHMMSS.parquet  (~45 KB)
```

**View sample data:**
```bash
docker exec crypto_pipeline_runner head -20 /opt/dagster/app/data/raw/$(date +%Y-%m-%d)/*.json
```

✅ **Success criteria:**
- Both files exist in date folder
- JSON is readable
- Parquet is ~60% smaller

---

### Stage 2: Silver Layer (Staging Table)

**Check table exists:**
```bash
docker exec -it crypto_postgres psql -U pipeline_user -d crypto_data -c "\dt"
```

**Expected:** Table `staging_crypto_market` appears

**Validate record count:**
```bash
docker exec -it crypto_postgres psql -U pipeline_user -d crypto_data -c "
SELECT COUNT(*) as records, MAX(processed_at) as last_updated 
FROM staging_crypto_market;"
```

**Expected:**
```
 records |       last_updated
---------+---------------------------
     100 | 2025-11-09 20:11:48
```

**View sample data:**
```bash
docker exec -it crypto_postgres psql -U pipeline_user -d crypto_data -c "
SELECT symbol, name, current_price, market_cap_category 
FROM staging_crypto_market 
ORDER BY market_cap_rank 
LIMIT 5;"
```

**Expected:**
```
 symbol |   name    | current_price | market_cap_category
--------+-----------+---------------+--------------------
 BTC    | Bitcoin   |      43250.50 | large_cap
 ETH    | Ethereum  |       2280.75 | large_cap
 ...
```

**Verify transformations:**
```bash
docker exec -it crypto_postgres psql -U pipeline_user -d crypto_data -c "
SELECT symbol, 
       ROUND(price_volatility_24h, 2) as volatility,
       ROUND(volume_to_mcap_ratio, 4) as liquidity
FROM staging_crypto_market 
WHERE market_cap_rank <= 5;"
```

✅ **Success criteria:**
- 100 records in table
- Derived columns present (market_cap_category, price_volatility_24h, volume_to_mcap_ratio)
- No NULL in required fields
- Recent processed_at timestamp

---

### Stage 3: Gold Layer (Analytics Tables)

**1. Analytics Mart**
```bash
docker exec -it crypto_postgres psql -U pipeline_user -d crypto_data -c "
SELECT COUNT(*) FROM crypto_analytics_mart;"
```

**Expected:** 50 records (top 50 cryptocurrencies)

**View top performers:**
```bash
docker exec -it crypto_postgres psql -U pipeline_user -d crypto_data -c "
SELECT symbol, name, 
       ROUND(market_dominance_pct, 2) as dominance,
       price_trend_category 
FROM crypto_analytics_mart 
ORDER BY market_cap_rank 
LIMIT 10;"
```

**Expected:**
```
 symbol |   name    | dominance | price_trend_category
--------+-----------+-----------+---------------------
 BTC    | Bitcoin   |     48.23 | moderate_gain
 ETH    | Ethereum  |     18.45 | moderate_gain
 ...
```

**2. Market Segments**
```bash
docker exec -it crypto_postgres psql -U pipeline_user -d crypto_data -c "
SELECT * FROM market_segment_analysis;"
```

**Expected:**
```
   segment   | crypto_count | segment_sentiment
-------------+--------------+-------------------
 large_cap   |           10 | bullish
 mid_cap     |           40 | neutral
 small_cap   |           50 | bearish
```

**3. Market Summary**
```bash
docker exec -it crypto_postgres psql -U pipeline_user -d crypto_data -c "
SELECT * FROM crypto_market_summary;"
```

**Expected:**
```
 total_cryptocurrencies | gainers | losers
-----------------------+---------+--------
                   100 |      58 |     42
```

**4. Verify Indexes**
```bash
docker exec -it crypto_postgres psql -U pipeline_user -d crypto_data -c "
SELECT tablename, indexname 
FROM pg_indexes 
WHERE tablename LIKE '%crypto%' OR tablename LIKE '%market%'
ORDER BY tablename;"
```

**Expected indexes:**
- `idx_mart_rank` on crypto_analytics_mart
- `idx_mart_price_trend` on crypto_analytics_mart  
- `idx_market_cap_rank` on staging_crypto_market
- `idx_segment_sentiment` on market_segment_analysis

✅ **Success criteria:**
- Analytics mart has 50 records
- 3 market segments with sentiment
- Summary view shows aggregates
- Strategic indexes created

---

### Complete Validation (One Command)
```bash
docker exec -it crypto_postgres psql -U pipeline_user -d crypto_data << 'EOF'
\echo '===== PIPELINE VALIDATION ====='
\echo ''
\echo 'Stage 2: Staging Table'
SELECT COUNT(*) as records FROM staging_crypto_market;
\echo ''
\echo 'Stage 3: Analytics Tables'
SELECT 'crypto_analytics_mart' as table, COUNT(*) as records FROM crypto_analytics_mart
UNION ALL
SELECT 'market_segment_analysis', COUNT(*) FROM market_segment_analysis;
\echo ''
\echo 'Market Summary:'
SELECT * FROM crypto_market_summary;
EOF
```

---

## Validation Checklist

- [ ] **Bronze**: Files in `data/raw/YYYY-MM-DD/` (JSON + Parquet)
- [ ] **Silver**: 100 records in `staging_crypto_market` 
- [ ] **Gold**: 50 records in `crypto_analytics_mart`
- [ ] **Gold**: 3 segments in `market_segment_analysis`
- [ ] **Indexes**: Created on key columns
- [ ] **Data Quality**: No NULLs in required fields

---

## Architecture
```
CoinGecko API (100 cryptos)
         ↓
BRONZE: data/raw/ (JSON + Parquet)
         ↓
SILVER: staging_crypto_market (PostgreSQL)
         ↓  
GOLD:   crypto_analytics_mart + market_segment_analysis
```

---

## Troubleshooting

**Services won't start:**
```bash
docker-compose restart
```

**No data in database:**
```bash
docker exec -it crypto_pipeline_runner python scripts/run_pipeline.py
```

**Check logs:**
```bash
docker-compose logs -f
```

---

For detailed architecture and design decisions, see `REPORT.md`.