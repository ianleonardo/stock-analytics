"""Load config from environment."""
import os

def get_env(key: str, default: str | None = None) -> str:
    val = os.environ.get(key, default)
    if val is None or val == "":
        raise RuntimeError(f"Missing required env: {key}")
    return val

FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TICKERS_STR = os.environ.get("TICKERS", "AAPL,TSLA,MSFT,AMZN,BTC-USD")
TICKERS = [s.strip() for s in TICKERS_STR.split(",") if s.strip()]

TOPIC_RAW = "trades-raw"
TOPIC_METRICS = "trades-metrics"
TOPIC_ALERTS = "trades-alerts"
TOPICS = [TOPIC_RAW, TOPIC_METRICS, TOPIC_ALERTS]
NUM_PARTITIONS = 5
REPLICATION_FACTOR = 1

FINNHUB_WS_URL = "wss://ws.finnhub.io"
