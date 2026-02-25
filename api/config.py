from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    database_url_async: str = "postgresql+asyncpg://stock:stock@localhost:5432/stock_analytics"
    kafka_bootstrap_servers: str = "localhost:9092"
    tickers: str = "AAPL,TSLA,MSFT,AMZN,BTC-USD"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def ticker_list(self) -> list[str]:
        return [s.strip() for s in self.tickers.split(",") if s.strip()]

settings = Settings()
