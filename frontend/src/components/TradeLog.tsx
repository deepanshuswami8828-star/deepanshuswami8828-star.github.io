"use client";

import React, { useState } from "react";

interface TradeLogProps {
  trades: any[][]; // list of lists representation
}

export default function TradeLog({ trades = [] }: TradeLogProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [filterType, setFilterType] = useState<"all" | "long" | "short">("all");
  const [filterResult, setFilterResult] = useState<"all" | "profit" | "loss">("all");
  const pageSize = 15;

  const parsedTrades = (trades || []).map((t) => ({
    entry_time: t?.[0] || "",
    exit_time: t?.[1] || "",
    direction: t?.[2] || "long",
    entry: t?.[3] || 0,
    exit: t?.[4] || 0,
    qty: t?.[5] || 0,
    sl: t?.[6] || 0,
    target: t?.[7] || 0,
    net_pnl: t?.[8] || 0,
    return_pct: t?.[9] || 0,
    trend_regime: t?.[10] || "",
    entry_reason: t?.[11] || "",
    exit_reason: t?.[12] || "",
  }));

  // Filtering
  const filteredTrades = parsedTrades.filter((trade) => {
    if (filterType === "long" && trade.direction !== "long") return false;
    if (filterType === "short" && trade.direction !== "short") return false;
    if (filterResult === "profit" && trade.net_pnl <= 0) return false;
    if (filterResult === "loss" && trade.net_pnl >= 0) return false;
    return true;
  });

  const totalPages = Math.ceil(filteredTrades.length / pageSize);
  const paginatedTrades = filteredTrades.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg shadow-xl p-6 text-slate-200 space-y-4">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center border-b border-slate-800 pb-4 gap-4">
        <div>
          <h3 className="text-lg font-bold text-white">Trade Logs</h3>
          <p className="text-xs text-slate-500 font-mono mt-0.5">Total: {filteredTrades.length} / {parsedTrades.length} trades</p>
        </div>
        
        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          {/* Direction Filter */}
          <div className="flex items-center space-x-2 text-xs">
            <span className="text-slate-400 font-semibold uppercase">Dir:</span>
            <select
              value={filterType}
              onChange={(e) => {
                setFilterType(e.target.value as any);
                setCurrentPage(1);
              }}
              className="bg-slate-950 border border-slate-800 text-slate-300 rounded px-2.5 py-1 focus:outline-none focus:border-blue-500"
            >
              <option value="all">All</option>
              <option value="long">Long</option>
              <option value="short">Short</option>
            </select>
          </div>

          {/* Outcome Filter */}
          <div className="flex items-center space-x-2 text-xs">
            <span className="text-slate-400 font-semibold uppercase">Result:</span>
            <select
              value={filterResult}
              onChange={(e) => {
                setFilterResult(e.target.value as any);
                setCurrentPage(1);
              }}
              className="bg-slate-950 border border-slate-800 text-slate-300 rounded px-2.5 py-1 focus:outline-none focus:border-blue-500"
            >
              <option value="all">All</option>
              <option value="profit">Profits</option>
              <option value="loss">Losses</option>
            </select>
          </div>
        </div>
      </div>

      {filteredTrades.length === 0 ? (
        <div className="text-center py-12 text-slate-600">No trades match the selected filters.</div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-950 border-b border-slate-800 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  <th className="px-4 py-3">Entry Time</th>
                  <th className="px-4 py-3">Exit Time</th>
                  <th className="px-2 py-3 text-center">Dir</th>
                  <th className="px-4 py-3 text-right">Entry (INR)</th>
                  <th className="px-4 py-3 text-right">Exit (INR)</th>
                  <th className="px-2 py-3 text-right">Qty</th>
                  <th className="px-4 py-3 text-right">SL</th>
                  <th className="px-4 py-3 text-right">Target</th>
                  <th className="px-4 py-3 text-right">Net P&L</th>
                  <th className="px-4 py-3 text-right">Return %</th>
                  <th className="px-4 py-3">Regime</th>
                  <th className="px-6 py-3">Trigger Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50 font-mono text-xs text-slate-300">
                {paginatedTrades.map((trade, idx) => (
                  <tr key={idx} className="hover:bg-slate-850/40 transition-colors">
                    <td className="px-4 py-3 whitespace-nowrap text-slate-400">{trade.entry_time}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-slate-400">{trade.exit_time}</td>
                    <td className="px-2 py-3 text-center font-sans">
                      <span className={`font-bold px-1.5 py-0.5 rounded text-[10px] uppercase ${
                        trade.direction === "long" ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400"
                      }`}>
                        {trade.direction}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">{trade.entry.toFixed(2)}</td>
                    <td className="px-4 py-3 text-right">{trade.exit.toFixed(2)}</td>
                    <td className="px-2 py-3 text-right text-slate-400">{trade.qty}</td>
                    <td className="px-4 py-3 text-right text-slate-400">{trade.sl.toFixed(2)}</td>
                    <td className="px-4 py-3 text-right text-slate-400">{trade.target.toFixed(2)}</td>
                    <td className={`px-4 py-3 text-right font-bold ${trade.net_pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                      {trade.net_pnl >= 0 ? "+" : ""}{trade.net_pnl.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </td>
                    <td className={`px-4 py-3 text-right ${trade.return_pct >= 0 ? "text-emerald-500" : "text-rose-500"}`}>
                      {trade.return_pct >= 0 ? "+" : ""}{trade.return_pct.toFixed(2)}%
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-slate-400 font-sans text-xs uppercase tracking-wider">{trade.trend_regime}</td>
                    <td className="px-6 py-3 font-sans text-slate-400 max-w-sm overflow-hidden text-ellipsis whitespace-nowrap" title={trade.entry_reason}>
                      <span className="font-bold text-slate-300">[{trade.entry_reason}]</span> then <span className="italic">[{trade.exit_reason}]</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex justify-between items-center border-t border-slate-800 pt-4 text-xs font-semibold">
              <button
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                className="bg-slate-950 border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-900 px-3 py-1.5 rounded disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                Previous
              </button>
              <span className="text-slate-500">
                Page <span className="text-slate-300 font-mono">{currentPage}</span> of <span className="text-slate-300 font-mono">{totalPages}</span>
              </span>
              <button
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                className="bg-slate-950 border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-900 px-3 py-1.5 rounded disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
