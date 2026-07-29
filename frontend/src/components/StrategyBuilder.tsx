"use client";

import React, { useState } from "react";

interface StrategyBuilderProps {
  apiBaseUrl: string;
  onClose: () => void;
  onSaveSuccess: () => void;
}

const INDICATORS = [
  { id: "ema", name: "Exponential Moving Average (EMA)", params: [{ name: "period", type: "number", default: 9 }] },
  { id: "sma", name: "Simple Moving Average (SMA)", params: [{ name: "period", type: "number", default: 14 }] },
  { id: "rsi", name: "Relative Strength Index (RSI)", params: [{ name: "period", type: "number", default: 14 }] },
  { id: "atr", name: "Average True Range (ATR)", params: [{ name: "period", type: "number", default: 14 }] },
  { id: "adx", name: "Average Directional Index (ADX)", params: [{ name: "period", type: "number", default: 14 }] },
  { id: "plus_di", name: "+DI (Directional Indicator)", params: [{ name: "period", type: "number", default: 14 }] },
  { id: "minus_di", name: "-DI (Directional Indicator)", params: [{ name: "period", type: "number", default: 14 }] },
  { id: "supertrend_dir", name: "SuperTrend Direction", params: [{ name: "period", type: "number", default: 10 }, { name: "multiplier", type: "number", default: 3.0 }] },
  { id: "bb_upper", name: "Bollinger Band Upper", params: [{ name: "period", type: "number", default: 20 }, { name: "std_dev", type: "number", default: 2.0 }] },
  { id: "bb_mid", name: "Bollinger Band Mid", params: [{ name: "period", type: "number", default: 20 }, { name: "std_dev", type: "number", default: 2.0 }] },
  { id: "bb_lower", name: "Bollinger Band Lower", params: [{ name: "period", type: "number", default: 20 }, { name: "std_dev", type: "number", default: 2.0 }] },
  { id: "macd", name: "MACD Line", params: [{ name: "fast", type: "number", default: 12 }, { name: "slow", type: "number", default: 26 }] },
  { id: "macd_signal", name: "MACD Signal Line", params: [{ name: "fast", type: "number", default: 12 }, { name: "slow", type: "number", default: 26 }, { name: "signal", type: "number", default: 9 }] },
  { id: "macd_hist", name: "MACD Histogram", params: [{ name: "fast", type: "number", default: 12 }, { name: "slow", type: "number", default: 26 }, { name: "signal", type: "number", default: 9 }] },
  { id: "stoch_k", name: "Stochastic %K", params: [{ name: "k", type: "number", default: 14 }] },
  { id: "stoch_d", name: "Stochastic %D", params: [{ name: "k", type: "number", default: 14 }, { name: "d", type: "number", default: 3 }] },
  { id: "stoch_rsi_k", name: "StochRSI %K", params: [{ name: "n", type: "number", default: 14 }] },
  { id: "stoch_rsi_d", name: "StochRSI %D", params: [{ name: "n", type: "number", default: 14 }, { name: "d", type: "number", default: 3 }] },
  { id: "cci", name: "Commodity Channel Index (CCI)", params: [{ name: "period", type: "number", default: 20 }] },
  { id: "williams_r", name: "Williams %R", params: [{ name: "period", type: "number", default: 14 }] },
  { id: "roc", name: "Rate of Change (ROC)", params: [{ name: "period", type: "number", default: 12 }] },
  { id: "trix", name: "TRIX Line", params: [{ name: "period", type: "number", default: 15 }] },
  { id: "awesome_oscillator", name: "Awesome Oscillator (AO)", params: [] },
  { id: "obv", name: "On-Balance Volume (OBV)", params: [] },
  { id: "mfi", name: "Money Flow Index (MFI)", params: [{ name: "period", type: "number", default: 14 }] },
  { id: "cmf", name: "Chaikin Money Flow (CMF)", params: [{ name: "period", type: "number", default: 20 }] },
  { id: "rel_volume", name: "Relative Volume", params: [{ name: "period", type: "number", default: 20 }] },
  { id: "zscore", name: "Z-Score", params: [{ name: "period", type: "number", default: 20 }] },
  { id: "donchian_upper", name: "Donchian Upper High", params: [{ name: "period", type: "number", default: 20 }] },
  { id: "donchian_lower", name: "Donchian Lower Low", params: [{ name: "period", type: "number", default: 20 }] },
  { id: "keltner_upper", name: "Keltner Upper", params: [{ name: "period", type: "number", default: 20 }] },
  { id: "keltner_lower", name: "Keltner Lower", params: [{ name: "period", type: "number", default: 20 }] },
  { id: "linreg_slope", name: "Linear Regression Slope", params: [{ name: "period", type: "number", default: 20 }] },
  { id: "psar", name: "Parabolic SAR Line", params: [] },
  { id: "vi_plus", name: "Vortex VI+", params: [{ name: "period", type: "number", default: 14 }] },
  { id: "vi_minus", name: "Vortex VI-", params: [{ name: "period", type: "number", default: 14 }] },
  { id: "bullish_engulfing", name: "Bullish Engulfing Pattern", params: [] },
  { id: "bearish_engulfing", name: "Bearish Engulfing Pattern", params: [] },
  { id: "hammer", name: "Hammer Rejection Pattern", params: [] },
  { id: "shooting_star", name: "Shooting Star Pattern", params: [] },
  { id: "doji", name: "Doji Candle Pattern", params: [] },
  { id: "inside_bar", name: "Inside Bar Pattern", params: [] },
  { id: "nr7", name: "NR7 Range Pattern", params: [] }
];

