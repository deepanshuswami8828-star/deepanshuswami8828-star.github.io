"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Header from "../../../components/Header";
import Leaderboard from "../../../components/Leaderboard";
import PriceChart from "../../../components/PriceChart";
import EquityChart from "../../../components/EquityChart";
import TradeLog from "../../../components/TradeLog";
import RegimeBreakdown from "../../../components/RegimeBreakdown";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SharePage() {
  const params = useParams();
  const publicId = params?.public_id as string;

  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [backtestResult, setBacktestResult] = useState<any | null>(null);
  const [selectedStrategy, setSelectedStrategy] = useState<string>("");

  useEffect(() => {
    if (!publicId) return;
    setIsLoading(true);
    setErrorMsg(null);

    fetch(`${API_BASE_URL}/r/${publicId}`, {
      headers: { "bypass-tunnel-reminder": "true" },
    })
      .then(async (res) => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `Backtest run '${publicId}' not found.`);
        }
        return res.json();
      })
      .then((data) => {
        setBacktestResult(data);
        if (data.leaderboard && data.leaderboard.length > 0) {
          setSelectedStrategy(data.leaderboard[0].name);
        }
      })
      .catch((err: any) => {
        console.error(err);
        setErrorMsg(err.message || "Failed to load shared backtest.");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [publicId]);

  const getAllEquityCurves = () => {
    if (!backtestResult || !backtestResult.per_strategy) return {};
    const curves: { [name: string]: any[] } = {};
    Object.keys(backtestResult.per_strategy).forEach((name) => {
      curves[name] = backtestResult.per_strategy[name].equity;
    });
    return curves;
  };

  const selectedDetails = backtestResult?.per_strategy?.[selectedStrategy];

  return (
    <main className="min-h-screen bg-[#07090e] text-slate-100 p-4 md:p-8 font-sans selection:bg-blue-500 selection:text-white">
      <Header
        publicId={publicId}
        pdfUrl={backtestResult?.id ? `${API_BASE_URL}/backtest/${backtestResult.id}/pdf` : undefined}
      />

      <div className="max-w-7xl mx-auto space-y-8">
        {isLoading && (
          <div className="bg-slate-900/40 border border-slate-800 rounded-xl py-24 px-6 text-center space-y-4">
            <div className="flex justify-center">
              <span className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
            </div>
            <h2 className="text-lg font-bold text-slate-300">Loading Shared Backtest</h2>
            <p className="text-slate-500 text-sm max-w-sm mx-auto">
              Fetching historical results, charts, and trade data...
            </p>
          </div>
        )}

        {errorMsg && (
          <div className="bg-rose-950/40 border border-rose-800 text-rose-300 text-sm p-6 rounded-xl text-center space-y-3">
            <div className="text-3xl">⚠️</div>
            <h2 className="text-lg font-bold text-rose-200">Unable to Load Backtest</h2>
            <p className="text-rose-400 text-sm max-w-md mx-auto">{errorMsg}</p>
          </div>
        )}

        {backtestResult && !isLoading && (
          <>
            {/* Run summary badge */}
            <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl flex flex-wrap items-center justify-between gap-4">
              <div>
                <span className="text-blue-400 font-bold text-xs uppercase tracking-wider">Public Shared Result</span>
                <h2 className="text-2xl font-extrabold text-white mt-1">
                  {backtestResult.symbol} ({backtestResult.interval})
                </h2>
                <p className="text-slate-400 text-sm mt-0.5">
                  Period: {backtestResult.period} • {backtestResult.bars} Bars Analyzed
                </p>
              </div>

              {backtestResult.leaderboard?.[0] && (
                <div className="bg-slate-950 border border-slate-800 px-5 py-3 rounded-lg text-right">
                  <span className="text-slate-400 text-xs font-semibold uppercase">Winning Strategy</span>
                  <div className="text-lg font-bold text-emerald-400">
                    {backtestResult.leaderboard[0].name}
                  </div>
                  <div className="text-xs text-slate-300 font-mono mt-0.5">
                    Net P&L: ₹{backtestResult.leaderboard[0].net_pnl.toLocaleString("en-IN")} ({backtestResult.leaderboard[0].return_pct > 0 ? "+" : ""}{backtestResult.leaderboard[0].return_pct.toFixed(2)}%)
                  </div>
                </div>
              )}
            </div>

            {/* 1. Leaderboard */}
            <Leaderboard
              entries={backtestResult.leaderboard}
              selectedStrategy={selectedStrategy}
              onSelectStrategy={setSelectedStrategy}
            />

            {/* Strategy selector bar */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-slate-900 border border-slate-800 px-6 py-4 rounded-lg gap-4">
              <div>
                <span className="text-slate-500 text-xs font-semibold uppercase tracking-wider">Viewing Strategy Details</span>
                <h2 className="text-xl font-bold text-white mt-0.5">{selectedStrategy}</h2>
              </div>
              
              <div className="flex items-center space-x-2 text-sm w-full sm:w-auto">
                <span className="text-slate-400 font-semibold uppercase text-xs whitespace-nowrap">Select Strategy:</span>
                <select
                  value={selectedStrategy}
                  onChange={(e) => setSelectedStrategy(e.target.value)}
                  className="w-full sm:w-auto bg-slate-950 border border-slate-800 text-slate-100 rounded px-3 py-1.5 focus:outline-none focus:border-blue-500 text-sm font-semibold"
                >
                  {backtestResult.leaderboard?.map((entry: any) => (
                    <option key={entry.name} value={entry.name}>
                      {entry.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* 2. Candlestick Chart */}
            {selectedDetails && (
              <PriceChart ohlcv={backtestResult.ohlcv} trades={selectedDetails.trades} />
            )}

            {/* 3. Equity Curve Comparison */}
            <EquityChart
              allCurves={getAllEquityCurves()}
              selectedStrategy={selectedStrategy}
            />

            {/* 4. Regime & Trade Log */}
            {selectedDetails && (
              <div className="grid grid-cols-1 gap-8">
                <RegimeBreakdown entries={selectedDetails.regime} />
                <TradeLog trades={selectedDetails.trades} />
              </div>
            )}
          </>
        )}
      </div>
    </main>
  );
}
