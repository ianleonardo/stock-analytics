from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MetricsResponse(BaseModel):
    price: float
    vwap_1m: float
    vwap_5m: Optional[float] = None
    vwap_15m: Optional[float] = None
    ema9: float
    ema21: float
    vol: float
    ts: str

class OHLCVPoint(BaseModel):
    open: float
    high: float
    low: float
    close: float
    volume: int
    date: str

class TopMoversResponse(BaseModel):
    gainers: list[dict]
    losers: list[dict]
    generated_at: Optional[str] = None

class AlertResponse(BaseModel):
    ticker: str
    type: str
    severity: str
    value: Optional[float] = None
    ts: str
