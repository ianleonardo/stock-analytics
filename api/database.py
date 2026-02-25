import os
import asyncpg

def get_pg_url() -> str:
    # FastAPI/asyncpg use postgresql:// not postgresql+asyncpg
    url = os.environ.get("DATABASE_URL_ASYNC", "postgresql+asyncpg://stock:stock@localhost:5432/stock_analytics")
    return url.replace("postgresql+asyncpg://", "postgresql://")

async def get_pool():
    url = get_pg_url()
    # asyncpg expects postgresql://user:pass@host:port/db
    return await asyncpg.create_pool(
        url,
        min_size=1,
        max_size=10,
        command_timeout=60,
    )

async def fetch_historical(conn, ticker: str, limit: int = 200):
    rows = await conn.fetch(
        """
        SELECT open, high, low, close, volume, date::text
        FROM ohlcv_daily
        WHERE symbol = $1
        ORDER BY date DESC
        LIMIT $2
        """,
        ticker.upper(),
        limit,
    )
    return [{"open": r["open"], "high": r["high"], "low": r["low"], "close": r["close"], "volume": r["volume"], "date": r["date"]} for r in rows]

async def fetch_alerts(conn, limit: int = 100):
    rows = await conn.fetch(
        """
        SELECT ticker, alert_type, severity, value, ts
        FROM alerts
        ORDER BY ts DESC
        LIMIT $1
        """,
        limit,
    )
    return [{"ticker": r["ticker"], "type": r["alert_type"], "severity": r["severity"], "value": float(r["value"]) if r["value"] else None, "ts": r["ts"].isoformat() if hasattr(r["ts"], "isoformat") else str(r["ts"])} for r in rows]

async def fetch_top_movers(conn):
    # Latest report: get max(generated_at) then gainers/losers
    row = await conn.fetchrow(
        "SELECT generated_at FROM top_movers ORDER BY generated_at DESC LIMIT 1"
    )
    if not row:
        return {"gainers": [], "losers": [], "generated_at": None}
    gen_at = row["generated_at"]
    gainers = await conn.fetch(
        "SELECT symbol, pct_change, rank_gainers, volume, close FROM top_movers WHERE generated_at = $1 AND rank_gainers IS NOT NULL ORDER BY rank_gainers LIMIT 5",
        gen_at,
    )
    losers = await conn.fetch(
        "SELECT symbol, pct_change, rank_losers, volume, close FROM top_movers WHERE generated_at = $1 AND rank_losers IS NOT NULL ORDER BY rank_losers LIMIT 5",
        gen_at,
    )
    return {
        "gainers": [{"symbol": r["symbol"], "pct_change": float(r["pct_change"]), "rank": r["rank_gainers"], "volume": r["volume"], "close": float(r["close"]) if r["close"] else None} for r in gainers],
        "losers": [{"symbol": r["symbol"], "pct_change": float(r["pct_change"]), "rank": r["rank_losers"], "volume": r["volume"], "close": float(r["close"]) if r["close"] else None} for r in losers],
        "generated_at": gen_at.isoformat() if hasattr(gen_at, "isoformat") else str(gen_at),
    }
