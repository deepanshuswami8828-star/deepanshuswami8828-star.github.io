import uuid
import secrets
from datetime import datetime
from typing import Optional, List, Dict
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON, UniqueConstraint

def generate_public_id() -> str:
    return secrets.token_urlsafe(6)

class Stock(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True, unique=True)
    name: str = Field(index=True)
    exchange: str = Field(default="NSE")
    series: str = Field(default="EQ")

class BacktestRun(SQLModel, table=True):
    __tablename__ = "backtests"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    public_id: str = Field(default_factory=generate_public_id, index=True, unique=True)
    symbol: str = Field(default="", index=True)
    start: str = Field(default="")
    end: str = Field(default="")
    interval: str = Field(default="")
    capital_per_trade: float = Field(default=100000.0)
    segment: str = Field(default="EQ")
    strategy_ids: List[str] = Field(default=[], sa_column=Column(JSON))
    params_json: Dict = Field(default={}, sa_column=Column(JSON))
    params_hash: str = Field(default="", index=True)
    summary_json: Dict = Field(default={}, sa_column=Column(JSON))
    result_json: Dict = Field(default={}, sa_column=Column(JSON))
    pdf_path: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

class UserStrategy(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True)
    spec_json: Dict = Field(default={}, sa_column=Column(JSON))
    created_by: str = Field(default="user")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_public: bool = Field(default=True)

class PriceBar(SQLModel, table=True):
    __tablename__ = "price_bars"

    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    interval: str = Field(default="1d", index=True)
    timestamp: datetime = Field(index=True)
    open: float
    high: float
    low: float
    close: float
    volume: float

    __table_args__ = (
        UniqueConstraint("symbol", "interval", "timestamp", name="uix_symbol_interval_timestamp"),
    )

class StockStatus(SQLModel, table=True):
    __tablename__ = "stock_status"

    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    interval: str = Field(default="1d", index=True)
    first_bar: Optional[str] = Field(default=None)
    last_bar: Optional[str] = Field(default=None)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    total_bars: int = Field(default=0)

