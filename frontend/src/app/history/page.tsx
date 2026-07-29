"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import Header from "../../components/Header";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface HistoryItem {
  id: string;
  public_id: string;
  symbol: string;
  interval: string;
  period: string;
  capital: number;
  winner: string;
  net_pnl: number;
  return_pct: number;
  created_at: string;
}

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filters
  const [symbolFilter, setSymbolFilter] = useState("");
  const [intervalFilter, setIntervalFilter] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  // Compare multi-selection
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const fetchHistory = async () => {
    setIsLoading(true);
    setErrorMsg(null);

    const queryParams = new URLSearchParams();
    if (symbolFilter) queryParams.set("symbol", symbolFilter.trim());
    if (intervalFilter) queryParams.set("interval", intervalFilter);
    if (fromDate) queryParams.set("from", fromDate);
    if (toDate) queryParams.set("to", toDate);
    queryParams.set("page", page.toString());
    queryParams.set("limit", "10");

    try {
      const res = await fetch(`${API_BASE_URL}/backtests?${queryParams.toString()}`, {
        headers: { "bypass-tunnel-reminder": "true" },
      });
      if (!res.ok) {
        throw new Error("Failed to fetch backtest history.");
      }
      const data = await res.json();
      setItems(data.items || []);
      setTotal(data.total || 0);
      setPages(data.pages || 1);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || "Error loading history.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [page]);

  const handleApplyFilters = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchHistory();
  };

  const handleClearFilters = () => {
    setSymbolFilter("");
    setIntervalFilter("");
    setFromDate("");
    setToDate("");
    setPage(1);
    setTimeout(fetchHistory, 50);
  };

  const toggleSelectRun = (pubId: string) => {
    setSelectedIds((prev) =>
      prev.includes(pubId) ? prev.filter((id) => id !== pubId) : [...prev, pubId]
    );
  };

  const handleShareRun = (pubId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const shareUrl = `${window.location.origin}/r/${pubId}`;
    navigator.clipboard.writeText(shareUrl);
    setCopiedId(pubId);
    setTimeout(() => setCopiedId(null), 2500);
  };

  return (
    <main className="min-h-screen bg-[#07090e] text-slate-100 p-4 md:p-8 font-sans selection:bg-blue-500 selection:text-white">
      <Header />

      <div className="max-w-7xl mx-auto space-y-6">
        {/* Title & Action Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Backtest History</h1>
            <p className="text-slate-400 text-sm mt-0.5">
              Review past backtest executions, reopen details, copy share links, or select runs to compare.
            </p>
          </div>

          {selectedIds.length > 0 && (
            <Link
              href={`/compare?ids=${selectedIds.join(",")}`}
              className="flex items-center justify-center space-x-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-sm px-5 py-2.5 rounded-lg shadow-lg hover:shadow-blue-500/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <span>Compare Selected ({selectedIds.length})</span>
            </Link>
          )}
        </div>

        {/* Filter Toolbar */}
        <form onSubmit={handleApplyFilters} className="bg-slate-900 border border-slate-800 p-4 rounded-xl grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 items-end">
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
              Symbol
            </label>
            <input
              type="text"
              placeholder="e.g. RELIANCE"
              value={symbolFilter}
              onChange={(e) => setSymbolFilter(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 text-white rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500 font-mono placeholder:text-slate-600"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
              Timeframe
            </label>
            <select
              value={intervalFilter}
              onChange={(e) => setIntervalFilter(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 text-white rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500 font-semibold"
            >
              <option value="">All Timeframes</option>
              <option value="1d">1 Day (1d)</option>
              <option value="1h">1 Hour (1h)</option>
              <option value="15m">15 Mins (15m)</option>
              <option value="5m">5 Mins (5m)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
              From Date
            </label>
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 text-white rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
              To Date
            </label>
            <input
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 text-white rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="submit"
              className="flex-1 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm py-2 rounded-lg transition-colors"
            >
              Filter
            </button>
            <button
              type="button"
              onClick={handleClearFilters}
              className="bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-sm px-3 py-2 rounded-lg transition-colors"
            >
              Reset
            </button>
          </div>
        </form>

        {errorMsg && (
          <div className="bg-rose-950/40 border border-rose-800 text-rose-300 text-sm p-4 rounded-lg">
            {errorMsg}
          </div>
        )}

        {/* History Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300 border-collapse">
              <thead>
                <tr className="bg-slate-950 text-slate-400 uppercase text-[11px] tracking-wider border-b border-slate-800">
                  <th className="py-3 px-4 w-10 text-center">Select</th>
                  <th className="py-3 px-4 font-bold">Stock</th>
                  <th className="py-3 px-4 font-bold">Timeframe</th>
                  <th className="py-3 px-4 font-bold">Period</th>
                  <th className="py-3 px-4 font-bold">Winner Strategy</th>
                  <th className="py-3 px-4 font-bold text-right">Net P&L</th>
                  <th className="py-3 px-4 font-bold text-right">Return %</th>
                  <th className="py-3 px-4 font-bold">Ran At</th>
                  <th className="py-3 px-4 text-center font-bold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {isLoading ? (
                  <tr>
                    <td colSpan={9} className="py-16 text-center text-slate-500">
                      <div className="flex justify-center mb-2">
                        <span className="animate-spin h-6 w-6 border-2 border-blue-500 border-t-transparent rounded-full" />
                      </div>
                      Loading history runs...
                    </td>
                  </tr>
                ) : items.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="py-16 text-center text-slate-500">
                      No past backtest runs found. Try adjusting your filters or run a backtest!
                    </td>
                  </tr>
                ) : (
                  items.map((item) => {
                    const isSelected = selectedIds.includes(item.public_id);
                    const isProfit = item.net_pnl >= 0;
                    const dateFormatted = item.created_at
                      ? new Date(item.created_at).toLocaleString("en-IN", {
                          dateStyle: "short",
                          timeStyle: "short",
                        })
                      : "-";

                    return (
                      <tr
                        key={item.id}
                        className={`hover:bg-slate-800/50 transition-colors ${
                          isSelected ? "bg-blue-950/20" : ""
                        }`}
                      >
                        <td className="py-3.5 px-4 text-center">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleSelectRun(item.public_id)}
                            className="rounded border-slate-700 bg-slate-950 text-blue-600 focus:ring-blue-500 h-4 w-4 cursor-pointer"
                          />
                        </td>
                        <td className="py-3.5 px-4 font-bold text-white font-mono">
                          {item.symbol}
                        </td>
                        <td className="py-3.5 px-4 font-semibold text-slate-300">
                          <span className="bg-slate-800 text-slate-300 text-xs px-2 py-0.5 rounded font-mono">
                            {item.interval}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-xs text-slate-400 whitespace-nowrap">
                          {item.period}
                        </td>
                        <td className="py-3.5 px-4 font-semibold text-blue-300">
                          {item.winner}
                        </td>
                        <td
                          className={`py-3.5 px-4 text-right font-mono font-bold ${
                            isProfit ? "text-emerald-400" : "text-rose-400"
                          }`}
                        >
                          ₹{item.net_pnl.toLocaleString("en-IN")}
                        </td>
                        <td
                          className={`py-3.5 px-4 text-right font-mono font-bold ${
                            isProfit ? "text-emerald-400" : "text-rose-400"
                          }`}
                        >
                          {isProfit ? "+" : ""}
                          {item.return_pct?.toFixed(2)}%
                        </td>
                        <td className="py-3.5 px-4 text-xs text-slate-400 whitespace-nowrap">
                          {dateFormatted}
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          <div className="flex items-center justify-center space-x-2">
                            <Link
                              href={`/r/${item.public_id}`}
                              className="text-xs bg-blue-600/20 text-blue-400 hover:bg-blue-600 hover:text-white px-2.5 py-1 rounded font-semibold transition-colors"
                            >
                              View
                            </Link>

                            <button
                              onClick={(e) => handleShareRun(item.public_id, e)}
                              className="text-xs bg-slate-800 text-slate-300 hover:bg-slate-700 px-2.5 py-1 rounded font-semibold transition-colors"
                              title="Copy Share Link"
                            >
                              {copiedId === item.public_id ? "Copied!" : "Share"}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {pages > 1 && (
            <div className="bg-slate-950 border-t border-slate-800 px-6 py-3.5 flex items-center justify-between text-xs text-slate-400">
              <div>
                Showing page <span className="font-bold text-white">{page}</span> of{" "}
                <span className="font-bold text-white">{pages}</span> ({total} total runs)
              </div>
              <div className="flex items-center space-x-2">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="px-3 py-1.5 bg-slate-900 border border-slate-800 rounded font-semibold text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-800"
                >
                  Previous
                </button>
                <button
                  disabled={page >= pages}
                  onClick={() => setPage((p) => Math.min(pages, p + 1))}
                  className="px-3 py-1.5 bg-slate-900 border border-slate-800 rounded font-semibold text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-800"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
