"use client";

import React from "react";

interface RegimeEntry {
  trend_regime: string;
  trades: number;
  net_pnl: number;
  win_rate: number;
}

interface RegimeBreakdownProps {
  entries: RegimeEntry[];
}

export default function RegimeBreakdown({ entries = [] }: RegimeBreakdownProps) {
  if (!entries || !Array.isArray(entries) || entries.length === 0) return null;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg shadow-xl p-6 text-slate-200">
      <h3 className="text-lg font-bold text-white mb-4">Regime Performance Breakdown</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-950 border-b border-slate-800 text-xs font-semibold uppercase tracking-wider text-slate-400">
              <th className="px-4 py-3">Market Regime</th>
              <th className="px-4 py-3 text-right">Trades</th>
              <th className="px-4 py-3 text-right">Net P&L (INR)</th>
              <th className="px-4 py-3 text-right">Win Rate</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50 font-mono text-sm text-slate-300">
            {(entries || []).map((entry) => (
              <tr key={entry.trend_regime} className="hover:bg-slate-850/40 transition-colors">
                <td className="px-4 py-3 font-sans font-semibold text-slate-200 capitalize">
                  {entry.trend_regime}
                </td>
                <td className="px-4 py-3 text-right text-slate-400">{entry.trades}</td>
                <td className={`px-4 py-3 text-right font-bold ${entry.net_pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                  {entry.net_pnl >= 0 ? "+" : ""}{entry.net_pnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </td>
                <td className="px-4 py-3 text-right text-slate-300">
                  {entry.win_rate.toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
