import pandas as pd
import numpy as np
from .base import Strategy
import indicators

# Allowed values for validation
ALLOWED_INDICATORS = {
    "ema", "sma", "rsi", "atr", "adx", "plus_di", "minus_di", 
    "supertrend_dir", "bb_upper", "bb_mid", "bb_lower",
    "macd", "macd_signal", "macd_hist",
    "stoch_k", "stoch_d", "stoch_rsi_k", "stoch_rsi_d", "cci", "williams_r",
    "roc", "trix", "trix_signal", "awesome_oscillator", "obv", "mfi", "cmf", "vol_sma",
    "rel_volume", "zscore", "donchian_upper", "donchian_mid", "donchian_lower",
    "keltner_upper", "keltner_mid", "keltner_lower", "linreg_slope", "psar",
    "vi_plus", "vi_minus", "bullish_engulfing", "bearish_engulfing", "hammer",
    "shooting_star", "doji", "inside_bar", "nr7"
}
ALLOWED_FIELDS = {"open", "high", "low", "close", "volume"}
ALLOWED_OPERATORS = {
    "crosses_above", "crosses_below", "greater_than", "less_than", 
    "equals", "not_equals", "flips_up", "flips_down", "is_true", "is_false"
}

def resolve_source_series(df: pd.DataFrame, src: dict) -> pd.Series:
    src_type = src.get("type")
    
    if src_type == "const":
        val = float(src.get("value", 0.0))
        return pd.Series(val, index=df.index)
        
    elif src_type == "price":
        field = src.get("field", "close").lower()
        if field not in ALLOWED_FIELDS:
            raise ValueError(f"Invalid price field: {field}")
        return df[field]
        
    elif src_type == "indicator":
        name = src.get("name", "").lower()
        if name not in ALLOWED_INDICATORS:
            raise ValueError(f"Invalid indicator name: {name}")
        params = src.get("params", {})
        
        if name == "ema":
            n = int(params.get("n", params.get("period", 9)))
            return indicators.ema(df["close"], n)
        elif name == "sma":
            n = int(params.get("n", params.get("period", 14)))
            return indicators.sma(df["close"], n)
        elif name == "rsi":
            n = int(params.get("n", params.get("period", 14)))
            return indicators.rsi(df["close"], n)
        elif name == "atr":
            n = int(params.get("n", params.get("period", 14)))
            return indicators.atr(df, n)
        elif name in ("adx", "plus_di", "minus_di"):
            n = int(params.get("n", params.get("period", 14)))
            adx_val, plus_di_val, minus_di_val = indicators.adx(df, n)
            if name == "adx":
                return adx_val
            elif name == "plus_di":
                return plus_di_val
            else:
                return minus_di_val
        elif name == "supertrend_dir":
            period = int(params.get("period", 10))
            multiplier = float(params.get("multiplier", 3.0))
            st_line, st_dir = indicators.supertrend(df, period, multiplier)
            return st_dir
        elif name in ("bb_upper", "bb_mid", "bb_lower"):
            n = int(params.get("n", params.get("period", 20)))
            k = float(params.get("k", params.get("std_dev", 2.0)))
            upper, mid, lower = indicators.bollinger(df["close"], n, k)
            if name == "bb_upper":
                return upper
            elif name == "bb_mid":
                return mid
            else:
                return lower
        elif name in ("macd", "macd_signal", "macd_hist"):
            fast = int(params.get("fast", 12))
            slow = int(params.get("slow", 26))
            signal = int(params.get("signal", 9))
            m_line, s_line, hist = indicators.macd(df["close"], fast, slow, signal)
            if name == "macd":
                return m_line
            elif name == "macd_signal":
                return s_line
            else:
                return hist
        elif name in ("stoch_k", "stoch_d"):
            k_period = int(params.get("k", 14))
            d_period = int(params.get("d", 3))
            smooth = int(params.get("smooth", 3))
            sk, sd = indicators.stochastic(df, k_period, d_period, smooth)
            return sk if name == "stoch_k" else sd
        elif name in ("stoch_rsi_k", "stoch_rsi_d"):
            n = int(params.get("n", 14))
            k = int(params.get("k", 3))
            d = int(params.get("d", 3))
            srk, srd = indicators.stoch_rsi(df["close"], n, k, d)
            return srk if name == "stoch_rsi_k" else srd
        elif name == "cci":
            n = int(params.get("n", 20))
            return indicators.cci(df, n)
        elif name == "williams_r":
            n = int(params.get("n", 14))
            return indicators.williams_r(df, n)
        elif name == "roc":
            n = int(params.get("n", 12))
            return indicators.roc(df["close"], n)
        elif name in ("trix", "trix_signal"):
            n = int(params.get("n", 15))
            t_line, s_line = indicators.trix(df["close"], n)
            return t_line if name == "trix" else s_line
        elif name == "awesome_oscillator":
            return indicators.awesome_oscillator(df)
        elif name == "obv":
            return indicators.obv(df)
        elif name == "mfi":
            n = int(params.get("n", 14))
            return indicators.mfi(df, n)
        elif name == "cmf":
            n = int(params.get("n", 20))
            return indicators.cmf(df, n)
        elif name == "vol_sma":
            n = int(params.get("n", 20))
            return indicators.vol_sma(df["volume"], n)
        elif name == "rel_volume":
            n = int(params.get("n", 20))
            return indicators.rel_volume(df["volume"], n)
        elif name == "zscore":
            n = int(params.get("n", 20))
            return indicators.zscore(df["close"], n)
        elif name in ("donchian_upper", "donchian_mid", "donchian_lower"):
            n = int(params.get("n", 20))
            u, m, l = indicators.donchian(df, n)
            return u if name == "donchian_upper" else (m if name == "donchian_mid" else l)
        elif name in ("keltner_upper", "keltner_mid", "keltner_lower"):
            ema_n = int(params.get("ema_n", 20))
            atr_n = int(params.get("atr_n", 10))
            mult = float(params.get("mult", 2.0))
            u, m, l = indicators.keltner(df, ema_n, atr_n, mult)
            return u if name == "keltner_upper" else (m if name == "keltner_mid" else l)
        elif name == "linreg_slope":
            n = int(params.get("n", 20))
            return indicators.linreg_slope(df["close"], n)
        elif name == "psar":
            af = float(params.get("af", 0.02))
            max_af = float(params.get("max_af", 0.2))
            return indicators.parabolic_sar(df, af, max_af)
        elif name in ("vi_plus", "vi_minus"):
            n = int(params.get("n", 14))
            vp, vm = indicators.vortex(df, n)
            return vp if name == "vi_plus" else vm
        elif name == "bullish_engulfing":
            return indicators.bullish_engulfing(df).astype(float)
        elif name == "bearish_engulfing":
            return indicators.bearish_engulfing(df).astype(float)
        elif name == "hammer":
            return indicators.hammer(df).astype(float)
        elif name == "shooting_star":
            return indicators.shooting_star(df).astype(float)
        elif name == "doji":
            return indicators.doji(df).astype(float)
        elif name == "inside_bar":
            return indicators.inside_bar(df).astype(float)
        elif name == "nr7":
            return indicators.nr7(df).astype(float)
    else:
        raise ValueError(f"Unknown source type: {src_type}")

