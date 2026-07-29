"use client";

import React from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  AreaChart,
  Area,
} from "recharts";

interface EquityPoint {
  time: string;
  value: number;
}

interface EquityChartProps {
  allCurves: { [strategyName: string]: EquityPoint[] };
  selectedStrategy: string;
}

const STRATEGY_COLORS: { [key: string]: string } = {
  "EMA Crossover": "#3b82f6",       // blue
  "SuperTrend": "#10b981",          // emerald
  "RSI Mean-Reversion": "#f59e0b",   // amber
  "Bollinger Breakout": "#8b5cf6",   // violet
};

export default function EquityChart({ allCurves, selectedStrategy }: EquityChartProps) {
  // 1. Prepare combined data for the all-strategies chart
  // Find the strategy with the longest timeline to align times
  const strategyNames = Object.keys(allCurves);
  if (strategyNames.length === 0) return null;

  // Let's merge the timelines
  const timeMap: { [time: string]: { [strat: string]: number } } = {};
  
  strategyNames.forEach((name) => {
    const points = allCurves[name] || [];
    points.forEach((pt) => {
      if (!timeMap[pt.time]) {
        timeMap[pt.time] = {};
      }
      timeMap[pt.time][name] = pt.value;
    });
  });

  // Convert map to sorted array
  const combinedData = Object.keys(timeMap)
    .sort()
    .map((time) => {
      const entry: any = { time };
      strategyNames.forEach((name) => {
        entry[name] = timeMap[time][name];
      });
      return entry;
    });

  // 2. Prepare single strategy data for the selected strategy (equity + drawdown)
  const selectedPoints = allCurves[selectedStrategy] || [];
  let peak = 0;
  const singleData = selectedPoints.map((pt) => {
    if (pt.value > peak) {
      peak = pt.value;
    }
    const drawdown = pt.value - peak;
    const drawdownPct = peak > 0 ? (drawdown / peak) * 100 : 0;
    return {
      time: pt.time,
      equity: pt.value,
      drawdown: drawdown, // raw value
      drawdownPct: parseFloat(drawdownPct.toFixed(2)), // in percentage
    };
  });

  return (
    <div className="space-y-6 text-slate-200">
      {/* 1. All Strategies Equity Curves */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg shadow-xl p-6">
        <h3 className="text-lg font-bold text-white mb-4">Equity Comparison (All Strategies)</h3>
        <div className="h-72 w-full font-mono text-xs">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={combinedData}>
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
              <XAxis dataKey="time" stroke="#64748b" tickLine={false} />
              <YAxis stroke="#64748b" tickLine={false} domain={["auto", "auto"]} />
              <Tooltip
                contentStyle={{ backgroundColor: "#090d16", borderColor: "#334155" }}
                labelStyle={{ fontWeight: "bold", color: "#f8fafc" }}
              />
              <Legend verticalAlign="top" height={36} />
              {strategyNames.map((name) => (
                <Line
                  key={name}
                  type="monotone"
                  dataKey={name}
                  name={name}
                  stroke={STRATEGY_COLORS[name] || "#64748b"}
                  dot={false}
                  strokeWidth={name === selectedStrategy ? 2.5 : 1.5}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 2. Selected Strategy Equity & Drawdown Area */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg shadow-xl p-6">
        <h3 className="text-lg font-bold text-white mb-4">{selectedStrategy} — Performance & Drawdown</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Equity Line */}
          <div className="h-60 w-full font-mono text-xs">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Equity Growth</h4>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={singleData}>
                <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                <XAxis dataKey="time" stroke="#64748b" tickLine={false} />
                <YAxis stroke="#64748b" tickLine={false} domain={["auto", "auto"]} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#090d16", borderColor: "#334155" }}
                  labelStyle={{ color: "#f8fafc" }}
                />
                <Line
                  type="monotone"
                  dataKey="equity"
                  name="Equity"
                  stroke={STRATEGY_COLORS[selectedStrategy] || "#3b82f6"}
                  dot={false}
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Drawdown Area */}
          <div className="h-60 w-full font-mono text-xs">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Drawdown %</h4>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={singleData}>
                <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                <XAxis dataKey="time" stroke="#64748b" tickLine={false} />
                <YAxis stroke="#64748b" tickLine={false} domain={["auto", 0]} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#090d16", borderColor: "#334155" }}
                  labelStyle={{ color: "#f8fafc" }}
                />
                <Area
                  type="monotone"
                  dataKey="drawdownPct"
                  name="Drawdown %"
                  stroke="#ef4444"
                  fill="#ef4444"
                  fillOpacity={0.2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
