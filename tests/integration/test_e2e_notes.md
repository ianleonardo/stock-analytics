# Integration test notes

## End-to-end (synthetic trade → dashboard)

1. Start stack: `docker compose up -d` (kafka, redis, postgres, api, ingestion; optional spark + stream).
2. Ensure FINNHUB_API_KEY is set so ingestion publishes to `trades-raw`.
3. Run stream processor (or mock Redis writes) so `trades:metrics:{ticker}` and `live:{ticker}` get updates.
4. Open dashboard; select ticker; assert metric card updates within 5s (manual or Playwright).

## Kafka producer

- Start Kafka (e.g. `docker compose up -d zookeeper kafka`).
- Run producer with test key; consume from `trades-raw`: `kafka-console-consumer --bootstrap-server localhost:9092 --topic trades-raw --from-beginning`.
- Assert messages appear within 1s of a trade on Finnhub.

## Airflow DAG

- Trigger `stock_nightly_batch` manually in Airflow UI.
- Assert task `compute_ohlcv` succeeds and `ohlcv_daily` / `top_movers` have new rows.

## Redis key expiry

- Set a key `trades:metrics:TEST` with TTL 1s; wait 2s; GET /api/metrics/TEST → 404 or appropriate message.
