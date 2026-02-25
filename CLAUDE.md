# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

This is a **capstone project** for a Real-Time Stock Market Analytics Platform. The repository is in early development — the source directories do not yet exist. The full implementation plan is in `implementation-plan/stock_analytics_implementation_plan.docx` and the GCP deployment plan is in `implementation-plan/gcp_deployment_plan.docx`.

## Planned Directory Structure

```
stock-analytics/
  ├── docker-compose.yml
  ├── .env
  ├── ingestion/          # Kafka producer (Finnhub WebSocket → trades-raw topic)
  ├── stream-processing/  # Spark Structured Streaming jobs (VWAP, EMA, anomaly detection)
  ├── batch-processing/   # Nightly Spark batch jobs (OHLCV, top movers, volatility)
  ├── api/                # FastAPI backend (REST + WebSocket /ws/live)
  ├── frontend/           # React 18 dashboard
  ├── redis/              # Redis config
  └── airflow/            # DAGs for nightly batch scheduling
```

## Tech Stack

| Layer | Technology |
|---|---|
| Data source | Finnhub WebSocket (`wss://ws.finnhub.io?token=...`) |
| Message broker | Apache Kafka (Confluent 7.4) via Docker Compose |
| Stream processing | Apache Spark 3.5 Structured Streaming |
| Cache / Pub-Sub | Redis 7 |
| Database | PostgreSQL 15 |
| API backend | FastAPI (async, `aioredis`, `asyncpg`) |
| Frontend | React 18, TradingView Lightweight Charts, Recharts, Tailwind, Zustand, React Query |
| Batch scheduler | Apache Airflow 2.7 |
| Infrastructure | Docker Compose (local), GKE + Cloud Run + Dataproc (GCP) |

## Development Setup

Prerequisites: Docker & Docker Compose v24+, Python 3.10+, Node.js 18+, a Finnhub free API key.

```bash
# Start all infrastructure services
docker compose up -d

# Run the Finnhub Kafka producer
python ingestion/producer.py

# Submit Spark streaming job
docker exec spark-master spark-submit stream-processing/vwap_streaming.py

# Start FastAPI backend
cd api && uvicorn main:app --reload --port 8000

# Start React frontend
cd frontend && npm install && npm run dev

# Run Python tests (from any service directory)
pytest tests/

# Run a single test file
pytest tests/test_producer.py

# Run a single test
pytest tests/test_vwap.py::test_vwap_formula
```

## Architecture & Data Flow

```
Finnhub WebSocket
  → ingestion/ (confluent-kafka producer, partitioned by symbol)
  → Kafka topic: trades-raw (5 partitions, 48h retention)
  → stream-processing/ (Spark micro-batches every 5s)
      computes: VWAP (1m/5m/15m), EMA-9, EMA-21, rolling volatility, volume anomalies
  → Redis HSET trades:metrics:{symbol} (TTL 120s) + Pub/Sub live:{symbol}
  → PostgreSQL: raw_trades, alerts tables
  → api/ (FastAPI /ws/live subscribes to Redis Pub/Sub, forwards to frontend)
  → frontend/ (Zustand store → chart and indicator re-renders)

Nightly (00:05):
  Airflow DAG → Spark batch job
  → PostgreSQL raw_trades → ohlcv_daily, top_movers, most_volatile tables
```

## Key Implementation Details

**Kafka Topics:** `trades-raw`, `trades-metrics`, `trades-alerts` — 5 partitions, replication factor 1 for local dev.

**Spark VWAP:** `sum(price × volume) / sum(volume)` over tumbling windows with 30s watermark for late data.

**Spark EMA:** Stateful via `mapGroupsWithState`; formula `EMA = price × (2/(period+1)) + prevEMA × (1 − 2/(period+1))`.

**Anomaly detection:** Volume > 2× 10-minute rolling average → publish alert to `trades-alerts` Kafka topic and write to PostgreSQL `alerts` table.

**Redis key patterns:**
- `trades:metrics:{symbol}` — Hash, TTL 120s
- `leaderboard:gainers` / `leaderboard:losers` — Sorted Sets
- `alerts:recent` — List, capped at 100 via LTRIM
- `live:{symbol}` — Pub/Sub channel
- `price:{symbol}` — String with 10s TTL

**FastAPI:** Uses `aioredis` (async), `asyncpg`/SQLAlchemy async, Pydantic models for all I/O. WebSocket `/ws/live` subscribes to Redis Pub/Sub per ticker. Include `/health` endpoint.

**React chart performance:** Use `useRef` for chart container; call `chart.update()` only — never re-render the chart component. Seed from `GET /api/historical/{ticker}` (last 200 candles) then append live updates.

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/tickers` | List tracked symbols |
| `GET /api/metrics/{ticker}` | Latest streaming metrics from Redis |
| `GET /api/historical/{ticker}` | OHLCV history from PostgreSQL |
| `GET /api/reports/top-movers` | Batch report (gainers/losers) |
| `GET /api/alerts` | Recent anomaly alerts |
| `WS /ws/live` | Live Redis Pub/Sub stream |

## GCP Deployment (see `implementation-plan/gcp_deployment_plan.docx`)

Local Docker services map to GCP managed equivalents: Kafka → Cloud Pub/Sub, Spark → Dataproc, Redis → Memorystore, PostgreSQL → Cloud SQL, FastAPI → Cloud Run, React → Firebase Hosting, Kafka producer → GKE, Airflow → Cloud Composer or Cloud Scheduler + Cloud Functions.

Target region: `asia-southeast1`. Secrets via Secret Manager (never in `.env` committed to git). VPC private networking required — Memorystore and Cloud SQL are not public-internet accessible.

CI/CD via Cloud Build (`cloudbuild.yaml`) triggered on push to `main`.
