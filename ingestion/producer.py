"""
Finnhub WebSocket → Kafka producer.
Subscribes to tickers, deserializes trade JSON, publishes to trades-raw with key=symbol.
Exponential backoff for WebSocket and Kafka; never crash on Kafka unavailable.
"""
import json
import logging
import os
import time
from typing import Any

import websocket
from confluent_kafka import Producer
from confluent_kafka import KafkaException

from config import (
    FINNHUB_WS_URL,
    FINNHUB_API_KEY,
    KAFKA_BOOTSTRAP_SERVERS,
    TICKERS,
    TOPIC_RAW,
)
from topics import ensure_topics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Backoff: 1s → 2s → 4s → ... → max 30s
BACKOFF_INIT = 1.0
BACKOFF_MAX = 30.0
BACKOFF_MULT = 2.0


def make_producer() -> Producer:
    return Producer({
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "client.id": "finnhub-ingestion",
        "message.timeout.ms": 5000,
    })


def on_open(ws: websocket.WebSocketApp, producer: Producer):
    logger.info("WebSocket connected to Finnhub")
    for ticker in TICKERS:
        msg = json.dumps({"type": "subscribe", "symbol": ticker})
        ws.send(msg)
        logger.info("Subscribed to %s", ticker)


def on_message(ws: websocket.WebSocketApp, message: str, producer: Producer):
    try:
        data = json.loads(message)
    except json.JSONDecodeError as e:
        logger.warning("Invalid JSON: %s", e)
        return

    if data.get("type") == "ping":
        return
    if data.get("type") != "trade":
        return

    for trade in data.get("data", []):
        symbol = trade.get("s")
        if not symbol:
            continue
        # Normalize to doc shape: symbol, price, volume, timestamp, conditions
        payload = {
            "symbol": symbol,
            "price": trade.get("p"),
            "volume": trade.get("v", 0),
            "timestamp": trade.get("t"),
            "conditions": trade.get("c", []),
        }
        value = json.dumps(payload).encode("utf-8")
        key = symbol.encode("utf-8")
        try:
            producer.produce(
                TOPIC_RAW,
                key=key,
                value=value,
                callback=lambda err, msg: _delivery_callback(err, msg, symbol),
            )
            producer.poll(0)
        except (KafkaException, BufferError) as e:
            logger.warning("Kafka unavailable, skipping message for %s: %s", symbol, e)
            # Do not crash; skip message


def _delivery_callback(err, msg, symbol: str):
    if err:
        logger.warning("Delivery failed for %s: %s", symbol, err)


def on_error(ws: websocket.WebSocketApp, error: Exception):
    logger.error("WebSocket error: %s", error)


def on_close(ws: websocket.WebSocketApp, close_status_code: int, close_msg: str):
    logger.warning("WebSocket closed: code=%s reason=%s", close_status_code, close_msg)


def run_forever():
    if not FINNHUB_API_KEY or FINNHUB_API_KEY == "your_finnhub_api_key":
        logger.error("Set FINNHUB_API_KEY in environment")
        raise SystemExit(1)
    if not TICKERS:
        logger.error("Set TICKERS in environment (comma-separated)")
        raise SystemExit(1)

    ensure_topics()
    producer = make_producer()
    url = f"{FINNHUB_WS_URL}?token={FINNHUB_API_KEY}"
    backoff = BACKOFF_INIT

    while True:
        ws = websocket.WebSocketApp(
            url,
            on_open=lambda w: on_open(w, producer),
            on_message=lambda w, m: on_message(w, m, producer),
            on_error=on_error,
            on_close=on_close,
        )
        try:
            logger.info("Connecting to %s", FINNHUB_WS_URL)
            ws.run_forever()
        except Exception as e:
            logger.exception("WebSocket run_forever failed: %s", e)
        # Exponential backoff before reconnect
        logger.info("Reconnecting in %.1fs", backoff)
        time.sleep(backoff)
        backoff = min(backoff * BACKOFF_MULT, BACKOFF_MAX)


if __name__ == "__main__":
    run_forever()
