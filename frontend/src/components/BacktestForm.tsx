"use client";

import React, { useState, useEffect, useRef } from "react";

interface Stock {
  symbol: string;
  name: string;
  exchange: string;
}

interface Strategy {
  id: string;
  name: string;
  category?: string;
  description: string;
  rules_text?: string;
  params?: Record<string, any>;
  is_custom?: boolean;
  is_stub?: boolean;
}

interface BacktestFormProps {
  apiBaseUrl: string;
  onRunBacktest: (params: any) => void;
  isLoading: boolean;
  onBuildStrategyClick: () => void;
  strategiesTrigger: number; // Increment this to force strategy list reload
  onSelectionChange?: (symbol: string, start: string, end: string, interval: string) => void;
}

export default function BacktestForm({
  apiBaseUrl,
  onRunBacktest,
  isLoading,
  onBuildStrategyClick,
  strategiesTrigger,
  onSelectionChange,
}: BacktestFormProps) {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [selectedStock, setSelectedStock] = useState<Stock | null>({
    symbol: "RELIANCE",
    name: "Reliance Industries Limited",
    exchange: "NSE",
  });
  const [showDropdown, setShowDropdown] = useState(false);
  const [startDate, setStartDate] = useState("2023-01-01");
  const [endDate, setEndDate] = useState("2025-01-01");
  const [timeframe, setTimeframe] = useState("1d");
  const [capital, setCapital] = useState(100000);
  const [segment, setSegment] = useState("delivery");
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([]);
  
  // Info Popover state
  const [popoverStrategy, setPopoverStrategy] = useState<Strategy | null>(null);

  // Add Stock form state
  const [showAddStock, setShowAddStock] = useState(false);
  const [newStockSymbol, setNewStockSymbol] = useState("");
  const [newStockName, setNewStockName] = useState("");
  const [addStockLoading, setAddStockLoading] = useState(false);
  const [addStockError, setAddStockError] = useState<string | null>(null);
  const [addStockSuccess, setAddStockSuccess] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  const dropdownRef = useRef<HTMLDivElement>(null);

  // Notify parent of selection changes for pre-backtest OHLCV chart preview
  useEffect(() => {
    if (selectedStock?.symbol && onSelectionChange) {
      onSelectionChange(selectedStock.symbol, startDate, endDate, timeframe);
    }
  }, [selectedStock, startDate, endDate, timeframe]);

  // Fetch registered strategies (built-ins + customs)
  const fetchStrategies = () => {
    setApiError(null);
    fetch(`${apiBaseUrl}/strategies`, {
      headers: { "bypass-tunnel-reminder": "true" },
    })
      .then((res) => {
        if (!res.ok) throw new Error(`Server returned HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        const safeData = Array.isArray(data) ? data : [];
        setStrategies(safeData);
        // Select top strategies by default
        if (selectedStrategies.length === 0 && safeData.length > 0) {
          const defaultIds = ["ema_crossover", "macd_crossover", "stochastic_reversal", "donchian_breakout_turtle", "bollinger_squeeze_breakout"];
          const available = safeData.map((s: Strategy) => s.id);
          const toSelect = defaultIds.filter((id) => available.includes(id));
          setSelectedStrategies(toSelect.length > 0 ? toSelect : available.slice(0, 5));
        }
      })
      .catch((err) => {
        console.error("Error fetching strategies:", err);
        setApiError("Can't reach the server. Please check backend API deployment URL.");
      });
  };

  useEffect(() => {
    fetchStrategies();
  }, [apiBaseUrl, strategiesTrigger]);

  // Debounced stock search
  useEffect(() => {
    if (!searchQuery) {
      setStocks([]);
      return;
    }
    const delay = setTimeout(() => {
      fetch(`${apiBaseUrl}/stocks?query=${encodeURIComponent(searchQuery)}&limit=10`, {
        headers: { "bypass-tunnel-reminder": "true" },
      })
        .then((res) => res.json())
        .then((data) => setStocks(data))
        .catch((err) => console.error("Error fetching stocks:", err));
    }, 200);

    return () => clearTimeout(delay);
  }, [searchQuery, apiBaseUrl]);

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelectStock = (stock: Stock) => {
    setSelectedStock(stock);
    setSearchQuery("");
    setShowDropdown(false);
  };

  const handleToggleStrategy = (id: string) => {
    setSelectedStrategies((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleSelectAll = () => {
    if (selectedStrategies.length === strategies.length) {
      setSelectedStrategies([]);
    } else {
      setSelectedStrategies(strategies.map((s) => s.id));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStock) return;

    onRunBacktest({
      symbol: selectedStock.symbol,
      start: startDate,
      end: endDate,
      interval: timeframe,
      capital_per_trade: capital,
      segment: segment,
      strategy_ids: selectedStrategies,
    });
  };

  const handleAddStockSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newStockSymbol.trim()) return;

    setAddStockLoading(true);
    setAddStockError(null);
    setAddStockSuccess(null);

    try {
      const res = await fetch(`${apiBaseUrl}/stocks`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "bypass-tunnel-reminder": "true" },
        body: JSON.stringify({
          symbol: newStockSymbol.trim(),
          name: newStockName.trim() || undefined,
          exchange: "NSE",
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to validate stock symbol.");
      }

      const data = await res.json();
      setAddStockSuccess(`Successfully validated and added ${data.stock.symbol}!`);
      
      // Auto-select the newly added stock
      setSelectedStock({
        symbol: data.stock.symbol,
        name: data.stock.name,
        exchange: data.stock.exchange,
      });

      setNewStockSymbol("");
      setNewStockName("");
      setTimeout(() => {
        setShowAddStock(false);
        setAddStockSuccess(null);
      }, 1500);

    } catch (err: any) {
      console.error(err);
      setAddStockError(err.message || "Validation failed.");
    } finally {
      setAddStockLoading(false);
    }
  };

  const handleDeleteCustomStrategy = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this custom strategy?")) return;
    try {
      const res = await fetch(`${apiBaseUrl}/strategies/${id}`, {
        method: "DELETE",
        headers: { "bypass-tunnel-reminder": "true" },
      });
      if (res.ok) {
        fetchStrategies();
      }
    } catch (err) {
      console.error("Error deleting strategy:", err);
    }
  };

  // Group strategies by category
  const categoriesOrder = [
    "Trend-following",
    "Mean-reversion",
    "Momentum",
    "Breakout / volatility",
    "Volume-based",
    "Multi-indicator combos",
    "Candlestick / price-action",
    "Custom",
    "General"
  ];

  const groupedStrategies = strategies.reduce((acc, strat) => {
    const cat = strat.category || (strat.is_custom ? "Custom" : "General");
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(strat);
    return acc;
  }, {} as Record<string, Strategy[]>);

  return (
    <div className="space-y-6 bg-slate-900 border border-slate-800 p-6 rounded-lg shadow-xl text-slate-200 relative">
      <h2 className="text-xl font-bold tracking-tight text-white border-b border-slate-800 pb-3">Backtest Settings</h2>

      {apiError && (
        <div className="bg-rose-950/60 border border-rose-800 text-rose-300 text-xs p-3 rounded-lg flex items-start space-x-2">
          <span className="text-sm">⚠️</span>
          <span>{apiError}</span>
        </div>
      )}

      {/* Stock Autocomplete & Add Stock Section */}
      <div className="space-y-2 relative" ref={dropdownRef}>
        <div className="flex justify-between items-center">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">Stock Symbol</label>
          <button
            type="button"
            onClick={() => {
              setShowAddStock(!showAddStock);
              setAddStockError(null);
              setAddStockSuccess(null);
            }}
            className="text-xs text-blue-400 hover:underline"
          >
            {showAddStock ? "Cancel" : "+ Add Stock"}
          </button>
        </div>

        {showAddStock ? (
          <form onSubmit={handleAddStockSubmit} className="bg-slate-950 p-4 border border-slate-800 rounded space-y-3">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Validate & Add New Stock</h3>
            <div className="space-y-2">
              <input
                type="text"
                placeholder="Symbol (e.g. ZOMATO, TCS)"
                value={newStockSymbol}
                onChange={(e) => setNewStockSymbol(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-xs font-mono text-white placeholder-slate-600 focus:outline-none focus:border-blue-500"
              />
              <input
                type="text"
                placeholder="Company Name (Optional)"
                value={newStockName}
                onChange={(e) => setNewStockName(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-blue-500"
              />
            </div>
            
            {addStockError && (
              <p className="text-[10px] text-rose-400 font-semibold leading-tight">{addStockError}</p>
            )}
            {addStockSuccess && (
              <p className="text-[10px] text-emerald-400 font-semibold leading-tight">{addStockSuccess}</p>
            )}

            <button
              type="submit"
              disabled={addStockLoading || !newStockSymbol.trim()}
              className="w-full py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-500 text-white rounded font-bold text-xs uppercase transition-colors"
            >
              {addStockLoading ? "Validating & Adding..." : "Add Symbol"}
            </button>
          </form>
        ) : (
          <div className="relative">
            <input
              type="text"
              placeholder="Search 2,300+ NSE stocks (e.g. RELIANCE, TCS)..."
              value={selectedStock ? `${selectedStock.symbol} - ${selectedStock.name}` : searchQuery}
              onChange={(e) => {
                setSelectedStock(null);
                setSearchQuery(e.target.value);
                setShowDropdown(true);
              }}
              onFocus={() => setShowDropdown(true)}
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
            {selectedStock && (
              <button
                type="button"
                onClick={() => {
                  setSelectedStock(null);
                  setSearchQuery("");
                }}
                className="absolute right-2.5 top-2.5 text-slate-400 hover:text-white text-xs font-bold"
              >
                ✕
              </button>
            )}

            {showDropdown && stocks.length > 0 && (
              <div className="absolute z-20 top-full left-0 right-0 mt-1 bg-slate-900 border border-slate-800 rounded shadow-2xl max-h-56 overflow-y-auto">
                {stocks.map((stock) => (
                  <div
                    key={stock.symbol}
                    onClick={() => handleSelectStock(stock)}
                    className="p-2.5 hover:bg-slate-800 cursor-pointer flex justify-between items-center border-b border-slate-850 last:border-0"
                  >
                    <div>
                      <div className="text-sm font-bold text-white font-mono">{stock.symbol}</div>
                      <div className="text-xs text-slate-400">{stock.name}</div>
                    </div>
                    <span className="text-[10px] bg-slate-800 text-slate-400 font-mono px-1.5 py-0.5 rounded border border-slate-700">
                      {stock.exchange}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Date Range Selection */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        {/* Timeframe Dropdown */}
        <div className="space-y-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">Timeframe</label>
          <select
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500"
          >
            <option value="1d">Daily (1d)</option>
            <option value="1h">1 Hour (1h)</option>
            <option value="15m">15 Minutes (15m)</option>
            <option value="5m">5 Minutes (5m)</option>
          </select>
        </div>

        {/* Capital Input */}
        <div className="space-y-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">Capital Per Trade (INR)</label>
          <input
            type="number"
            value={capital}
            onChange={(e) => setCapital(Number(e.target.value))}
            className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:border-blue-500"
          />
        </div>

        {/* Segment Toggle */}
        <div className="space-y-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 block">Segment</label>
          <div className="flex border border-slate-800 rounded overflow-hidden">
            <button
              type="button"
              onClick={() => setSegment("delivery")}
              className={`flex-1 py-2 text-sm font-semibold transition-all ${
                segment === "delivery"
                  ? "bg-blue-600 text-white"
                  : "bg-slate-950 text-slate-400 hover:text-slate-200"
              }`}
            >
              Delivery
            </button>
            <button
              type="button"
              onClick={() => setSegment("intraday")}
              className={`flex-1 py-2 text-sm font-semibold transition-all ${
                segment === "intraday"
                  ? "bg-blue-600 text-white"
                  : "bg-slate-950 text-slate-400 hover:text-slate-200"
              }`}
            >
              Intraday
            </button>
          </div>
        </div>

        {/* Strategy Selector Grouped by Category */}
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Strategies ({selectedStrategies.length} selected)
            </label>
            <div className="flex items-center space-x-3">
              <button
                type="button"
                onClick={onBuildStrategyClick}
                className="text-xs text-emerald-400 hover:underline font-bold"
              >
                + Build Strategy
              </button>
              <span className="text-slate-700 text-xs">|</span>
              <button
                type="button"
                onClick={handleSelectAll}
                className="text-xs text-blue-400 hover:underline"
              >
                {selectedStrategies.length === strategies.length ? "Deselect All" : "Select All"}
              </button>
            </div>
          </div>

          <div className="space-y-3 max-h-72 overflow-y-auto border border-slate-800 p-2.5 rounded bg-slate-950">
            {categoriesOrder.map((cat) => {
              const catStrats = groupedStrategies[cat];
              if (!catStrats || catStrats.length === 0) return null;

              return (
                <div key={cat} className="space-y-1.5">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-blue-400 bg-slate-900/80 px-2 py-1 rounded border border-slate-800/60 flex justify-between items-center">
                    <span>{cat}</span>
                    <span className="text-[10px] text-slate-500 bg-slate-950 px-1.5 py-0.5 rounded font-mono">
                      {catStrats.length}
                    </span>
                  </div>

                  <div className="space-y-1 pl-1">
                    {catStrats.map((strategy) => (
                      <div
                        key={strategy.id}
                        className={`flex items-center justify-between p-2 rounded hover:bg-slate-900 border transition-all ${
                          selectedStrategies.includes(strategy.id)
                            ? "bg-blue-950/20 border-blue-800/40 text-white"
                            : "bg-slate-950/40 border-slate-850 text-slate-300 hover:text-white"
                        }`}
                      >
                        <label className="flex items-center space-x-2.5 cursor-pointer flex-1 min-w-0 pr-2">
                          <input
                            type="checkbox"
                            checked={selectedStrategies.includes(strategy.id)}
                            onChange={() => handleToggleStrategy(strategy.id)}
                            className="accent-blue-500 rounded"
                          />
                          <div className="flex items-center space-x-1.5 truncate">
                            <span className="text-xs font-semibold truncate">{strategy.name}</span>
                            {strategy.is_custom && (
                              <span className="bg-blue-500/20 text-blue-400 border border-blue-500/30 text-[9px] font-bold px-1 rounded uppercase tracking-wider">
                                Custom
                              </span>
                            )}
                            {strategy.is_stub && (
                              <span className="bg-amber-500/20 text-amber-400 border border-amber-500/30 text-[9px] font-bold px-1 rounded uppercase tracking-wider">
                                Needs Intraday/MTF
                              </span>
                            )}
                          </div>
                        </label>

                        <div className="flex items-center space-x-1.5 shrink-0">
                          {/* Info Popover Trigger Icon */}
                          <button
                            type="button"
                            title="Strategy Details & Rules"
                            onClick={(e) => {
                              e.stopPropagation();
                              setPopoverStrategy(strategy);
                            }}
                            className="text-slate-400 hover:text-blue-400 bg-slate-900 border border-slate-800 hover:border-blue-600 rounded-full w-5 h-5 flex items-center justify-center text-[11px] font-mono transition-colors"
                          >
                            ℹ
                          </button>

                          {strategy.is_custom && (
                            <button
                              type="button"
                              onClick={(e) => handleDeleteCustomStrategy(strategy.id, e)}
                              className="text-rose-400 hover:text-rose-300 text-xs font-semibold px-1.5 py-0.5"
                            >
                              Delete
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isLoading || !selectedStock || selectedStrategies.length === 0}
          className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-500 text-white font-bold text-sm uppercase tracking-wider rounded transition-all shadow-lg shadow-blue-900/20"
        >
          {isLoading ? "Running Simulation..." : "Run Backtest"}
        </button>
      </form>

      {/* Info Popover Modal */}
      {popoverStrategy && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl shadow-2xl max-w-md w-full p-6 space-y-4 text-slate-200 animate-in fade-in zoom-in duration-150">
            <div className="flex justify-between items-start border-b border-slate-800 pb-3">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider bg-blue-500/20 text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded">
                  {popoverStrategy.category || "General"}
                </span>
                <h3 className="text-lg font-bold text-white mt-1.5">{popoverStrategy.name}</h3>
              </div>
              <button
                type="button"
                onClick={() => setPopoverStrategy(null)}
                className="text-slate-400 hover:text-white text-base font-bold bg-slate-800 rounded-full w-7 h-7 flex items-center justify-center"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                  Description
                </label>
                <p className="text-slate-300 leading-relaxed bg-slate-950 p-2.5 rounded border border-slate-850">
                  {popoverStrategy.description}
                </p>
              </div>

              {popoverStrategy.rules_text && (
                <div>
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                    Strategy Rules
                  </label>
                  <div className="text-emerald-300 bg-slate-950 p-2.5 rounded border border-slate-850 font-mono leading-normal">
                    {popoverStrategy.rules_text}
                  </div>
                </div>
              )}

              {popoverStrategy.params && Object.keys(popoverStrategy.params).length > 0 && (
                <div>
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                    Default Parameters
                  </label>
                  <div className="grid grid-cols-2 gap-2 bg-slate-950 p-2.5 rounded border border-slate-850 font-mono text-[11px]">
                    {Object.entries(popoverStrategy.params).map(([key, val]) => (
                      <div key={key} className="flex justify-between border-b border-slate-900 pb-1 last:border-0">
                        <span className="text-slate-400">{key}:</span>
                        <span className="text-blue-400 font-bold">{String(val)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <button
              type="button"
              onClick={() => setPopoverStrategy(null)}
              className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-white font-semibold text-xs rounded transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
