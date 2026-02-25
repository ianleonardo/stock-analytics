"""
Nightly batch job: read raw_trades for previous day, compute OHLCV,
daily returns, top_movers and most_volatile reports. Write to PostgreSQL.
"""
import os
import sys
from datetime import datetime, timedelta

import psycopg2
from psycopg2.extras import execute_values

PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_PORT = int(os.environ.get("PG_PORT", "5432"))
PG_DB = os.environ.get("PG_DATABASE", "stock_analytics")
PG_USER = os.environ.get("PG_USER", "stock")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "stock")


def run():
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
    )
    conn.autocommit = False
    cur = conn.cursor()

    # Previous trading day (use yesterday for simplicity)
    target_date = (datetime.utcnow() - timedelta(days=1)).date()
    started_at = datetime.utcnow()

    try:
        # 1. Extract raw_trades for target_date (trade_ts in that day)
        ts_start = int(datetime.combine(target_date, datetime.min.time()).timestamp() * 1000)
        ts_end = int(datetime.combine(target_date, datetime.max.time()).timestamp() * 1000) + 86400_000

        cur.execute(
            """
            SELECT symbol, price, volume, trade_ts
            FROM raw_trades
            WHERE trade_ts >= %s AND trade_ts < %s
            ORDER BY symbol, trade_ts
            """,
            (ts_start, ts_end),
        )
        rows = cur.fetchall()
    except Exception as e:
        _log_job(cur, "extract_raw_trades", started_at, "failed", 0, str(e))
        conn.commit()
        raise

    if not rows:
        _log_job(cur, "extract_raw_trades", started_at, "success", 0, "No data")
        conn.commit()
        return

    # 2. Compute OHLCV per (symbol, date)
    from collections import defaultdict
    agg = defaultdict(lambda: {"prices": [], "volumes": [], "ts": []})
    for symbol, price, volume, trade_ts in rows:
        key = (symbol, target_date)
        agg[key]["prices"].append(float(price))
        agg[key]["volumes"].append(int(volume))
        agg[key]["ts"].append(trade_ts)

    ohlcv_rows = []
    for (symbol, date), v in agg.items():
        prices = v["prices"]
        volumes = v["volumes"]
        if not prices:
            continue
        open_p = prices[0]
        close_p = prices[-1]
        high_p = max(prices)
        low_p = min(prices)
        vol_sum = sum(volumes)
        ohlcv_rows.append((symbol, date, open_p, high_p, low_p, close_p, vol_sum))

    # 3. Write ohlcv_daily (upsert)
    execute_values(
        cur,
        """
        INSERT INTO ohlcv_daily (symbol, date, open, high, low, close, volume)
        VALUES %s
        ON CONFLICT (symbol, date) DO UPDATE SET
          open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
          close = EXCLUDED.close, volume = EXCLUDED.volume
        """,
        ohlcv_rows,
    )

    # 4. Compute daily returns and top_movers / most_volatile
    prev_date = target_date - timedelta(days=1)
    cur.execute(
        """
        SELECT symbol, date, open, high, low, close, volume
        FROM ohlcv_daily
        WHERE date IN (%s, %s)
        ORDER BY symbol, date
        """,
        (target_date, prev_date),
    )
    ohlcv = cur.fetchall()
    prev_close = {}
    for symbol, date, o, h, l, c, vol in ohlcv:
        if date == prev_date:
            prev_close[symbol] = c
    current = {}
    volatility_sum = {}
    volatility_count = {}
    for symbol, date, o, h, l, c, vol in ohlcv:
        if date == target_date:
            current[symbol] = {"close": c, "high": h, "low": l, "vol": vol}
            daily_vol = (h - l) / o if o else 0
            volatility_sum[symbol] = volatility_sum.get(symbol, 0) + daily_vol
            volatility_count[symbol] = volatility_count.get(symbol, 0) + 1

    generated_at = datetime.utcnow()
    movers = []
    for symbol, data in current.items():
        prev = prev_close.get(symbol)
        if prev and prev != 0:
            pct = (data["close"] - prev) / prev * 100
        else:
            pct = 0.0
        avg_vol = volatility_sum.get(symbol, 0) / max(volatility_count.get(symbol, 1), 1)
        movers.append((symbol, pct, data["close"], data["vol"], avg_vol))

    movers.sort(key=lambda x: x[1], reverse=True)
    gainers = [(generated_at, m[0], m[1], i + 1, None, m[3], m[2]) for i, m in enumerate(movers[:5])]
    losers = [(generated_at, m[0], m[1], None, i + 1, m[3], m[2]) for i, m in enumerate(movers[-5:][::-1])]

    cur.execute("DELETE FROM top_movers WHERE generated_at >= %s - interval '1 day'", (generated_at,))
    if gainers:
        execute_values(
            cur,
            """INSERT INTO top_movers (generated_at, symbol, pct_change, rank_gainers, rank_losers, volume, close)
               VALUES %s""",
            gainers,
            template="(%s, %s, %s, %s, %s, %s, %s)",
        )
    if losers:
        execute_values(
            cur,
            """INSERT INTO top_movers (generated_at, symbol, pct_change, rank_gainers, rank_losers, volume, close)
               VALUES %s""",
            losers,
            template="(%s, %s, %s, %s, %s, %s, %s)",
        )

    # most_volatile: top 5 by avg daily volatility
    vol_list = [(s, volatility_sum.get(s, 0) / max(volatility_count.get(s, 1), 1), v["vol"]) for s, v in current.items()]
    vol_list.sort(key=lambda x: x[1], reverse=True)
    volatile_rows = [(generated_at, x[0], x[1], i + 1, x[2]) for i, x in enumerate(vol_list[:5])]
    cur.execute("DELETE FROM most_volatile WHERE generated_at >= %s - interval '1 day'", (generated_at,))
    execute_values(
        cur,
        """INSERT INTO most_volatile (generated_at, symbol, avg_volatility, rank, volume) VALUES %s""",
        volatile_rows,
    )

    _log_job(cur, "batch_job", started_at, "success", len(rows), None)
    conn.commit()
    cur.close()
    conn.close()
    print("Batch job completed.", len(ohlcv_rows), "OHLCV rows,", len(movers), "movers.")


def _log_job(cur, job_name, started_at, status, rows_processed, message):
    cur.execute(
        """INSERT INTO job_logs (job_name, started_at, finished_at, status, rows_processed, message)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (job_name, started_at, datetime.utcnow(), status, rows_processed, message),
    )


if __name__ == "__main__":
    run()
    sys.exit(0)
