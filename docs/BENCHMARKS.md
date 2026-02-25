# Performance benchmarks

Capture these during final testing for the capstone demo.

## Metrics to measure

| Metric | How to measure | Target (from plan) |
|--------|----------------|--------------------|
| End-to-end latency | Timestamp in Finnhub message vs timestamp of Redis write (or dashboard update) | < 2 s |
| Kafka throughput | Consumer group lag via `kafka-consumer-groups.sh`; or count messages/sec on trades-raw | ≥ 500 msg/s |
| Spark processing time | Spark UI → Streaming tab → batch duration per micro-batch | — |
| Redis read latency | `redis-cli --latency` or time GET in API | < 5 ms |
| API response time (Redis-backed) | `time curl -s http://localhost:8000/api/metrics/AAPL` or httpx in test | < 50 ms |
| WebSocket message rate | Count messages received in browser DevTools → Network → WS | — |

## Example commands

```bash
# Kafka consumer lag (run while producer is active)
docker compose exec kafka kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group spark-streaming

# Redis latency
docker compose exec redis redis-cli --latency

# API latency (repeat several times)
curl -w "%{time_total}\n" -o /dev/null -s http://localhost:8000/api/metrics/AAPL
```

## Logging benchmarks

- In the streaming job, log batch size and duration in `_write_metrics_batch`.
- In the API, add optional timing middleware or log request duration for `/api/metrics/*`.
