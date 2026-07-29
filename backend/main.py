import sys
import os
import datetime as dt
import uuid
import hashlib
import json
from typing import List, Optional
from pydantic import BaseModel, Field as PydanticField, field_validator
from fastapi import FastAPI, HTTPException, Depends, Query, status, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select, or_, func
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)


# 1. Inject engine directory to sys.path so inner imports work unchanged
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine"))

from database import engine, get_session, create_db_and_tables
from models import Stock, BacktestRun, UserStrategy, PriceBar, StockStatus
from seed import seed_stocks

# Engine module imports (which now work directly via path injection)
from strategies import all_strategies
from engine import run_backtest
from metrics import compute
from regime import tag_bars, attach_to_trades
from report import build_report
from data import get_data

app = FastAPI(
    title="BacktestLab Backend",
    description="FastAPI stock backtesting platform wrapping the trading_platform engine",
    version="1.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Configure CORS middleware dynamically via ALLOWED_ORIGINS or FRONTEND_ORIGIN env var
raw_origins = os.getenv("ALLOWED_ORIGINS") or os.getenv("FRONTEND_ORIGIN") or "*"
if raw_origins == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

if "*" not in allowed_origins:
    defaults = [
        "https://frontend-azure-delta-48.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000"
    ]
    for d in defaults:
        if d not in allowed_origins:
            allowed_origins.append(d)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "app": "BacktestLab Backend"}

# Initialize database tables, run migrations, and seed stocks on startup
@app.on_event("startup")
def on_startup():
    try:
        from alembic.config import Config
        from alembic import command
        alembic_ini_path = os.path.join(os.path.dirname(__file__), "alembic.ini")
        if os.path.exists(alembic_ini_path):
            alembic_cfg = Config(alembic_ini_path)
            command.upgrade(alembic_cfg, "head")
        else:
            create_db_and_tables()
    except Exception as e:
        print(f"Alembic migration on startup: {e}")
        create_db_and_tables()

    try:
        # Check if database has stocks already
        with Session(engine) as session:
            count = session.exec(select(Stock)).first()
            if not count:
                print("Database stocks table is empty. Seeding 2300+ NSE stocks...")
                seed_stocks()
            else:
                print("Stocks table already seeded.")
    except Exception as e:
        print(f"Error during startup seeding: {e}")

# Pydantic schemas for Strategy Specs (No-code builder)
class SourceSpec(BaseModel):
    type: str
    name: Optional[str] = None
    field: Optional[str] = None
    value: Optional[float] = None
    params: Optional[dict] = {}

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        allowed = {"indicator", "price", "const"}
        if v not in allowed:
            raise ValueError(f"type must be one of {allowed}")
        return v

    @field_validator("field")
    @classmethod
    def validate_field(cls, v):
        if v is not None and v.lower() not in {"open", "high", "low", "close"}:
            raise ValueError("field must be one of: open, high, low, close")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            allowed = {
                "ema", "sma", "rsi", "atr", "adx", "plus_di", "minus_di", 
                "supertrend_dir", "bb_upper", "bb_mid", "bb_lower"
            }
            if v.lower() not in allowed:
                raise ValueError(f"Indicator name must be one of {allowed}")
        return v

class ConditionSpec(BaseModel):
    left: SourceSpec
    op: str
    right: Optional[SourceSpec] = None

    @field_validator("op")
    @classmethod
    def validate_op(cls, v):
        allowed = {"crosses_above", "crosses_below", "greater_than", "less_than", "flips_up", "flips_down"}
        if v.lower() not in allowed:
            raise ValueError(f"Operator must be one of {allowed}")
        return v

class RiskSpec(BaseModel):
    sl_atr_mult: float = 2.0
    rr_ratio: float = 2.0
    allow_long: bool = True
    allow_short: bool = True
    atr_period: int = 14

class StrategySpecSchema(BaseModel):
    name: str
    entry_long: List[ConditionSpec] = []
    entry_short: List[ConditionSpec] = []
    exit: List[ConditionSpec] = []
    risk: RiskSpec

class AddStockRequest(BaseModel):
    symbol: str
    name: Optional[str] = None
    exchange: Optional[str] = "NSE"

# Pydantic schemas for requests/responses
class BacktestRequest(BaseModel):
    symbol: str
    start: str
    end: str
    interval: str
    capital_per_trade: float
    segment: str
    strategy_ids: List[str] = []

