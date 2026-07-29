You are building a production, publicly shareable web app called BacktestLab: a
stock-strategy BACKTESTING platform for Indian (NSE) markets.

A WORKING Python backtesting engine ALREADY EXISTS in trading_platform/ and MUST be reused
as the backend core. DO NOT rewrite the backtest math, cost model, or metrics. It exposes:
  - engine.run_backtest(df, strategy, capital_per_trade, costs) -> (trades_df, daily_equity)
  - indicators.py: ema, sma, rsi, atr, adx, supertrend, bollinger (all backward-looking)
  - strategies/: a Strategy base class + @register decorator + all_strategies() registry
                 + built-ins (EMA Crossover, SuperTrend, RSI Mean-Reversion, Bollinger Breakout)
  - metrics.compute(trades_df, equity, capital) -> dict of pro stats
  - regime.tag_bars(df) / regime.attach_to_trades(...) -> market-regime tagging
  - report.build_report(path, symbol, interval, df, results) -> writes a PDF
  - data.get_data(symbol, start, end, interval) -> OHLCV with a Parquet cache
    (yfinance for daily; fetch_raw() is meant to be swapped for a broker API for intraday)
The engine is LOOK-AHEAD SAFE (signal on bar t, fill at t+1 open) and models real Indian
costs (brokerage, STT, exchange txn, GST, SEBI, stamp) + slippage. Never fake or hide costs.

STACK: Monorepo /backend + /frontend. Backend = FastAPI (Python 3.12) + SQLModel + PostgreSQL
+ Alembic. Frontend = Next.js 14 (App Router, TypeScript) + Tailwind + shadcn/ui + TanStack
Query. Charts: candlesticks via lightweight-charts, stats via Recharts.

HARD PRINCIPLES:
  1. Reuse the existing engine; import it, do not duplicate its logic.
  2. This app is PUBLIC — NEVER execute untrusted user code. User-added strategies are
     declarative JSON specs interpreted by whitelisted indicators/operators only. No eval/exec.
  3. Every backtest must be reproducible from its stored parameters.
  4. Protect the public backtest endpoint with input caps + rate limiting.
WORKING STYLE: after each task, run the app, open it in your browser, and verify the
acceptance criteria with a screenshot before finishing.
