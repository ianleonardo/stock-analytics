-- Stock Analytics Platform: PostgreSQL schema
-- Used by stream layer (alerts), batch layer (OHLCV, reports), and API.

-- Raw trade events (can be written by stream processor or backfill job)
CREATE TABLE IF NOT EXISTS raw_trades (
    id          BIGSERIAL PRIMARY KEY,
    symbol      VARCHAR(20) NOT NULL,
    price       NUMERIC(20, 8) NOT NULL,
    volume      BIGINT NOT NULL,
    trade_ts    BIGINT NOT NULL,
    conditions  TEXT[],
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_raw_trades_symbol_ts ON raw_trades (symbol, trade_ts);
CREATE INDEX IF NOT EXISTS idx_raw_trades_created_at ON raw_trades (created_at);

-- Daily OHLCV (batch job output)
CREATE TABLE IF NOT EXISTS ohlcv_daily (
    id        SERIAL PRIMARY KEY,
    symbol    VARCHAR(20) NOT NULL,
    date      DATE NOT NULL,
    open      NUMERIC(20, 8) NOT NULL,
    high      NUMERIC(20, 8) NOT NULL,
    low       NUMERIC(20, 8) NOT NULL,
    close     NUMERIC(20, 8) NOT NULL,
    volume    BIGINT NOT NULL,
    UNIQUE (symbol, date)
);
CREATE INDEX IF NOT EXISTS idx_ohlcv_daily_symbol_date ON ohlcv_daily (symbol, date);

-- Anomaly alerts (stream processor writes here)
CREATE TABLE IF NOT EXISTS alerts (
    id         SERIAL PRIMARY KEY,
    ticker     VARCHAR(20) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    severity   VARCHAR(20) NOT NULL,
    value      NUMERIC(20, 8),
    ts         TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_alerts_ticker_ts ON alerts (ticker, ts);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts (created_at DESC);

-- Top movers report (batch job)
CREATE TABLE IF NOT EXISTS top_movers (
    id           SERIAL PRIMARY KEY,
    generated_at TIMESTAMPTZ NOT NULL,
    symbol       VARCHAR(20) NOT NULL,
    pct_change   NUMERIC(10, 4) NOT NULL,
    rank_gainers INT,
    rank_losers  INT,
    volume       BIGINT,
    close        NUMERIC(20, 8)
);
CREATE INDEX IF NOT EXISTS idx_top_movers_generated ON top_movers (generated_at DESC);

-- Most volatile report (batch job)
CREATE TABLE IF NOT EXISTS most_volatile (
    id           SERIAL PRIMARY KEY,
    generated_at TIMESTAMPTZ NOT NULL,
    symbol       VARCHAR(20) NOT NULL,
    avg_volatility NUMERIC(20, 8) NOT NULL,
    rank         INT,
    volume       BIGINT
);
CREATE INDEX IF NOT EXISTS idx_most_volatile_generated ON most_volatile (generated_at DESC);

-- Batch job execution log
CREATE TABLE IF NOT EXISTS job_logs (
    id          SERIAL PRIMARY KEY,
    job_name    VARCHAR(100) NOT NULL,
    started_at  TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    status      VARCHAR(20) NOT NULL,
    rows_processed BIGINT,
    message     TEXT
);
CREATE INDEX IF NOT EXISTS idx_job_logs_job_started ON job_logs (job_name, started_at DESC);