const FIELDS = ["close", "open", "high", "low"];

const OPERATORS = [
  { id: "crosses_above", name: "Crosses Above" },
  { id: "crosses_below", name: "Crosses Below" },
  { id: "greater_than", name: "Greater Than" },
  { id: "less_than", name: "Less Than" },
  { id: "equals", name: "Equals" },
  { id: "not_equals", name: "Not Equals" },
  { id: "flips_up", name: "Flips Up" },
  { id: "flips_down", name: "Flips Down" },
  { id: "is_true", name: "Is True" },
  { id: "is_false", name: "Is False" }
];

export default function StrategyBuilder({ apiBaseUrl, onClose, onSaveSuccess }: StrategyBuilderProps) {
  const [name, setName] = useState("");
  const [slAtrMult, setSlAtrMult] = useState(2.0);
  const [rrRatio, setRrRatio] = useState(2.0);
  const [allowLong, setAllowLong] = useState(true);
  const [allowShort, setAllowShort] = useState(true);
  const [atrPeriod, setAtrPeriod] = useState(14);

  const [entryLong, setEntryLong] = useState<any[]>([]);
  const [entryShort, setEntryShort] = useState<any[]>([]);
  const [exitRule, setExitRule] = useState<any[]>([]);
  
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const createDefaultSource = () => ({
    type: "indicator",
    name: "ema",
    field: "close",
    value: 50,
    params: { period: 9 },
  });

  const handleAddCondition = (type: "long" | "short" | "exit") => {
    const newCond = {
      left: createDefaultSource(),
      op: "crosses_above",
      right: createDefaultSource(),
    };
    if (type === "long") setEntryLong([...entryLong, newCond]);
    else if (type === "short") setEntryShort([...entryShort, newCond]);
    else setExitRule([...exitRule, newCond]);
  };

  const handleRemoveCondition = (type: "long" | "short" | "exit", index: number) => {
    if (type === "long") setEntryLong(entryLong.filter((_, i) => i !== index));
    else if (type === "short") setEntryShort(entryShort.filter((_, i) => i !== index));
    else setExitRule(exitRule.filter((_, i) => i !== index));
  };

  const handleUpdateSource = (type: "long" | "short" | "exit", condIndex: number, side: "left" | "right", field: string, value: any) => {
    const updateList = (list: any[]) => {
      return list.map((cond, idx) => {
        if (idx !== condIndex) return cond;
        const newSide = { ...cond[side] };
        
        if (field === "type") {
          newSide.type = value;
          if (value === "indicator") {
            newSide.name = "ema";
            newSide.params = { period: 9 };
          } else if (value === "price") {
            newSide.field = "close";
          } else {
            newSide.value = 50;
          }
        } else if (field === "name") {
          newSide.name = value;
          const found = INDICATORS.find((i) => i.id === value);
          newSide.params = {};
          found?.params.forEach((p) => {
            newSide.params[p.name] = p.default;
          });
        } else if (field === "param") {
          newSide.params = { ...newSide.params, [value.name]: Number(value.val) };
        } else {
          newSide[field] = value;
        }

        return { ...cond, [side]: newSide };
      });
    };

    if (type === "long") setEntryLong(updateList(entryLong));
    else if (type === "short") setEntryShort(updateList(entryShort));
    else setExitRule(updateList(exitRule));
  };

  const handleUpdateOperator = (type: "long" | "short" | "exit", condIndex: number, op: string) => {
    const updateList = (list: any[]) => {
      return list.map((cond, idx) => {
        if (idx !== condIndex) return cond;
        // If flips_up/down, clear right side
        const right = ["flips_up", "flips_down"].includes(op) ? undefined : cond.right || createDefaultSource();
        return { ...cond, op, right };
      });
    };
    if (type === "long") setEntryLong(updateList(entryLong));
    else if (type === "short") setEntryShort(updateList(entryShort));
    else setExitRule(updateList(exitRule));
  };

  const getSourceText = (src: any) => {
    if (!src) return "";
    if (src.type === "const") return src.value;
    if (src.type === "price") return src.field.toUpperCase();
    if (src.type === "indicator") {
      const pStr = Object.entries(src.params || {}).map(([k, v]) => `${k}=${v}`).join(", ");
      return `${src.name.toUpperCase()}(${pStr})`;
    }
    return "";
  };

  const getConditionText = (cond: any) => {
    const leftText = getSourceText(cond.left);
    const opText = OPERATORS.find((o) => o.id === cond.op)?.name.toUpperCase() || cond.op;
    const rightText = cond.right ? getSourceText(cond.right) : "";
    return `${leftText} ${opText} ${rightText}`.trim();
  };

  const getRulesPreview = (list: any[]) => {
    if (list.length === 0) return "No conditions defined (defaults to false)";
    return list.map(getConditionText).join(" AND ");
  };

  const handleSave = async () => {
    if (!name.trim()) {
      setErrorMsg("Strategy Name is required.");
      return;
    }
    setIsSaving(true);
    setErrorMsg(null);

    const payload = {
      name,
      entry_long: entryLong,
      entry_short: entryShort,
      exit: exitRule,
      risk: {
        sl_atr_mult: slAtrMult,
        rr_ratio: rrRatio,
        allow_long: allowLong,
        allow_short: allowShort,
        atr_period: atrPeriod,
      },
    };

    try {
      const res = await fetch(`${apiBaseUrl}/strategies`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail?.[0]?.msg || errData.detail || "Failed to save strategy spec.");
      }

      onSaveSuccess();
      onClose();
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const renderSourceForm = (type: "long" | "short" | "exit", condIndex: number, side: "left" | "right", src: any) => {
    if (!src) return null;
    return (
      <div className="flex flex-wrap gap-2 items-center bg-slate-950 p-2.5 rounded border border-slate-800">
        <select
          value={src.type}
          onChange={(e) => handleUpdateSource(type, condIndex, side, "type", e.target.value)}
          className="bg-slate-900 border border-slate-800 text-slate-200 rounded px-2 py-1 text-xs"
        >
          <option value="indicator">Indicator</option>
          <option value="price">Price Field</option>
          <option value="const">Constant</option>
        </select>

        {src.type === "indicator" && (
          <>
            <select
              value={src.name}
              onChange={(e) => handleUpdateSource(type, condIndex, side, "name", e.target.value)}
              className="bg-slate-900 border border-slate-800 text-slate-200 rounded px-2 py-1 text-xs"
            >
              {INDICATORS.map((ind) => (
                <option key={ind.id} value={ind.id}>{ind.name}</option>
              ))}
            </select>
            {INDICATORS.find((ind) => ind.id === src.name)?.params.map((p) => (
              <div key={p.name} className="flex items-center space-x-1">
                <span className="text-[10px] text-slate-500 uppercase">{p.name}:</span>
                <input
                  type="number"
                  value={src.params?.[p.name] ?? p.default}
                  onChange={(e) => handleUpdateSource(type, condIndex, side, "param", { name: p.name, val: e.target.value })}
                  className="bg-slate-900 border border-slate-800 text-slate-200 rounded px-1.5 py-0.5 text-xs w-14 text-center font-mono"
                />
              </div>
            ))}
          </>
        )}

        {src.type === "price" && (
          <select
            value={src.field}
            onChange={(e) => handleUpdateSource(type, condIndex, side, "field", e.target.value)}
            className="bg-slate-900 border border-slate-800 text-slate-200 rounded px-2 py-1 text-xs uppercase font-mono"
          >
            {FIELDS.map((f) => (
              <option key={f} value={f}>{f}</option>
            ))}
          </select>
        )}

        {src.type === "const" && (
          <input
            type="number"
            value={src.value}
            onChange={(e) => handleUpdateSource(type, condIndex, side, "value", Number(e.target.value))}
            className="bg-slate-900 border border-slate-800 text-slate-200 rounded px-2 py-1 text-xs w-20 font-mono"
          />
        )}
      </div>
    );
  };

  const renderConditionList = (type: "long" | "short" | "exit", list: any[]) => {
    return (
      <div className="space-y-3">
        {list.map((cond, idx) => (
          <div key={idx} className="flex flex-col lg:flex-row gap-3 items-start lg:items-center bg-slate-900/60 p-4 border border-slate-800/80 rounded relative">
            <button
              type="button"
              onClick={() => handleRemoveCondition(type, idx)}
              className="absolute top-2 right-2 text-rose-400 hover:text-rose-300 text-xs"
            >
              Remove
            </button>
            
            {/* Left Source */}
            {renderSourceForm(type, idx, "left", cond.left)}

            {/* Operator */}
            <select
              value={cond.op}
              onChange={(e) => handleUpdateOperator(type, idx, e.target.value)}
              className="bg-slate-950 border border-slate-800 text-blue-400 rounded px-2 py-1 text-xs font-semibold uppercase"
            >
              {OPERATORS.map((op) => (
                <option key={op.id} value={op.id}>{op.name}</option>
              ))}
            </select>

            {/* Right Source */}
            {cond.right && renderSourceForm(type, idx, "right", cond.right)}
          </div>
        ))}
        <button
          type="button"
          onClick={() => handleAddCondition(type)}
          className="text-xs text-blue-400 hover:text-blue-300 font-semibold flex items-center space-x-1.5"
        >
          <span>+ Add Condition</span>
        </button>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 w-full max-w-4xl rounded-xl shadow-2xl overflow-hidden flex flex-col my-8 max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/50">
          <h2 className="text-xl font-bold text-white">No-Code Strategy Builder</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-lg font-bold">&times;</button>
        </div>

        {/* Scrollable Form Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 text-slate-300">
          
          {/* Strategy Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold uppercase text-slate-400">Strategy Name</label>
              <input
                type="text"
                placeholder="e.g. EMA 5 Crossover 20"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 placeholder-slate-700 focus:outline-none focus:border-blue-500"
              />
            </div>
            
            {/* Risk Settings */}
            <div className="grid grid-cols-3 gap-2">
              <div className="space-y-1">
                <label className="text-[10px] font-semibold uppercase text-slate-400">SL ATR Mult</label>
                <input
                  type="number"
                  step="0.1"
                  value={slAtrMult}
                  onChange={(e) => setSlAtrMult(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 font-mono text-center focus:outline-none focus:border-blue-500"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-semibold uppercase text-slate-400">R:R Ratio</label>
                <input
                  type="number"
                  step="0.1"
                  value={rrRatio}
                  onChange={(e) => setRrRatio(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 font-mono text-center focus:outline-none focus:border-blue-500"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-semibold uppercase text-slate-400">ATR Period</label>
                <input
                  type="number"
                  value={atrPeriod}
                  onChange={(e) => setAtrPeriod(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 font-mono text-center focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <label className="flex items-center space-x-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={allowLong}
                onChange={() => setAllowLong(!allowLong)}
                className="accent-blue-500"
              />
              <span>Allow Long Trades</span>
            </label>
            <label className="flex items-center space-x-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={allowShort}
                onChange={() => setAllowShort(!allowShort)}
                className="accent-blue-500"
              />
              <span>Allow Short Trades</span>
            </label>
          </div>

          {/* Rules Sections */}
          <div className="border-t border-slate-800 pt-4 space-y-6">
            {/* Long Entry Conditions */}
            <div className="space-y-2">
              <h3 className="text-sm font-bold text-emerald-400 uppercase tracking-wider">Long Entry Rules</h3>
              {renderConditionList("long", entryLong)}
            </div>

            {/* Short Entry Conditions */}
            <div className="space-y-2">
              <h3 className="text-sm font-bold text-amber-400 uppercase tracking-wider">Short Entry Rules</h3>
              {renderConditionList("short", entryShort)}
            </div>

            {/* Exit Conditions */}
            <div className="space-y-2">
              <h3 className="text-sm font-bold text-rose-400 uppercase tracking-wider">Exit Rules (Optional)</h3>
              {renderConditionList("exit", exitRule)}
            </div>
          </div>

          {/* Rule Sentence Live Preview */}
          <div className="bg-slate-950 border border-slate-850 p-4 rounded-lg space-y-2">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Live Preview (Rule Sentences)</h4>
            <div className="text-xs space-y-1 font-mono text-slate-300">
              <div><span className="text-emerald-400 font-bold">LONG ENTRY:</span> {getRulesPreview(entryLong)}</div>
              <div className="mt-1"><span className="text-amber-400 font-bold">SHORT ENTRY:</span> {getRulesPreview(entryShort)}</div>
              <div className="mt-1"><span className="text-rose-400 font-bold">EXIT:</span> {getRulesPreview(exitRule)}</div>
            </div>
          </div>

          {errorMsg && (
            <div className="bg-rose-950/40 border border-rose-800 text-rose-300 text-xs p-3 rounded-lg flex items-center space-x-2">
              <span>⚠️</span>
              <span>{errorMsg}</span>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-900/50 flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-slate-700 hover:border-slate-500 hover:text-white rounded text-sm text-slate-300 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving || !name.trim()}
            className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-500 text-white rounded font-bold text-sm shadow-lg transition-colors flex items-center space-x-2"
          >
            {isSaving ? <span>Saving...</span> : <span>Save Strategy</span>}
          </button>
        </div>
      </div>
    </div>
  );
}
