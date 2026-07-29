"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Header from "../../components/Header";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const COLOR_PALETTE = [
  "#38bdf8", // Sky blue
  "#34d399", // Emerald
  "#a78bfa", // Violet
  "#fbbf24", // Amber
  "#f43f5e", // Rose
  "#2dd4bf", // Teal
];

function CompareContent() {
  const searchParams = useSearchParams();
  const rawIds = searchParams?.get("ids") || "";

  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [availableHistory, setAvailableHistory] = useState<any[]>([]);
  const [runsData, setRunsData] = useState<{ [id: string]: any }>({});
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Parse initial IDs from URL query params
  useEffect(() => {
    if (rawIds) {
      const parsed = rawIds.split(",").map((s) => s.trim()).filter(Boolean);
      setCompareIds(parsed);
    }
  }, [rawIds]);

  // Load history list for the picker
  useEffect(() => {
    fetch(`${API_BASE_URL}/backtests?limit=50`, {
      headers: { "bypass-tunnel-reminder": "true" },
    })
      .then((res) => res.json())
      .then((data) => {
        setAvailableHistory(data.items || []);
      })
      .catch((err) => console.error("Failed to load history list:", err));
  }, []);

  // Fetch full details for all selected compare IDs
  useEffect(() => {
    if (compareIds.length === 0) {
      setRunsData({});
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);

    Promise.all(
      compareIds.map((pubId) =>
        fetch(`${API_BASE_URL}/r/${pubId}`, {
          headers: { "bypass-tunnel-reminder": "true" },
        })
          .then((res) => {
            if (!res.ok) throw new Error(`Run '${pubId}' not found`);
            return res.json();
          })
          .then((data) => ({ pubId, data }))
          .catch((err) => {
            console.error(err);
            return null;
          })
      )
    )
      .then((results) => {
        const map: { [id: string]: any } = {};
        results.forEach((r) => {
          if (r) map[r.pubId] = r.data;
        });
        setRunsData(map);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [compareIds]);

  const handleAddId = (pubId: string) => {
    if (!pubId || compareIds.includes(pubId)) return;
    setCompareIds([...compareIds, pubId]);
  };

  const handleRemoveId = (pubId: string) => {
    setCompareIds(compareIds.filter((id) => id !== pubId));
  };

  // Build Side-by-Side Data
  const validRuns = compareIds
    .map((id) => ({ id, data: runsData[id] }))
    .filter((r) => r.data && r.data.leaderboard && r.data.leaderboard.length > 0);

  // Build Normalized Equity Overlay Data
  // We normalize trading timeline into 100 percentage steps (0% to 100%)
  const buildNormalizedChartData = () => {
    if (validRuns.length === 0) return [];

    const numSteps = 100;
    const chartPoints: any[] = [];

    for (let step = 0; step <= numSteps; step++) {
      const stepPct = step; // 0 to 100
      const pointObj: any = { step: `${stepPct}%`, stepPct };

      validRuns.forEach((runItem) => {
        const data = runItem.data;
        const winnerName = data.leaderboard[0].name;
        const stratDetails = data.per_strategy?.[winnerName];
        if (!stratDetails || !stratDetails.equity || stratDetails.equity.length === 0) {
          return;
        }

        const eqList = stratDetails.equity;
        // Interpolate index
        const exactIdx = Math.min(
          eqList.length - 1,
          Math.floor((stepPct / 100) * (eqList.length - 1))
        );
        const startVal = eqList[0].value;
        const currVal = eqList[exactIdx].value;

        // Compute percentage return relative to starting capital
        const returnPct = startVal > 0 ? ((currVal - startVal) / startVal) * 100 : 0;
        const runKey = `${data.symbol} (${data.interval}) - ${winnerName} [${runItem.id.slice(0, 6)}]`;

        pointObj[runKey] = parseFloat(returnPct.toFixed(2));
      });

      chartPoints.push(pointObj);
    }

    return chartPoints;
  };

  const normalizedChartData = buildNormalizedChartData();

  return (
    <main className="min-h-screen bg-[#07090e] text-slate-100 p-4 md:p-8 font-sans selection:bg-blue-500 selection:text-white">
      <Header />

      <div className="max-w-7xl mx-auto space-y-8">
        {/* Title & Selector */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Compare Backtest Runs</h1>
            <p className="text-slate-400 text-sm mt-0.5">
              Side-by-side performance metrics and normalized % return equity curves across different stocks, periods, or capitals.
            </p>
          </div>

          {/* Quick Picker */}
          <div className="flex items-center space-x-2">
            <select
              onChange={(e) => {
                handleAddId(e.target.value);
                e.target.value = "";
              }}
              className="bg-slate-900 border border-slate-800 text-slate-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 font-semibold"
            >
              <option value="">+ Add Run to Compare...</option>
              {availableHistory
                .filter((h) => !compareIds.includes(h.public_id))
                .map((h) => (
                  <option key={h.public_id} value={h.public_id}>
                    {h.symbol} ({h.interval}) - {h.winner} ({h.return_pct > 0 ? "+" : ""}{h.return_pct.toFixed(1)}%)
                  </option>
                ))}
            </select>
          </div>
        </div>

        {/* Active Selection Pills */}
        {compareIds.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 bg-slate-900/60 p-3 rounded-lg border border-slate-800">
            <span className="text-slate-400 text-xs font-semibold uppercase mr-2">Selected Runs:</span>
            {compareIds.map((id, idx) => {
              const run = runsData[id];
              const color = COLOR_PALETTE[idx % COLOR_PALETTE.length];
              const label = run
                ? `${run.symbol} (${run.interval}) - ${run.leaderboard?.[0]?.name || "Run"}`
                : id;

              return (
                <span
                  key={id}
                  className="inline-flex items-center space-x-2 text-xs font-semibold px-3 py-1.5 rounded-full border bg-slate-950 text-white"
                  style={{ borderColor: color }}
                >
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
                  <span>{label}</span>
                  <button
                    onClick={() => handleRemoveId(id)}
                    className="text-slate-400 hover:text-white ml-1 font-bold"
                  >
                    ×
                  </button>
                </span>
              );
            })}
          </div>
        )}

        {compareIds.length === 0 && (
          <div className="bg-slate-900/40 border border-dashed border-slate-800 rounded-xl py-20 px-6 text-center space-y-3">
            <div className="text-4xl">⚖️</div>
            <h2 className="text-lg font-bold text-slate-300">No Runs Selected for Comparison</h2>
            <p className="text-slate-500 text-sm max-w-md mx-auto">
              Select 2 or more runs from the dropdown above or check boxes on the History page to view side-by-side metrics and normalized performance overlays.
            </p>
          </div>
        )}

        {isLoading && (
          <div className="bg-slate-900/40 border border-slate-800 rounded-xl py-16 px-6 text-center space-y-3">
            <div className="flex justify-center">
              <span className="animate-spin h-7 w-7 border-4 border-blue-500 border-t-transparent rounded-full" />
            </div>
            <p className="text-slate-400 text-sm">Loading comparison metrics and normalized equity curves...</p>
          </div>
        )}

        {validRuns.length > 0 && !isLoading && (
          <>
            {/* 1. Normalized Equity Overlay Chart */}
            <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl space-y-4 shadow-xl">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-blue-400 font-bold text-xs uppercase tracking-wider">Normalized Comparison</span>
                  <span className="bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] font-semibold px-2 py-0.5 rounded">
                    % Return vs Timeline
                  </span>
                </div>
                <h3 className="text-lg font-bold text-white mt-1">
                  Overlaid Normalized Equity Curves (% Return)
                </h3>
                <p className="text-slate-400 text-xs mt-0.5">
                  Normalized to percentage return relative to initial trade capital over trading progress (0% to 100%), ensuring fair comparison across different dates and capitals.
                </p>
              </div>

              <div className="h-80 w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={normalizedChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis
                      dataKey="step"
                      stroke="#64748b"
                      fontSize={11}
                      tickLine={false}
                    />
                    <YAxis
                      stroke="#64748b"
                      fontSize={11}
                      tickFormatter={(v) => `${v > 0 ? "+" : ""}${v}%`}
                      domain={["auto", "auto"]}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#090d16",
                        borderColor: "#334155",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                      formatter={(val: any) => [`${val > 0 ? "+" : ""}${val}%`, "Return"]}
                    />
                    <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />

                    {validRuns.map((runItem, idx) => {
                      const data = runItem.data;
                      const winnerName = data.leaderboard[0].name;
                      const runKey = `${data.symbol} (${data.interval}) - ${winnerName} [${runItem.id.slice(0, 6)}]`;
                      const color = COLOR_PALETTE[idx % COLOR_PALETTE.length];

                      return (
                        <Line
                          key={runKey}
                          type="monotone"
                          dataKey={runKey}
                          stroke={color}
                          strokeWidth={2.5}
                          dot={false}
                        />
                      );
                    })}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* 2. Side-by-Side Metrics Table */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
              <div className="p-6 border-b border-slate-800">
                <h3 className="text-lg font-bold text-white">Side-by-Side Metrics Table</h3>
                <p className="text-slate-400 text-xs mt-0.5">
                  Direct comparison of risk metrics, returns, drawdowns, win rates, and trade frequency.
                </p>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-300 border-collapse">
                  <thead>
                    <tr className="bg-slate-950 text-slate-400 uppercase text-[11px] tracking-wider border-b border-slate-800">
                      <th className="py-3.5 px-5 font-bold w-48 bg-slate-950/80 sticky left-0 z-10 border-r border-slate-800">
                        Metric
                      </th>
                      {validRuns.map((runItem, idx) => {
                        const data = runItem.data;
                        const color = COLOR_PALETTE[idx % COLOR_PALETTE.length];
                        return (
                          <th key={runItem.id} className="py-3.5 px-5 font-bold border-r border-slate-800 min-w-[200px]">
                            <div className="flex items-center space-x-2">
                              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
                              <span className="text-white font-mono text-xs">{data.symbol} ({data.interval})</span>
                            </div>
                          </th>
                        );
                      })}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-sans">
                    {/* Period */}
                    <tr>
                      <td className="py-3 px-5 font-semibold text-slate-400 bg-slate-950/50 sticky left-0 z-10 border-r border-slate-800">
                        Period
                      </td>
                      {validRuns.map((r) => (
                        <td key={r.id} className="py-3 px-5 text-xs text-slate-300 border-r border-slate-800 whitespace-nowrap">
                          {r.data.period}
                        </td>
                      ))}
                    </tr>

                    {/* Winning Strategy */}
                    <tr>
                      <td className="py-3 px-5 font-semibold text-slate-400 bg-slate-950/50 sticky left-0 z-10 border-r border-slate-800">
                        Winning Strategy
                      </td>
                      {validRuns.map((r) => (
                        <td key={r.id} className="py-3 px-5 font-bold text-blue-400 border-r border-slate-800">
                          {r.data.leaderboard[0].name}
                        </td>
                      ))}
                    </tr>

                    {/* Net P&L */}
                    <tr>
                      <td className="py-3 px-5 font-semibold text-slate-400 bg-slate-950/50 sticky left-0 z-10 border-r border-slate-800">
                        Net P&L (₹)
                      </td>
                      {validRuns.map((r) => {
                        const val = r.data.leaderboard[0].net_pnl;
                        const isProf = val >= 0;
                        return (
                          <td key={r.id} className={`py-3 px-5 font-mono font-bold border-r border-slate-800 ${isProf ? "text-emerald-400" : "text-rose-400"}`}>
                            ₹{val.toLocaleString("en-IN")}
                          </td>
                        );
                      })}
                    </tr>

                    {/* Net Return % */}
                    <tr>
                      <td className="py-3 px-5 font-semibold text-slate-400 bg-slate-950/50 sticky left-0 z-10 border-r border-slate-800">
                        Net Return (%)
                      </td>
                      {validRuns.map((r) => {
                        const val = r.data.leaderboard[0].return_pct;
                        const isProf = val >= 0;
                        return (
                          <td key={r.id} className={`py-3 px-5 font-mono font-bold border-r border-slate-800 ${isProf ? "text-emerald-400" : "text-rose-400"}`}>
                            {isProf ? "+" : ""}{val.toFixed(2)}%
                          </td>
                        );
                      })}
                    </tr>

                    {/* Win Rate */}
                    <tr>
                      <td className="py-3 px-5 font-semibold text-slate-400 bg-slate-950/50 sticky left-0 z-10 border-r border-slate-800">
                        Win Rate (%)
                      </td>
                      {validRuns.map((r) => (
                        <td key={r.id} className="py-3 px-5 font-mono text-slate-200 border-r border-slate-800">
                          {(r.data.leaderboard[0].win_rate * 100).toFixed(1)}%
                        </td>
                      ))}
                    </tr>

                    {/* Profit Factor */}
                    <tr>
                      <td className="py-3 px-5 font-semibold text-slate-400 bg-slate-950/50 sticky left-0 z-10 border-r border-slate-800">
                        Profit Factor
                      </td>
                      {validRuns.map((r) => (
                        <td key={r.id} className="py-3 px-5 font-mono text-slate-200 border-r border-slate-800">
                          {r.data.leaderboard[0].profit_factor?.toFixed(2)}
                        </td>
                      ))}
                    </tr>

                    {/* Sharpe Ratio */}
                    <tr>
                      <td className="py-3 px-5 font-semibold text-slate-400 bg-slate-950/50 sticky left-0 z-10 border-r border-slate-800">
                        Sharpe Ratio
                      </td>
                      {validRuns.map((r) => (
                        <td key={r.id} className="py-3 px-5 font-mono text-slate-200 border-r border-slate-800">
                          {r.data.leaderboard[0].sharpe?.toFixed(2)}
                        </td>
                      ))}
                    </tr>

                    {/* Max Drawdown */}
                    <tr>
                      <td className="py-3 px-5 font-semibold text-slate-400 bg-slate-950/50 sticky left-0 z-10 border-r border-slate-800">
                        Max Drawdown (%)
                      </td>
                      {validRuns.map((r) => (
                        <td key={r.id} className="py-3 px-5 font-mono text-rose-400 font-semibold border-r border-slate-800">
                          -{Math.abs(r.data.leaderboard[0].max_drawdown_pct).toFixed(2)}%
                        </td>
                      ))}
                    </tr>

                    {/* Total Trades */}
                    <tr>
                      <td className="py-3 px-5 font-semibold text-slate-400 bg-slate-950/50 sticky left-0 z-10 border-r border-slate-800">
                        Total Trades
                      </td>
                      {validRuns.map((r) => (
                        <td key={r.id} className="py-3 px-5 font-mono text-slate-200 border-r border-slate-800">
                          {r.data.leaderboard[0].trades}
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </main>
  );
}

export default function ComparePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#07090e] p-8 flex items-center justify-center text-slate-400">
          Loading comparison page...
        </div>
      }
    >
      <CompareContent />
    </Suspense>
  );
}
