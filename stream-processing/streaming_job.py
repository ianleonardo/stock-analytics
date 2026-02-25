"""
Spark Structured Streaming: consume trades-raw, compute VWAP (1m/5m/15m),
EMA-9/EMA-21 (stateful), rolling 10-min volatility, volume anomaly.
Write metrics to Redis (HSET + Pub/Sub) and alerts to PostgreSQL + trades-alerts.
"""
import os
import json
import logging
from typing import Iterator
from datetime import datetime

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, LongType,
)
from pyspark.sql.functions import col, from_json, from_unixtime, window, sum as spark_sum, stddev, mean
from pyspark.sql.streaming.state import GroupState, GroupStateTimeout

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_PORT = int(os.environ.get("PG_PORT", "5432"))
PG_DB = os.environ.get("PG_DATABASE", "stock_analytics")
PG_USER = os.environ.get("PG_USER", "stock")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "stock")
REDIS_TTL = 120
ANOMALY_VOLUME_MULTIPLIER = 2.0

TRADES_RAW_TOPIC = "trades-raw"
TRADES_ALERTS_TOPIC = "trades-alerts"


def main():
    spark = (
        SparkSession.builder.appName("stock-streaming")
        .config("spark.sql.streaming.metricsEnabled", "true")
        .config("spark.sql.shuffle.partitions", "5")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    schema = StructType([
        StructField("symbol", StringType(), False),
        StructField("price", DoubleType(), False),
        StructField("volume", LongType(), False),
        StructField("timestamp", LongType(), False),
        StructField("conditions", StringType(), True),
    ])

    df = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", TRADES_RAW_TOPIC)
        .option("startingOffsets", "latest")
        .load()
    )

    trades = (
        df.select(from_json(col("value").cast("string"), schema).alias("data"))
        .select("data.*")
        .withColumn(
            "event_time",
            from_unixtime(col("timestamp") / 1000.0).cast("timestamp"),
        )
        .withWatermark("event_time", "30 seconds")
    )

    # Stateful metrics: one row per symbol with VWAP, EMA, volatility
    metrics_stream = trades.groupBy("symbol").applyInPandasWithState(
        _metrics_stateful,
        _metrics_output_schema(),
        _metrics_state_schema(),
        "Update",
        GroupStateTimeout.NoTimeout,
    )

    # Alerts: compute in foreachBatch from raw trades
    def write_metrics(batch_df, batch_id):
        if batch_df.isEmpty():
            return
        _write_metrics_batch(batch_df, batch_id)

    def write_alerts_from_trades(batch_df, batch_id):
        if batch_df.isEmpty():
            return
        _compute_and_write_alerts(batch_df, batch_id)

    def write_raw_trades_batch(batch_df, batch_id):
        if batch_df.isEmpty():
            return
        _write_raw_trades_batch(batch_df)

    query_metrics = (
        metrics_stream.writeStream
        .foreachBatch(write_metrics)
        .outputMode("update")
        .trigger(processingTime="5 seconds")
        .start()
    )

    query_alerts = (
        trades.writeStream
        .foreachBatch(write_alerts_from_trades)
        .outputMode("append")
        .trigger(processingTime="5 seconds")
        .start()
    )

    query_raw = (
        trades.writeStream
        .foreachBatch(write_raw_trades_batch)
        .outputMode("append")
        .trigger(processingTime="5 seconds")
        .start()
    )

    spark.streams.awaitAnyTermination()


def _metrics_state_schema():
    return StructType([
        StructField("ema9", DoubleType()),
        StructField("ema21", DoubleType()),
    ])


def _metrics_output_schema():
    return StructType([
        StructField("symbol", StringType()),
        StructField("price", DoubleType()),
        StructField("ts", LongType()),
        StructField("vwap_1m", DoubleType()),
        StructField("vwap_5m", DoubleType()),
        StructField("vwap_15m", DoubleType()),
        StructField("ema9", DoubleType()),
        StructField("ema21", DoubleType()),
        StructField("vol", DoubleType()),
    ])


def _metrics_stateful(
    key: tuple,
    values: Iterator,
    state: GroupState,
) -> Iterator:
    import pandas as pd
    import numpy as np

    symbol = str(key[0])
    dfs = list(values)
    if not dfs:
        return
    pdf = pd.concat(dfs, ignore_index=True)
    pdf = pdf.sort_values("timestamp")
    prices = pdf["price"].values
    volumes = pdf["volume"].values
    timestamps = pdf["timestamp"].values
    if len(prices) == 0:
        return

    # State: EMA9, EMA21
    if state.exists:
        s = state.get
        ema9 = float(s[0])
        ema21 = float(s[1])
    else:
        ema9 = float(prices[0])
        ema21 = float(prices[0])

    k9 = 2.0 / (9 + 1)
    k21 = 2.0 / (21 + 1)
    for p in prices:
        ema9 = float(p) * k9 + ema9 * (1 - k9)
        ema21 = float(p) * k21 + ema21 * (1 - k21)
    state.update((ema9, ema21))

    # VWAP and volatility from last 1/5/15/10 minutes of data in batch
    one_min = 60 * 1000
    five_min = 5 * 60 * 1000
    fifteen_min = 15 * 60 * 1000
    ten_min = 10 * 60 * 1000
    mask_1m = timestamps >= (timestamps[-1] - one_min)
    mask_5m = timestamps >= (timestamps[-1] - five_min)
    mask_15m = timestamps >= (timestamps[-1] - fifteen_min)
    mask_10m = timestamps >= (timestamps[-1] - ten_min)

    def vwap(p, v):
        return float(np.average(p, weights=v)) if v.sum() > 0 else float(prices[-1])

    vwap_1m = vwap(prices[mask_1m], volumes[mask_1m])
    vwap_5m = vwap(prices[mask_5m], volumes[mask_5m])
    vwap_15m = vwap(prices[mask_15m], volumes[mask_15m])
    vol = float(np.std(prices[mask_10m])) if mask_10m.sum() > 1 else 0.0

    out = pd.DataFrame([{
        "symbol": symbol,
        "price": float(prices[-1]),
        "ts": int(timestamps[-1]),
        "vwap_1m": vwap_1m,
        "vwap_5m": vwap_5m,
        "vwap_15m": vwap_15m,
        "ema9": ema9,
        "ema21": ema21,
        "vol": vol,
    }])
    yield out


