"""Ingestion config and topic tests."""
import os
import pytest

# Set env before importing config
os.environ.setdefault("FINNHUB_API_KEY", "test_key")
os.environ.setdefault("TICKERS", "AAPL,MSFT")

from config import TICKERS, TOPIC_RAW, TOPICS, NUM_PARTITIONS


def test_tickers_parsed():
    assert "AAPL" in TICKERS
    assert "MSFT" in TICKERS


def test_topics_defined():
    assert TOPIC_RAW == "trades-raw"
    assert "trades-raw" in TOPICS
    assert "trades-metrics" in TOPICS
    assert "trades-alerts" in TOPICS


def test_partitions():
    assert NUM_PARTITIONS == 5
