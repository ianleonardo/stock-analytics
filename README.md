# Stock Analytics Platform

Real-time stock market analytics: Finnhub → Kafka → Spark (stream + batch) → Redis/PostgreSQL → FastAPI → React dashboard.

## Prerequisites

- Docker & Docker Compose v24+
- Python 3.10+ (for local runs)
- Node.js 18+ (for frontend dev)
- [Finnhub](https://finnhub.io) API key (free tier)

## Quick start

1. Copy env and set your API key:
   ```bash
   cp .env.example .env
   # Edit .env: set FINNHUB_API_KEY=your_key
   ```

2. Start infrastructure and services:
   ```bash
   docker compose up -d
   ```
   This starts Zookeeper, Kafka, Redis, PostgreSQL, Spark (master + worker), ingestion (Finnhub → Kafka), API, and frontend.

3. Open the dashboard: http://localhost:3000  
   API: http://localhost:8000  
   API docs: http://localhost:8000/docs  

4. (Optional) Run the Spark streaming job so metrics and alerts are computed and written to Redis/PostgreSQL. From the repo root with Kafka and Redis running:
   ```bash
   cd stream-processing
   pip install -r requirements.txt
   KAFKA_BOOTSTRAP_SERVERS=localhost:9092 REDIS_HOST=localhost PG_HOST=localhost spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 streaming_job.py
   ```

5. (Optional) Run the nightly batch job (OHLCV + reports):
   ```bash
   cd batch-processing
   pip install -r requirements.txt
   python batch_job.py
   ```
   Or schedule via Airflow: see `airflow/dags/stock_batch_dag.py` (set `BATCH_JOB_DIR` and PG_* env).

## Project layout

- `ingestion/` — Kafka producer (Finnhub WebSocket → `trades-raw`)
- `stream-processing/` — Spark Structured Streaming (VWAP, EMA, volatility, alerts → Redis + PostgreSQL)
- `batch-processing/` — Nightly OHLCV and top movers / most volatile reports
- `api/` — FastAPI (REST + WebSocket `/ws/live`)
- `frontend/` — React dashboard (Vite, Tailwind, Zustand, Lightweight Charts)
- `scripts/init-db.sql` — PostgreSQL schema
- `airflow/dags/` — DAG for nightly batch

## Testing

- **API**: From `api/` with Redis and Postgres up: `pip install -r requirements-dev.txt && pytest`
- **Ingestion**: From `ingestion/`: `pip install -r requirements.txt && pytest tests/`
- **Integration / benchmarks**: See `docs/BENCHMARKS.md` and `tests/integration/test_e2e_notes.md`

## Environment variables

See `.env.example`. Main ones: `FINNHUB_API_KEY`, `KAFKA_BOOTSTRAP_SERVERS`, `TICKERS`, `REDIS_URL`, `DATABASE_URL_ASYNC`.
