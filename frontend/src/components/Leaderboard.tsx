"use client";

import React from "react";

interface LeaderboardEntry {
  name: string;
  net_pnl: number;
  return_pct: number;
  trades: number;
  win_rate: number;
  profit_factor: number;
  reward_risk: number;
  max_drawdown_pct: number;
  sharpe: number;
  expectancy: number;
}

interface LeaderboardProps {
  entries: LeaderboardEntry[];
  selectedStrategy: string;
  onSelectStrategy: (name: string) => void;
}

export default function Leaderboard({ entries = [], selectedStrategy, onSelectStrategy }: LeaderboardProps) {
  if (!entries || !Array.isArray(entries) || entries.length === 0) return null;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg shadow-xl overflow-hidden text-slate-200">
      <div className="px-6 py-4 border-b border-slate-800 bg-slate-900/50 flex justify-between items-center">
        <h2 className="text-lg font-bold tracking-tight text-white">Strategy Leaderboard</h2>
        <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Ranked by Net P&L</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-950 border-b border-slate-800 text-xs font-semibold uppercase tracking-wider text-slate-400">
              <th className="px-6 py-3">Strategy</th>
              <th className="px-4 py-3 text-right">Net P&L (INR)</th>
              <th className="px-4 py-3 text-right">Return %</th>
              <th className="px-4 py-3 text-right">Trades</th>
              <th className="px-4 py-3 text-right">Win Rate</th>
              <th className="px-4 py-3 text-right">PF</th>
              <th className="px-4 py-3 text-right">R:R</th>
              <th className="px-4 py-3 text-right">Max DD %</th>
              <th className="px-4 py-3 text-right">Sharpe</th>
              <th className="px-6 py-3 text-right">Expectancy</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50 font-mono text-sm">
            {(entries || []).map((entry, index) => {
              const isWinner = index === 0;
              const isSelected = entry.name === selectedStrategy;
              
              return (
                <tr
                  key={entry.name}
                  onClick={() => onSelectStrategy(entry.name)}
                  className={`hover:bg-slate-800/40 cursor-pointer transition-colors ${
                    isWinner ? "bg-emerald-950/20 text-emerald-100 hover:bg-emerald-950/30" : ""
                  } ${isSelected ? "ring-1 ring-blue-500/50 bg-slate-800/20" : ""}`}
                >
                  <td className="px-6 py-4 font-sans font-semibold text-slate-100 flex items-center space-x-2">
                    {isWinner && (
                      <span className="bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider">
                        Winner
                      </span>
                    )}
                    <span>{entry.name}</span>
                  </td>
                  <td className={`px-4 py-4 text-right font-bold ${entry.net_pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                    {entry.net_pnl >= 0 ? "+" : ""}{entry.net_pnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td className={`px-4 py-4 text-right ${entry.return_pct >= 0 ? "text-emerald-500" : "text-rose-500"}`}>
                    {entry.return_pct >= 0 ? "+" : ""}{entry.return_pct.toFixed(2)}%
                  </td>
                  <td className="px-4 py-4 text-right text-slate-300">{entry.trades}</td>
                  <td className="px-4 py-4 text-right text-slate-300">{entry.win_rate.toFixed(1)}%</td>
                  <td className="px-4 py-4 text-right text-slate-300">{entry.profit_factor === Infinity ? "∞" : entry.profit_factor.toFixed(2)}</td>
                  <td className="px-4 py-4 text-right text-slate-300">{entry.reward_risk === Infinity ? "∞" : entry.reward_risk.toFixed(2)}</td>
                  <td className="px-4 py-4 text-right text-rose-400/80">{entry.max_drawdown_pct.toFixed(2)}%</td>
                  <td className="px-4 py-4 text-right text-slate-300">{entry.sharpe.toFixed(2)}</td>
                  <td className={`px-4 py-4 text-right ${entry.expectancy >= 0 ? "text-emerald-500/90" : "text-rose-500/90"}`}>
                    {entry.expectancy >= 0 ? "+" : ""}{entry.expectancy.toFixed(2)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