class LeaderboardEntry(BaseModel):
    name: str
    net_pnl: float
    return_pct: float
    trades: int
    win_rate: float
    profit_factor: float
    reward_risk: float
    max_drawdown_pct: float
    sharpe: float
    expectancy: float

class OHLCVBar(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float

class EquityPoint(BaseModel):
    time: str
    value: float

class RegimeEntry(BaseModel):
    trend_regime: str
    trades: int
    net_pnl: float
    win_rate: float

class StrategyDetail(BaseModel):
    metrics: dict
    equity: List[EquityPoint]
    regime: List[RegimeEntry]
    trades: List[List]

class BacktestResponse(BaseModel):
    id: str
    public_id: Optional[str] = ""
    symbol: str
    interval: str
    period: str
    bars: int
    leaderboard: List[LeaderboardEntry]
    ohlcv: List[OHLCVBar]
    per_strategy: dict[str, StrategyDetail]
    cached: Optional[bool] = False
    params_json: Optional[dict] = {}
    summary_json: Optional[dict] = {}

# Strategy registry mapping
def build_strategy_map():
    reg = all_strategies()
    mapping = {}
    for name in reg.keys():
        s_id = (
            name.lower()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("-", "_")
            .replace("(", "")
            .replace(")", "")
            .replace("+", "plus")
            .replace("%", "pct")
            .strip("_")
        )
        mapping[s_id] = name
        mapping[name] = name
    return mapping

# Pydantic schemas for Strategy Specs (No-code builder)
class SourceSpec(BaseModel):
    type: str
    name: Optional[str] = None
    field: Optional[str] = None
    value: Optional[float] = None
    params: Optional[dict] = {}

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        allowed = {"indicator", "price", "const"}
        if v not in allowed:
            raise ValueError(f"type must be one of {allowed}")
        return v

    @field_validator("field")
    @classmethod
    def validate_field(cls, v):
        if v is not None and v.lower() not in {"open", "high", "low", "close"}:
            raise ValueError("field must be one of: open, high, low, close")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            allowed = {
                "ema", "sma", "rsi", "atr", "adx", "plus_di", "minus_di", 
                "supertrend_dir", "bb_upper", "bb_mid", "bb_lower", "macd", "macd_signal", "macd_hist",
                "stoch_k", "stoch_d", "stoch_rsi_k", "stoch_rsi_d", "cci", "williams_r",
                "roc", "trix", "awesome_oscillator", "obv", "mfi", "cmf", "vol_sma",
                "rel_volume", "zscore", "donchian_upper", "donchian_mid", "donchian_lower",
                "keltner_upper", "keltner_mid", "keltner_lower", "linreg_slope", "psar",
                "vi_plus", "vi_minus", "bullish_engulfing", "bearish_engulfing", "hammer",
                "shooting_star", "doji", "inside_bar", "nr7"
            }
            if v.lower() not in allowed:
                raise ValueError(f"Indicator name must be one of {allowed}")
        return v

class ConditionSpec(BaseModel):
    left: SourceSpec
    op: str
    right: Optional[SourceSpec] = None

    @field_validator("op")
    @classmethod
    def validate_op(cls, v):
        allowed = {"crosses_above", "crosses_below", "greater_than", "less_than", "equals", "not_equals", "flips_up", "flips_down", "is_true", "is_false"}
        if v.lower() not in allowed:
            raise ValueError(f"Operator must be one of {allowed}")
        return v

@app.get("/strategies")
def get_strategies(db: Session = Depends(get_session)):
    strategies = all_strategies()
    s_map = build_strategy_map()
    result = []
    
    for name, cls in strategies.items():
        # Find friendly snake_case ID
        strat_id = next((k for k, v in s_map.items() if v == name and "_" in k), name.lower().replace(" ", "_"))
        result.append({
            "id": strat_id,
            "name": name,
            "category": getattr(cls, "category", "General"),
            "description": getattr(cls, "description", cls.__doc__ or "Built-in strategy"),
            "rules_text": getattr(cls, "rules_text", ""),
            "params": getattr(cls, "params", {}),
            "sl_atr_mult": getattr(cls, "sl_atr_mult", 2.0),
            "rr_ratio": getattr(cls, "rr_ratio", 2.0),
            "allow_long": getattr(cls, "allow_long", True),
            "allow_short": getattr(cls, "allow_short", True),
            "is_custom": False,
            "is_stub": getattr(cls, "is_stub", False)
        })
    
    # Load custom user strategies
    db_strats = db.exec(select(UserStrategy)).all()
    for s in db_strats:
        risk = s.spec_json.get("risk", {})
        result.append({
            "id": s.id,
            "name": s.name,
            "category": "Custom",
            "description": "User-defined custom strategy spec.",
            "rules_text": "Custom user-built rules.",
            "params": risk,
            "sl_atr_mult": float(risk.get("sl_atr_mult", 2.0)),
            "rr_ratio": float(risk.get("rr_ratio", 2.0)),
            "allow_long": bool(risk.get("allow_long", True)),
            "allow_short": bool(risk.get("allow_short", True)),
            "is_custom": True,
            "spec_json": s.spec_json
        })
    return result

@app.post("/strategies")
@limiter.limit("10/minute")
def create_strategy(request: Request, spec: StrategySpecSchema, db: Session = Depends(get_session)):
    db_strat = UserStrategy(name=spec.name, spec_json=spec.model_dump())
    db.add(db_strat)
    db.commit()
    db.refresh(db_strat)
    return {"id": db_strat.id, "name": db_strat.name, "spec_json": db_strat.spec_json}

@app.delete("/strategies/{id}")
def delete_strategy(id: str, db: Session = Depends(get_session)):
    db_strat = db.exec(select(UserStrategy).where(UserStrategy.id == id)).first()
    if not db_strat:
        raise HTTPException(status_code=404, detail="Strategy not found")
    db.delete(db_strat)
    db.commit()
    return {"status": "success", "message": f"Deleted strategy {id}"}

@app.post("/stocks")
def add_stock(req: AddStockRequest, db: Session = Depends(get_session)):
    symbol = req.symbol.strip().upper()
    exchange = (req.exchange or "NSE").strip().upper()
    name = (req.name or "").strip()
    
    existing = db.exec(select(Stock).where(Stock.symbol == symbol)).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Stock with symbol {symbol} already exists.")
        
    # Validation fetch
    import datetime as dt
    end_dt = dt.date.today()
    start_dt = end_dt - dt.timedelta(days=10)
    
    try:
        test_df = get_data(symbol, start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"), "1d")
        if test_df.empty:
            raise ValueError("Fetched dataset is empty. Symbol might be invalid or has no data.")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation failed for symbol {symbol}: {str(e)}"
        )
    
    if not name:
        import yfinance as yf
        try:
            ticker = yf.Ticker(symbol if symbol.endswith(".NS") else f"{symbol}.NS")
            name = ticker.info.get("longName", f"{symbol} Limited")
        except Exception:
            name = f"{symbol} Limited"
            
    new_stock = Stock(symbol=symbol, name=name, exchange=exchange, series="EQ")
    db.add(new_stock)
    db.commit()
    db.refresh(new_stock)
    
    return {
        "status": "success", 
        "stock": {"symbol": new_stock.symbol, "name": new_stock.name, "exchange": new_stock.exchange}
    }


@app.get("/stocks")
def search_stocks(
    query: str = Query("", description="Search by symbol or name"),
    limit: int = Query(20, ge=1, le=100)
):
    with Session(engine) as session:
        if not query:
            stocks = session.exec(select(Stock).limit(limit)).all()
        else:
            search_str = f"%{query}%"
            stocks = session.exec(
                select(Stock)
                .where(or_(Stock.symbol.ilike(search_str), Stock.name.ilike(search_str)))
                .limit(limit)
            ).all()
        
        return [
            {"symbol": s.symbol, "name": s.name, "exchange": s.exchange, "series": s.series}
            for s in stocks
        ]

@app.get("/ohlcv")
def get_ohlcv(
    symbol: str = Query(..., description="Stock symbol (e.g. RELIANCE)"),
    start: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end: str = Query(..., description="End date (YYYY-MM-DD)"),
    interval: str = Query("1d", description="Timeframe interval (1d, 1h, 15m, 5m)")
):
    sym = symbol.strip().upper()
    try:
        # If start and end dates are identical, adjust end date +1 day for yfinance non-inclusive bounds
        if start == end:
            try:
                dt_start = datetime.strptime(start, "%Y-%m-%d")
                end = (dt_start + timedelta(days=1)).strftime("%Y-%m-%d")
            except Exception:
                pass

        df = get_data(sym, start, end, interval)
        if df is None or df.empty:
            return []
        
        ohlcv_bars = []
        for idx, row in df.iterrows():
            t_str = idx.strftime("%Y-%m-%d %H:%M") if (hasattr(idx, "hour") and (idx.hour or idx.minute)) else idx.strftime("%Y-%m-%d")
            ohlcv_bars.append({
                "time": t_str,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"])
            })
        return ohlcv_bars
    except Exception as e:
        print(f"Notice: No OHLCV data for {sym} ({start} to {end}): {e}")
        # Return empty array gracefully instead of 422 error
        return []

@app.get("/stocks/{symbol}/status")
def get_stock_status(symbol: str, interval: str = Query("1d"), db: Session = Depends(get_session)):
    sym = symbol.strip().upper()
    status_rec = db.exec(
        select(StockStatus).where(StockStatus.symbol == sym, StockStatus.interval == interval)
    ).first()

    if not status_rec:
        # Query PriceBar directly if StockStatus row missing
        min_max = db.exec(
            select(func.min(PriceBar.timestamp), func.max(PriceBar.timestamp), func.count(PriceBar.id))
            .where(PriceBar.symbol == sym, PriceBar.interval == interval)
        ).one()
        min_ts, max_ts, total_bars = min_max

        if total_bars == 0:
            return {
                "symbol": sym,
                "interval": interval,
                "first_bar": None,
                "last_bar": None,
                "last_updated": None,
                "total_bars": 0,
                "cached": False
            }

        return {
            "symbol": sym,
            "interval": interval,
            "first_bar": min_ts.strftime("%Y-%m-%d") if min_ts else None,
            "last_bar": max_ts.strftime("%Y-%m-%d") if max_ts else None,
            "last_updated": max_ts.isoformat() if max_ts else None,
            "total_bars": total_bars,
            "cached": True
        }

    return {
        "symbol": status_rec.symbol,
        "interval": status_rec.interval,
        "first_bar": status_rec.first_bar,
        "last_bar": status_rec.last_bar,
        "last_updated": status_rec.last_updated.isoformat() if status_rec.last_updated else None,
        "total_bars": status_rec.total_bars,
        "cached": status_rec.total_bars > 0
    }

@app.post("/stocks/seed")
def trigger_seed_stocks():
    try:
        seed_stocks()
        with Session(engine) as session:
            total_stocks = session.exec(select(func.count(Stock.id))).one()
        return {"status": "success", "message": f"Seeded {total_stocks} NSE stocks successfully.", "total_stocks": total_stocks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to seed stocks: {str(e)}")

@app.post("/stocks/daily-update")
def trigger_daily_update():
    try:
        from daily_update import run_daily_update
        summary = run_daily_update()
        return {"status": "success", "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed daily update: {str(e)}")

@app.post("/stocks/prewarm")
def trigger_prewarm(years: int = Query(3, ge=1, le=10)):
    try:
        from prewarm import prewarm_top_n
        results = prewarm_top_n(years=years)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed prewarm: {str(e)}")

def compute_params_hash(symbol: str, start: str, end: str, interval: str, capital: float, segment: str, strategy_ids: List[str]) -> str:
    canonical = {
        "symbol": symbol.strip().upper(),
        "start": start.strip(),
        "end": end.strip(),
        "interval": interval.strip().lower(),
        "capital": float(capital),
        "segment": segment.strip().upper(),
        "strategy_ids": sorted([str(s) for s in strategy_ids])
    }
    dumped = json.dumps(canonical, sort_keys=True)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()

@app.post("/backtest", response_model=BacktestResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
def run_backtest_endpoint(request: Request, req: BacktestRequest, db: Session = Depends(get_session)):
    symbol = req.symbol.strip().upper()
    start_str = req.start
    end_str = req.end
    interval = req.interval
    capital = req.capital_per_trade
    segment = req.segment
    selected_ids = req.strategy_ids

    # 0. Check cache for identical parameters
    p_hash = compute_params_hash(symbol, start_str, end_str, interval, capital, segment, selected_ids)
    cached_run = db.exec(
        select(BacktestRun)
        .where(BacktestRun.params_hash == p_hash)
        .order_by(BacktestRun.created_at.desc())
    ).first()

    if cached_run and cached_run.result_json:
        res = dict(cached_run.result_json)
        res["id"] = cached_run.id
        res["public_id"] = cached_run.public_id
        res["cached"] = True
        return res

    # 1. Fetch data first to evaluate the length of the data series (guardrails)
    try:
        df = get_data(symbol, start_str, end_str, interval)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to fetch stock data for {symbol}: {str(e)}"
        )

    num_bars = len(df)
    
    # Map selected IDs to actual strategy names in registry
    registered_strategies = all_strategies()
    strategies_to_run = {}
    custom_strategies = []
    
    s_map = build_strategy_map()
    if not selected_ids:
        # Run all registered strategies
        strategies_to_run = registered_strategies
    else:
        for strat_id in selected_ids:
            strat_name = s_map.get(strat_id)
            if strat_name and strat_name in registered_strategies:
                strategies_to_run[strat_name] = registered_strategies[strat_name]
            else:
                # Try loading from DB
                db_strat = db.exec(select(UserStrategy).where(UserStrategy.id == strat_id)).first()
                if db_strat:
                    from strategies.spec_strategy import SpecStrategy
                    custom_strategies.append(SpecStrategy(db_strat.spec_json))
                else:
                    # Fallback to direct name matching
                    matching_name = next((name for name in registered_strategies if name.lower().replace(" ", "_") == strat_id), None)
                    if matching_name:
                        strategies_to_run[matching_name] = registered_strategies[matching_name]
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Invalid strategy ID: {strat_id}"
                        )

    num_strategies = len(strategies_to_run) + len(custom_strategies)
    total_compute_load = num_bars * num_strategies

    # 2. Enforce guardrails (max 5000 bars x 10 strategies)
    if num_bars > 5000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Backtest range too large: dataset has {num_bars} bars, maximum allowed is 5000 bars."
        )
    if num_strategies > 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Too many strategies: requested {num_strategies}, maximum allowed is 10."
        )
    if total_compute_load > 50000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Total backtest workload too high ({total_compute_load} compute load). Please reduce range or number of strategies."
        )

    # 3. Tag regimes once on the dataset
    regimes = tag_bars(df)

    # 4. Execute strategies and build results
    results_raw = {}
    leaderboard = []
    per_strategy_details = {}

    # Combine built-in and custom instances
    all_run_instances = []
    for name, StratClass in strategies_to_run.items():
        all_run_instances.append((name, StratClass()))
    for inst in custom_strategies:
        all_run_instances.append((inst.name, inst))

    for name, strategy_instance in all_run_instances:
        try:
            # Run backtest math
            trades_df, equity = run_backtest(df, strategy_instance, capital, {"segment": segment})
            trades_df = attach_to_trades(trades_df, regimes)
            
            # Compute stats
            m = compute(trades_df, equity, capital)
            results_raw[name] = {"trades": trades_df, "equity": equity, "metrics": m}
            
            # Add to leaderboard list
            leaderboard.append({
                "name": name,
                "net_pnl": float(m.get("net_pnl", 0.0)),
                "return_pct": float(m.get("return_pct", 0.0)),
                "trades": int(m.get("trades", 0)),
                "win_rate": float(m.get("win_rate", 0.0)),
                "profit_factor": float(m.get("profit_factor", 0.0)),
                "reward_risk": float(m.get("reward_risk", 0.0)),
                "max_drawdown_pct": float(m.get("max_drawdown_pct", 0.0)),
                "sharpe": float(m.get("sharpe", 0.0)),
                "expectancy": float(m.get("expectancy", 0.0))
            })

            # Format equity curve
            equity_points = []
            if not equity.empty:
                for t, val in equity.items():
                    t_str = t.strftime("%Y-%m-%d %H:%M") if (t.hour or t.minute) else t.strftime("%Y-%m-%d")
                    equity_points.append({"time": t_str, "value": float(val)})

            # Format regime breakdown
            from regime import by_regime
            br = by_regime(trades_df)
            regime_entries = []
            if not br.empty:
                for _, r_row in br.iterrows():
                    regime_entries.append({
                        "trend_regime": str(r_row["trend_regime"]),
                        "trades": int(r_row["trades"]),
                        "net_pnl": float(r_row["net_pnl"]),
                        "win_rate": float(r_row["win_rate"])
                    })

            # Format trade logs list
            trade_list = []
            if not trades_df.empty:
                for _, t_row in trades_df.iterrows():
                    entry_time_str = t_row["entry_time"].strftime("%Y-%m-%d %H:%M") if (t_row["entry_time"].hour or t_row["entry_time"].minute) else t_row["entry_time"].strftime("%Y-%m-%d")
                    exit_time_str = t_row["exit_time"].strftime("%Y-%m-%d %H:%M") if (t_row["exit_time"].hour or t_row["exit_time"].minute) else t_row["exit_time"].strftime("%Y-%m-%d")
                    
                    trade_list.append([
                        entry_time_str,
                        exit_time_str,
                        str(t_row["direction"]),
                        float(t_row["entry"]),
                        float(t_row["exit"]),
                        int(t_row["qty"]),
                        float(t_row["sl"]),
                        float(t_row["target"]),
                        float(t_row["net_pnl"]),
                        float(t_row["return_pct"]),
                        str(t_row.get("trend_regime", "-")),
                        str(t_row.get("entry_reason", "")),
                        str(t_row.get("exit_reason", ""))
                    ])

            per_strategy_details[name] = {
                "metrics": m,
                "equity": equity_points,
                "regime": regime_entries,
                "trades": trade_list
            }

        except Exception as e:
            print(f"Error executing strategy {name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error executing strategy {name}: {str(e)}"
            )

    # Sort leaderboard by net_pnl descending
    leaderboard = sorted(leaderboard, key=lambda x: x["net_pnl"], reverse=True)

    # 5. Format ohlcv
    ohlcv_points = []
    for idx, row in df.iterrows():
        t_str = idx.strftime("%Y-%m-%d %H:%M") if (idx.hour or idx.minute) else idx.strftime("%Y-%m-%d")
        ohlcv_points.append({
            "time": t_str,
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"])
        })

    # 6. Generate unique ID, public_id, and PDF report path
    run_id = str(uuid.uuid4())
    from models import generate_public_id
    pub_id = generate_public_id()

    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    pdf_path = os.path.join(reports_dir, f"report_{run_id}.pdf")
    
    # Build the report PDF
    try:
        build_report(pdf_path, symbol, interval, df, results_raw)
    except Exception as e:
        print(f"Failed to generate PDF report: {e}")
        pdf_path = ""

    params_json = {
        "symbol": symbol,
        "start": start_str,
        "end": end_str,
        "interval": interval,
        "capital": capital,
        "segment": segment,
        "strategy_ids": selected_ids
    }

    winner_name = leaderboard[0]["name"] if leaderboard else "-"
    winner_pnl = leaderboard[0]["net_pnl"] if leaderboard else 0.0
    winner_ret = leaderboard[0]["return_pct"] if leaderboard else 0.0

    summary_json = {
        "winner": winner_name,
        "net_pnl": winner_pnl,
        "return_pct": winner_ret,
        "period": f"{df.index.min().date()} to {df.index.max().date()}",
        "bars": num_bars,
        "leaderboard": leaderboard
    }

    # 7. Persist run params and results to DB
    response_data = {
        "id": run_id,
        "public_id": pub_id,
        "symbol": symbol,
        "interval": interval,
        "period": f"{df.index.min().date()} to {df.index.max().date()}",
        "bars": num_bars,
        "leaderboard": leaderboard,
        "ohlcv": ohlcv_points,
        "per_strategy": per_strategy_details,
        "cached": False,
        "params_json": params_json,
        "summary_json": summary_json
    }

    db_run = BacktestRun(
        id=run_id,
        public_id=pub_id,
        symbol=symbol,
        start=start_str,
        end=end_str,
        interval=interval,
        capital_per_trade=capital,
        segment=segment,
        strategy_ids=selected_ids,
        params_json=params_json,
        params_hash=p_hash,
        summary_json=summary_json,
        result_json=response_data,
        pdf_path=pdf_path
    )
    
    try:
        db.add(db_run)
        db.commit()
    except Exception as e:
        print(f"Database insertion failed: {e}")

    return response_data

