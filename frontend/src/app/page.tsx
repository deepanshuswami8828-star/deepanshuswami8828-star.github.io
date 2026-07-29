"use client";

import React, { useState, useCallback, useEffect } from "react";
import BacktestForm from "../components/BacktestForm";
import Leaderboard from "../components/Leaderboard";
import PriceChart from "../components/PriceChart";
import EquityChart from "../components/EquityChart";
import TradeLog from "../components/TradeLog";
import RegimeBreakdown from "../components/RegimeBreakdown";
import StrategyBuilder from "../components/StrategyBuilder";
import Header from "../components/Header";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [isLoading, setIsLoading] = useState(false);
  const [backtestResult, setBacktestResult] = useState<any | null>(null);
  const [selectedStrategy, setSelectedStrategy] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Standalone OHLCV chart preview state (pre-backtest)
  const [selectedSymbol, setSelectedSymbol] = useState("RELIANCE");
  const [selectedStart, setSelectedStart] = useState("2023-01-01");
  const [selectedEnd, setSelectedEnd] = useState("2025-01-01");
  const [selectedInterval, setSelectedInterval] = useState("1d");
  const [ohlcvData, setOhlcvData] = useState<any[]>([]);
  const [isOhlcvLoading, setIsOhlcvLoading] = useState(false);
  const [ohlcvError, setOhlcvError] = useState<string | null>(null);

  // Strategy Builder Modal states
  const [showBuilder, setShowBuilder] = useState(false);
  const [strategiesTrigger, setStrategiesTrigger] = useState(0);

  // Callback when stock, dates, or timeframe change in form
  const handleSelectionChange = useCallback(
    (symbol: string, start: string, end: string, interval: string) => {
      setSelectedSymbol(symbol);
      setSelectedStart(start);
      setSelectedEnd(end);
      setSelectedInterval(interval);
    },
    []
  );

  // Fetch OHLCV data for selected stock + range for pre-backtest chart preview
  useEffect(() => {
    if (!selectedSymbol || !selectedStart || !selectedEnd) return;

    let isMounted = true;
    setIsOhlcvLoading(true);
    setOhlcvError(null);

    const url = `${API_BASE_URL}/ohlcv?symbol=${encodeURIComponent(
      selectedSymbol
    )}&start=${encodeURIComponent(selectedStart)}&end=${encodeURIComponent(
      selectedEnd
    )}&interval=${encodeURIComponent(selectedInterval)}`;

    fetch(url, {
      headers: { "bypass-tunnel-reminder": "true" },
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (!isMounted) return;
        setOhlcvData(Array.isArray(data) ? data : []);
      })
      .catch((err) => {
        if (!isMounted) return;
        console.error("Error fetching pre-backtest OHLCV:", err);
        setOhlcvError(`Could not load price chart for ${selectedSymbol}. (${err.message})`);
      })
      .finally(() => {
        if (isMounted) setIsOhlcvLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedSymbol, selectedStart, selectedEnd, selectedInterval]);

  const handleRunBacktest = async (params: any) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const response = await fetch(`${API_BASE_URL}/backtest`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "bypass-tunnel-reminder": "true" },
        body: JSON.stringify(params),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: "Failed to run backtest" }));
        throw new Error(errData?.detail || `Server returned HTTP ${response.status}`);
      }

      const data = await response.json();
      setBacktestResult(data);
      
      // Update OHLCV data with the backtest result ohlcv
      if (data?.ohlcv) {
        setOhlcvData(data.ohlcv);
      }

      // Select the first strategy (winner) by default
      if (data?.leaderboard && data.leaderboard.length > 0) {
        setSelectedStrategy(data.leaderboard[0].name);
      }
    } catch (err: any) {
      console.error("Backtest error:", err);
      setErrorMsg(err?.message || "An unexpected error occurred during backtesting.");
    } finally {
      setIsLoading(false);
    }
  };

  // Helper to extract equity curves for all strategies
  const getAllEquityCurves = () => {
    if (!backtestResult || !backtestResult.per_strategy) return {};
    const curves: { [name: string]: any[] } = {};
    Object.keys(backtestResult.per_strategy).forEach((name) => {
      curves[name] = backtestResult.per_strategy[name]?.equity || [];
    });
    return curves;
  };

  const selectedDetails = backtestResult?.per_strategy?.[selectedStrategy];

  return (
    <main className="min-h-screen bg-[#07090e] text-slate-100 p-4 md:p-8 font-sans selection:bg-blue-500 selection:text-white">
      <Header
        publicId={backtestResult?.public_id}
        pdfUrl={backtestResult?.id ? `${API_BASE_URL}/backtest/${backtestResult.id}/pdf` : undefined}
      />

      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Settings Panel */}
        <div className="lg:col-span-4 lg:sticky lg:top-8">
          <BacktestForm
            apiBaseUrl={API_BASE_URL}
            onRunBacktest={handleRunBacktest}
            isLoading={isLoading}
            onBuildStrategyClick={() => setShowBuilder(true)}
            strategiesTrigger={strategiesTrigger}
            onSelectionChange={handleSelectionChange}
          />
          
          {errorMsg && (
            <div className="mt-4 bg-rose-950/40 border border-rose-800 text-rose-300 text-sm px-4 py-3 rounded-lg flex items-start space-x-3">
              <svg className="h-5 w-5 text-rose-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span>{errorMsg}</span>
            </div>
          )}
        </div>

        {/* Right Results Dashboard */}
        <div className="lg:col-span-8 space-y-8">
          {/* Always Render Price Chart for the selected stock + date range BEFORE running backtest */}
          <PriceChart
            symbol={selectedSymbol}
            ohlcv={ohlcvData}
            trades={selectedDetails?.trades || []}
            isLoading={isOhlcvLoading}
            error={ohlcvError}
            subtitle={`Historical price candles for ${selectedStart} to ${selectedEnd} (${selectedInterval})`}
          />

          {!backtestResult && !isLoading && (
            <div className="bg-slate-900/40 border border-dashed border-slate-800 rounded-xl py-12 px-6 text-center space-y-3">
              <div className="text-slate-500 text-3xl">⚡</div>
              <h2 className="text-base font-bold text-slate-300">Ready to Run Backtest</h2>
              <p className="text-slate-500 text-xs max-w-md mx-auto">
                Price candles for <span className="font-mono text-slate-300">{selectedSymbol}</span> are rendered above. Select your strategies on the left panel and click &ldquo;Run Backtest&rdquo; to overlay buy/sell signals and compute metrics.
              </p>
            </div>
          )}

          {isLoading && (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl py-16 px-6 text-center space-y-4">
              <div className="flex justify-center">
                <span className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
              </div>
              <h2 className="text-lg font-bold text-slate-300">Running Backtests</h2>
              <p className="text-slate-500 text-sm max-w-sm mx-auto">
                Calculating strategy indicators, stop losses, profit targets, and market regimes...
              </p>
            </div>
          )}

          {backtestResult && !isLoading && (
            <>
              {/* 1. Leaderboard */}
              <Leaderboard
                entries={backtestResult?.leaderboard || []}
                selectedStrategy={selectedStrategy}
                onSelectStrategy={setSelectedStrategy}
              />

              {/* Detail view header & selector */}
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-slate-900 border border-slate-800 px-6 py-4 rounded-lg gap-4">
                <div>
                  <span className="text-slate-500 text-xs font-semibold uppercase tracking-wider">Viewing Strategy Details</span>
                  <h2 className="text-xl font-bold text-white mt-0.5">{selectedStrategy}</h2>
                </div>
                
                <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
                  {backtestResult?.id && (
                    <a
                      href={`${API_BASE_URL}/backtest/${backtestResult.id}/pdf`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center space-x-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold text-xs uppercase px-4 py-2 rounded-lg shadow-lg hover:shadow-cyan-500/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
                    >
                      <svg className="h-4 w-4 fill-current" viewBox="0 0 20 20">
                        <path d="M13 8V2H7v6H2l8 8 8-8h-5zM0 18h20v2H0v-2z" />
                      </svg>
                      <span>Download PDF Report</span>
                    </a>
                  )}

                  <div className="flex items-center space-x-2 text-sm w-full sm:w-auto">
                    <span className="text-slate-400 font-semibold uppercase text-xs whitespace-nowrap">Select Strategy:</span>
                    <select
                      value={selectedStrategy}
                      onChange={(e) => setSelectedStrategy(e.target.value)}
                      className="w-full sm:w-auto bg-slate-950 border border-slate-800 text-slate-100 rounded px-3 py-1.5 focus:outline-none focus:border-blue-500 text-sm font-semibold"
                    >
                      {(backtestResult?.leaderboard || []).map((entry: any) => (
                        <option key={entry.name} value={entry.name}>
                          {entry.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {/* 2. Equity Curve Comparison & Drawdown */}
              <EquityChart
                allCurves={getAllEquityCurves()}
                selectedStrategy={selectedStrategy}
              />

              {/* 3. Regime Breakdown & Trade Logs */}
              {selectedDetails && (
                <div className="grid grid-cols-1 gap-8">
                  <RegimeBreakdown entries={selectedDetails?.regime || []} />
                  <TradeLog trades={selectedDetails?.trades || []} />
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Strategy Builder Modal */}
      {showBuilder && (
        <StrategyBuilder
          apiBaseUrl={API_BASE_URL}
          onClose={() => setShowBuilder(false)}
          onSaveSuccess={() => setStrategiesTrigger((prev) => prev + 1)}
        />
      )}
    </main>
  );
}
