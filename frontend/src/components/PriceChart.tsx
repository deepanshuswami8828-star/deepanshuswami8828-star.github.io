"use client";

import React, { useEffect, useRef, useState } from "react";
import { createChart, ColorType } from "lightweight-charts";

interface OHLCVBar {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface Trade {
  entry_time: string;
  exit_time: string;
  direction: "long" | "short" | string;
  entry: number;
  exit: number;
  qty: number;
  sl: number;
  target: number;
  net_pnl: number;
  return_pct: number;
  entry_reason: string;
  exit_reason: string;
}

interface PriceChartProps {
  symbol?: string;
  ohlcv?: OHLCVBar[];
  trades?: any[]; // list of list representation from backend
  isLoading?: boolean;
  error?: string | null;
  subtitle?: string;
}

export default function PriceChart({
  symbol = "RELIANCE",
  ohlcv = [],
  trades = [],
  isLoading = false,
  error = null,
  subtitle,
}: PriceChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const [hoveredTrade, setHoveredTrade] = useState<any | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  // Map backend list-of-lists trades to typed dict trades if provided
  const parsedTrades: Trade[] = (trades || []).map((t) => ({
    entry_time: t[0] || "",
    exit_time: t[1] || "",
    direction: t[2] || "long",
    entry: t[3] || 0,
    exit: t[4] || 0,
    qty: t[5] || 0,
    sl: t[6] || 0,
    target: t[7] || 0,
    net_pnl: t[8] || 0,
    return_pct: t[9] || 0,
    trend_regime: t[10] || "",
    entry_reason: t[11] || "",
    exit_reason: t[12] || "",
  }));

  useEffect(() => {
    if (!chartContainerRef.current || !ohlcv || ohlcv.length === 0) return;

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    // Create chart
    const chart: any = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#090d16" },
        textColor: "#94a3b8",
      },
      grid: {
        vertLines: { color: "#1e293b", style: 1 },
        horzLines: { color: "#1e293b", style: 1 },
      },
      width: chartContainerRef.current.clientWidth,
      height: 400,
      timeScale: {
        borderColor: "#334155",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    // Add candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: "#10b981",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
    });

    // Map data cleanly
    const chartData = ohlcv.map((bar) => ({
      time: bar.time,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
    }));

    candlestickSeries.setData(chartData);

    // Create markers for trades if available
    if (parsedTrades.length > 0) {
      const markers: any[] = [];
      parsedTrades.forEach((trade, idx) => {
        if (trade.entry_time) {
          markers.push({
            time: trade.entry_time.split(" ")[0],
            position: trade.direction === "long" ? "belowBar" : "aboveBar",
            color: trade.direction === "long" ? "#10b981" : "#f59e0b",
            shape: trade.direction === "long" ? "arrowUp" : "arrowDown",
            text: `BUY`,
            id: `entry_${idx}`,
          });
        }

        if (trade.exit_time) {
          markers.push({
            time: trade.exit_time.split(" ")[0],
            position: trade.direction === "long" ? "aboveBar" : "belowBar",
            color: "#ef4444",
            shape: trade.direction === "long" ? "arrowDown" : "arrowUp",
            text: `SELL`,
            id: `exit_${idx}`,
          });
        }
      });

      markers.sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());
      candlestickSeries.setMarkers(markers);
    }

    // Fit content
    chart.timeScale().fitContent();

