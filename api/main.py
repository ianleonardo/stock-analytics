import json
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from config import settings
from models import MetricsResponse, OHLCVPoint, TopMoversResponse, AlertResponse
from database import get_pool, fetch_historical, fetch_alerts, fetch_top_movers

redis_client: Redis | None = None
db_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, db_pool
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    db_pool = await get_pool()
    yield
    if redis_client:
        await redis_client.close()
    if db_pool:
        await db_pool.close()

app = FastAPI(title="Stock Analytics API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    checks = {}
    try:
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = str(e)
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = str(e)
    # Kafka check optional
    checks["kafka"] = "not_checked"
    return {"status": "ok" if all(v == "ok" for k, v in checks.items() if k != "kafka") else "degraded", "checks": checks}


@app.get("/api/tickers")
async def list_tickers():
    return {"tickers": settings.ticker_list}


@app.get("/api/metrics/{ticker}", response_model=MetricsResponse)
async def get_metrics(ticker: str):
    if not redis_client:
        raise HTTPException(500, "Redis not available")
    key = f"trades:metrics:{ticker.upper()}"
    data = await redis_client.hgetall(key)
    if not data:
        raise HTTPException(404, f"No metrics for ticker {ticker}")
    return MetricsResponse(
        price=float(data.get("price", 0)),
        vwap_1m=float(data.get("vwap_1m", 0)),
        vwap_5m=float(data.get("vwap_5m")) if data.get("vwap_5m") else None,
        vwap_15m=float(data.get("vwap_15m")) if data.get("vwap_15m") else None,
        ema9=float(data.get("ema9", 0)),
        ema21=float(data.get("ema21", 0)),
        vol=float(data.get("vol", 0)),
        ts=data.get("ts", "0"),
    )


@app.get("/api/historical/{ticker}")
async def get_historical(ticker: str, limit: int = 200):
    async with db_pool.acquire() as conn:
        rows = await fetch_historical(conn, ticker, limit)
    return rows


@app.get("/api/reports/top-movers", response_model=TopMoversResponse)
async def get_top_movers():
    async with db_pool.acquire() as conn:
        data = await fetch_top_movers(conn)
    return TopMoversResponse(**data)


@app.get("/api/alerts")
async def get_alerts(limit: int = 100):
    async with db_pool.acquire() as conn:
        rows = await fetch_alerts(conn, limit)
    return rows


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_text()
        msg = json.loads(data) if data else {}
        ticker = (msg.get("ticker") or msg.get("symbol") or "AAPL").upper()
    except Exception:
        ticker = "AAPL"
    if ticker not in settings.ticker_list:
        ticker = settings.ticker_list[0] if settings.ticker_list else "AAPL"
    pubsub = redis_client.pubsub()
    channel = f"live:{ticker}"
    await pubsub.subscribe(channel)
    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg and msg.get("type") == "message" and msg.get("data"):
                await websocket.send_text(msg["data"])
            await asyncio.sleep(0.01)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