@app.get("/backtests")
def get_backtest_history(
    symbol: Optional[str] = Query(None),
    interval: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_session)
):
    query = select(BacktestRun)
    if symbol and symbol.strip():
        query = query.where(BacktestRun.symbol.ilike(f"%{symbol.strip()}%"))
    if interval and interval.strip():
        query = query.where(BacktestRun.interval == interval.strip())
    if from_date and from_date.strip():
        query = query.where(or_(BacktestRun.start >= from_date.strip(), BacktestRun.created_at >= from_date.strip()))
    if to_date and to_date.strip():
        query = query.where(or_(BacktestRun.end <= to_date.strip(), BacktestRun.created_at <= to_date.strip()))

    total = db.exec(select(func.count()).select_from(query.subquery())).one()
    
    offset = (page - 1) * limit
    runs = db.exec(query.order_by(BacktestRun.created_at.desc()).offset(offset).limit(limit)).all()

    items = []
    for r in runs:
        summary = r.summary_json or {}
        leaderboard = summary.get("leaderboard", [])
        winner = summary.get("winner") or (leaderboard[0]["name"] if leaderboard else "-")
        net_pnl = summary.get("net_pnl") if "net_pnl" in summary else (leaderboard[0]["net_pnl"] if leaderboard else 0.0)
        return_pct = summary.get("return_pct") if "return_pct" in summary else (leaderboard[0]["return_pct"] if leaderboard else 0.0)

        items.append({
            "id": r.id,
            "public_id": r.public_id,
            "symbol": r.symbol,
            "interval": r.interval,
            "start": r.start,
            "end": r.end,
            "period": summary.get("period") or f"{r.start} to {r.end}",
            "capital": r.capital_per_trade,
            "segment": r.segment,
            "strategy_ids": r.strategy_ids,
            "winner": winner,
            "net_pnl": net_pnl,
            "return_pct": return_pct,
            "created_at": r.created_at.isoformat() if r.created_at else "",
            "summary_json": summary,
            "params_json": r.params_json
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if limit > 0 else 1
    }

@app.get("/r/{public_id}")
def get_shared_backtest(public_id: str, db: Session = Depends(get_session)):
    run = db.exec(select(BacktestRun).where(BacktestRun.public_id == public_id)).first()
    if not run:
        run = db.exec(select(BacktestRun).where(BacktestRun.id == public_id)).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest with share ID '{public_id}' not found."
        )
    return run.result_json

