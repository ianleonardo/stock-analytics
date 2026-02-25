"""API tests: health and REST endpoints (require Redis/Postgres or mocks)."""
import pytest
from httpx import ASGITransport, AsyncClient
from main import app

pytestmark = pytest.mark.asyncio


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_health_returns_200(client):
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert "checks" in data


async def test_tickers_returns_list(client):
    r = await client.get("/api/tickers")
    assert r.status_code == 200
    data = r.json()
    assert "tickers" in data
    assert isinstance(data["tickers"], list)


async def test_metrics_404_when_no_data(client):
    r = await client.get("/api/metrics/NONEXISTENT_TICKER_XYZ")
    assert r.status_code == 404


async def test_historical_returns_array(client):
    r = await client.get("/api/historical/AAPL")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_top_movers_returns_shape(client):
    r = await client.get("/api/reports/top-movers")
    assert r.status_code == 200
    data = r.json()
    assert "gainers" in data
    assert "losers" in data
    assert "generated_at" in data


async def test_alerts_returns_array(client):
    r = await client.get("/api/alerts")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