def get_source_description(src: dict, ts=None, series=None) -> str:
    src_type = src.get("type")
    
    val_str = ""
    if ts is not None and series is not None:
        try:
            val_str = f"={series[ts]:.2f}"
        except Exception:
            pass

    if src_type == "const":
        return str(src.get("value", 0.0))
    elif src_type == "price":
        return f"{src.get('field', 'Close').capitalize()}{val_str}"
    elif src_type == "indicator":
        name = src.get("name", "").upper()
        params = src.get("params", {})
        param_strs = [f"{k}={v}" for k, v in params.items()]
        params_desc = f"({','.join(param_strs)})" if param_strs else ""
        return f"{name}{params_desc}{val_str}"
    return "Unknown"

def evaluate_condition(df: pd.DataFrame, cond: dict) -> tuple[pd.Series, str]:
    left_spec = cond.get("left")
    op = cond.get("op", "").lower()
    right_spec = cond.get("right")
    
    if op not in ALLOWED_OPERATORS:
        raise ValueError(f"Invalid operator: {op}")
        
    left_series = resolve_source_series(df, left_spec)
    
    # is_true / is_false / flips_up / flips_down only need the left series
    if op == "is_true":
        res = left_series.astype(bool)
        def build_desc(ts):
            l_desc = get_source_description(left_spec, ts, left_series)
            return f"{l_desc} is TRUE"
        return res, build_desc

    elif op == "is_false":
        res = ~left_series.astype(bool)
        def build_desc(ts):
            l_desc = get_source_description(left_spec, ts, left_series)
            return f"{l_desc} is FALSE"
        return res, build_desc

    elif op == "flips_up":
        res = (left_series > left_series.shift(1)) & (left_series.shift(1) <= 0) & (left_series > 0)
        # Fallback for non-zero binary transitions (e.g. going from -1 to 1)
        res = res | ((left_series > left_series.shift(1)) & (left_series.shift(1) == -1))
        
        def build_desc(ts):
            l_desc = get_source_description(left_spec, ts, left_series)
            return f"{l_desc} flipped UP"
        return res, build_desc
        
    elif op == "flips_down":
        res = (left_series < left_series.shift(1)) & (left_series.shift(1) >= 0) & (left_series < 0)
        res = res | ((left_series < left_series.shift(1)) & (left_series.shift(1) == 1))
        
        def build_desc(ts):
            l_desc = get_source_description(left_spec, ts, left_series)
            return f"{l_desc} flipped DOWN"
        return res, build_desc

    # For other operators we need the right series
    if not right_spec:
        raise ValueError(f"Right source required for operator {op}")
        
    right_series = resolve_source_series(df, right_spec)
    
    if op == "greater_than":
        res = left_series > right_series
        op_name = ">"
    elif op == "less_than":
        res = left_series < right_series
        op_name = "<"
    elif op == "equals":
        res = left_series == right_series
        op_name = "=="
    elif op == "not_equals":
        res = left_series != right_series
        op_name = "!="
    elif op == "crosses_above":
        res = (left_series > right_series) & (left_series.shift(1) <= right_series.shift(1))
        op_name = "crossed ABOVE"
    elif op == "crosses_below":
        res = (left_series < right_series) & (left_series.shift(1) >= right_series.shift(1))
        op_name = "crossed BELOW"
    else:
        raise ValueError(f"Unknown operator: {op}")
        
    def build_desc(ts):
        l_desc = get_source_description(left_spec, ts, left_series)
        r_desc = get_source_description(right_spec, ts, right_series)
        return f"{l_desc} {op_name} {r_desc}"
        
    return res, build_desc