@app.get("/backtest/{run_id}/pdf")
def download_pdf(run_id: str, db: Session = Depends(get_session)):
    db_run = db.exec(select(BacktestRun).where(BacktestRun.id == run_id)).first()
    if not db_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF report not found for the given backtest run ID."
        )
    
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    pdf_path = db_run.pdf_path or os.path.join(reports_dir, f"report_{run_id}.pdf")

    if not os.path.exists(pdf_path):
        try:
            res_data = db_run.result_json or {}
            ohlcv_list = res_data.get("ohlcv", [])
            df_data = []
            for b in ohlcv_list:
                df_data.append({
                    "open": float(b.get("open", 0)),
                    "high": float(b.get("high", 0)),
                    "low": float(b.get("low", 0)),
                    "close": float(b.get("close", 0)),
                    "volume": float(b.get("volume", 0)),
                })
            idx = pd.to_datetime([b["time"] for b in ohlcv_list]) if ohlcv_list else pd.DatetimeIndex([])
            df = pd.DataFrame(df_data, index=idx)

            results_raw = {}
            for strat_name, details in res_data.get("per_strategy", {}).items():
                eq_pts = details.get("equity", [])
                eq_series = pd.Series(
                    [p["value"] for p in eq_pts],
                    index=pd.to_datetime([p["time"] for p in eq_pts])
                ) if eq_pts else pd.Series(dtype=float)
                
                raw_trades = details.get("trades", [])
                cols = ["entry_time", "exit_time", "type", "entry_price", "exit_price", "size", "stop_loss", "target", "net_pnl", "return_pct", "trend_regime", "entry_reason", "exit_reason"]
                trades_df = pd.DataFrame(raw_trades, columns=cols) if raw_trades else pd.DataFrame(columns=cols)
                if not trades_df.empty:
                    trades_df["entry_time"] = pd.to_datetime(trades_df["entry_time"])
                    trades_df["exit_time"] = pd.to_datetime(trades_df["exit_time"])

                results_raw[strat_name] = {
                    "trades": trades_df,
                    "equity": eq_series,
                    "metrics": details.get("metrics", {})
                }

            build_report(pdf_path, db_run.symbol, db_run.interval, df, results_raw)
            db_run.pdf_path = pdf_path
            db.add(db_run)
            db.commit()
        except Exception as e:
            print(f"Dynamic PDF build error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate PDF report: {e}"
            )

    filename = f"BacktestLab_Report_{db_run.symbol}_{db_run.interval}.pdf"
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=filename
    )