    // Subscribe to crosshair moves for tooltip information
    chart.subscribeCrosshairMove((param: any) => {
      if (!param.point || !param.time || param.point.x < 0 || param.point.y < 0) {
        setHoveredTrade(null);
        return;
      }

      const timeStr = param.time.toString();
      const matchedTrade = parsedTrades.find(
        (t) => t.entry_time.startsWith(timeStr) || t.exit_time.startsWith(timeStr)
      );

      if (matchedTrade) {
        setHoveredTrade(matchedTrade);
        setTooltipPos({
          x: param.point.x + 15,
          y: param.point.y + 15,
        });
      } else {
        setHoveredTrade(null);
      }
    });

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [ohlcv, trades]);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg shadow-xl p-6 text-slate-200 relative">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 gap-2 border-b border-slate-800 pb-3">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <span>📈</span> {symbol} Price Chart
          </h3>
          {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
        </div>
        {parsedTrades.length > 0 && (
          <span className="text-xs font-semibold bg-blue-950/80 text-blue-300 border border-blue-800/60 px-2.5 py-1 rounded">
            {parsedTrades.length} Trade Signals Overlaid
          </span>
        )}
      </div>

      {isLoading && (
        <div className="py-24 text-center space-y-3 bg-slate-950/40 rounded border border-slate-850">
          <div className="flex justify-center">
            <span className="animate-spin h-7 w-7 border-3 border-blue-500 border-t-transparent rounded-full" />
          </div>
          <p className="text-sm font-semibold text-slate-400">Fetching live price history for {symbol}...</p>
        </div>
      )}

      {error && !isLoading && (
        <div className="py-16 px-4 text-center bg-rose-950/20 border border-rose-900/50 rounded text-rose-300 space-y-2">
          <p className="text-sm font-bold">Failed to load price chart</p>
          <p className="text-xs text-rose-400">{error}</p>
        </div>
      )}

      {!isLoading && !error && (!ohlcv || ohlcv.length === 0) && (
        <div className="py-20 text-center text-slate-500 space-y-2 bg-slate-950/40 rounded border border-dashed border-slate-800">
          <p className="text-base font-semibold text-slate-400">No price candles found</p>
          <p className="text-xs max-w-sm mx-auto text-slate-500">
            No historical price data available for {symbol} in the selected date range. Select a different date range or symbol.
          </p>
        </div>
      )}

      {!isLoading && !error && ohlcv && ohlcv.length > 0 && (
        <div ref={chartContainerRef} className="w-full relative min-h-[400px]" />
      )}

      {/* Tooltip Overlay */}
      {hoveredTrade && (
        <div
          style={{
            position: "absolute",
            left: `${tooltipPos.x}px`,
            top: `${tooltipPos.y}px`,
            zIndex: 100,
          }}
          className="bg-slate-950/95 backdrop-blur border border-slate-700 p-4 rounded-md shadow-2xl text-xs space-y-2 pointer-events-none max-w-sm"
        >
          <div className="flex justify-between items-center border-b border-slate-800 pb-1.5 mb-1.5">
            <span className="font-bold text-slate-200 uppercase">Trade Details</span>
            <span
              className={`font-bold px-1 rounded ${
                hoveredTrade.direction === "long"
                  ? "bg-emerald-500/20 text-emerald-400"
                  : "bg-amber-500/20 text-amber-400"
              }`}
            >
              {hoveredTrade.direction}
            </span>
          </div>
          <div>
            <span className="text-slate-500">Qty:</span>{" "}
            <span className="font-mono text-slate-300 font-semibold">{hoveredTrade.qty}</span>
          </div>
          <div>
            <span className="text-slate-500">Entry:</span>{" "}
            <span className="font-mono text-slate-300">INR {hoveredTrade.entry?.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-slate-500">Exit:</span>{" "}
            <span className="font-mono text-slate-300">INR {hoveredTrade.exit?.toFixed(2)}</span>
          </div>
          <div className="border-t border-slate-800 pt-1.5">
            <span className="text-slate-400 font-semibold block">Entry Reason:</span>
            <p className="text-slate-300 italic">{hoveredTrade.entry_reason}</p>
          </div>
          <div className="border-t border-slate-800 pt-1.5">
            <span className="text-slate-400 font-semibold block">Exit Reason:</span>
            <p className="text-slate-300 italic">{hoveredTrade.exit_reason}</p>
          </div>
          <div className="border-t border-slate-800 pt-1.5 flex justify-between">
            <span className="text-slate-500">Net P&L:</span>
            <span
              className={`font-mono font-bold ${
                (hoveredTrade.net_pnl || 0) >= 0 ? "text-emerald-400" : "text-rose-400"
              }`}
            >
              {(hoveredTrade.net_pnl || 0) >= 0 ? "+" : ""}
              {hoveredTrade.net_pnl?.toFixed(2)} ({hoveredTrade.return_pct?.toFixed(2)}%)
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