class SpecStrategy(Strategy):
    def __init__(self, spec: dict):
        self.name = spec.get("name", "Custom Spec Strategy")
        self.spec = spec
        
        # Risk settings from spec
        risk = spec.get("risk", {})
        self.sl_atr_mult = float(risk.get("sl_atr_mult", 2.0))
        self.rr_ratio = float(risk.get("rr_ratio", 2.0))
        self.allow_long = bool(risk.get("allow_long", True))
        self.allow_short = bool(risk.get("allow_short", True))
        self.atr_period = int(risk.get("atr_period", 14))

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        out = self._blank(df)
        
        # Evaluate entry_long
        long_conds = self.spec.get("entry_long", [])
        long_series_list = []
        long_desc_funcs = []
        
        for cond in long_conds:
            series, desc_func = evaluate_condition(df, cond)
            long_series_list.append(series)
            long_desc_funcs.append(desc_func)
            
        if long_series_list:
            combined_long = long_series_list[0]
            for s in long_series_list[1:]:
                combined_long = combined_long & s
        else:
            combined_long = pd.Series(False, index=df.index)

        # Evaluate entry_short
        short_conds = self.spec.get("entry_short", [])
        short_series_list = []
        short_desc_funcs = []
        
        for cond in short_conds:
            series, desc_func = evaluate_condition(df, cond)
            short_series_list.append(series)
            short_desc_funcs.append(desc_func)
            
        if short_series_list:
            combined_short = short_series_list[0]
            for s in short_series_list[1:]:
                combined_short = combined_short & s
        else:
            combined_short = pd.Series(False, index=df.index)

        # Evaluate exit
        exit_conds = self.spec.get("exit", [])
        exit_series_list = []
        exit_desc_funcs = []
        
        for cond in exit_conds:
            series, desc_func = evaluate_condition(df, cond)
            exit_series_list.append(series)
            exit_desc_funcs.append(desc_func)
            
        if exit_series_list:
            combined_exit = exit_series_list[0]
            for s in exit_series_list[1:]:
                combined_exit = combined_exit & s
        else:
            combined_exit = pd.Series(False, index=df.index)

        # Populate outputs
        out["enter_long"] = combined_long
        out["enter_short"] = combined_short
        out["exit"] = combined_exit

        # Generate reasons for bars where signals trigger
        for ts in df.index:
            reasons = []
            if combined_long[ts]:
                reasons.extend([f(ts) for f in long_desc_funcs])
            if combined_short[ts]:
                reasons.extend([f(ts) for f in short_desc_funcs])
            if combined_exit[ts]:
                reasons.extend([f(ts) for f in exit_desc_funcs])
                
            if reasons:
                out.at[ts, "reason"] = " AND ".join(reasons)
                
        return out