def _compute_and_write_alerts(batch_df, batch_id):
    """From a batch of trades, compute 1m volume and 10m avg per symbol; emit alerts if vol_1m > 2*avg_10m."""
    import pandas as pd

    rows = batch_df.collect()
    if not rows:
        return
    pdf = pd.DataFrame([r.asDict() for r in rows])
    pdf["event_time"] = pd.to_datetime(pdf["timestamp"], unit="ms")
    pdf = pdf.sort_values("event_time")

    # 1-minute windows: sum volume per symbol per 1m window
    pdf["window_1m"] = pdf["event_time"].dt.floor("1min")
    vol_1m = pdf.groupby(["symbol", "window_1m"])["volume"].sum().reset_index()
    vol_1m.columns = ["symbol", "window_1m", "vol_1m"]

    # 10-minute rolling avg volume per symbol (approximate: use 10m window)
    pdf["window_10m"] = pdf["event_time"].dt.floor("10min")
    vol_10m = pdf.groupby(["symbol", "window_10m"])["volume"].mean().reset_index()
    vol_10m.columns = ["symbol", "window_10m", "avg_vol_10m"]

    # Join: same symbol, 1m window within 10m window
    vol_1m["window_10m"] = vol_1m["window_1m"].dt.floor("10min")
    merged = vol_1m.merge(
        vol_10m,
        on=["symbol", "window_10m"],
        how="inner",
    )
    alerts_df = merged[merged["vol_1m"] > ANOMALY_VOLUME_MULTIPLIER * merged["avg_vol_10m"]]

    if alerts_df.empty:
        return

    # Write to PostgreSQL
    import psycopg2
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
    )
    cur = conn.cursor()
    for _, row in alerts_df.iterrows():
        ts_str = row["window_1m"].isoformat()
        value = float(row["vol_1m"] / row["avg_vol_10m"]) if row["avg_vol_10m"] else 0
        cur.execute(
            "INSERT INTO alerts (ticker, alert_type, severity, value, ts) VALUES (%s, %s, %s, %s, %s)",
            (row["symbol"], "volume_spike", "high", value, ts_str),
        )
    conn.commit()
    cur.close()
    conn.close()

    # Optionally produce to trades-alerts (Kafka)
    try:
        from kafka import KafkaProducer
        prod = KafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)
        for _, row in alerts_df.iterrows():
            msg = json.dumps({
                "ticker": row["symbol"],
                "type": "volume_spike",
                "severity": "high",
                "value": float(row["vol_1m"] / row["avg_vol_10m"]) if row["avg_vol_10m"] else 0,
                "ts": row["window_1m"].isoformat(),
            }).encode()
            prod.send(TRADES_ALERTS_TOPIC, key=row["symbol"].encode(), value=msg)
        prod.flush()
        prod.close()
    except Exception as e:
        logger.warning("Kafka alert produce failed: %s", e)

    logger.info("Wrote %d alerts batch %s", len(alerts_df), batch_id)


def _write_raw_trades_batch(batch_df):
    import psycopg2
    from psycopg2.extras import execute_batch
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
    )
    cur = conn.cursor()
    rows = batch_df.collect()
    for r in rows:
        cur.execute(
            "INSERT INTO raw_trades (symbol, price, volume, trade_ts) VALUES (%s, %s, %s, %s)",
            (r["symbol"], float(r["price"]), int(r["volume"]), int(r["timestamp"])),
        )
    conn.commit()
    cur.close()
    conn.close()


def _write_metrics_batch(batch_df, batch_id):
    import redis
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    for row in batch_df.collect():
        symbol = row["symbol"]
        key = f"trades:metrics:{symbol}"
        mapping = {
            "price": str(row["price"]),
            "ts": str(row["ts"]),
            "vwap_1m": str(row["vwap_1m"]),
            "vwap_5m": str(row["vwap_5m"]),
            "vwap_15m": str(row["vwap_15m"]),
            "ema9": str(row["ema9"]),
            "ema21": str(row["ema21"]),
            "vol": str(row["vol"]),
        }
        r.hset(key, mapping=mapping)
        r.expire(key, REDIS_TTL)
        r.publish(f"live:{symbol}", json.dumps(mapping))
    r.close()
    logger.info("Wrote metrics batch %s to Redis", batch_id)


if __name__ == "__main__":
    main()
