import numpy as np
import pandas as pd

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    c = df['Close'].astype(float)
    h = df['High'].astype(float)
    l = df['Low'].astype(float)
    v = df['Volume'].astype(float)

    # --- Trend ---
    df['EMA20']  = c.ewm(span=20, adjust=False).mean()
    df['EMA50']  = c.ewm(span=50, adjust=False).mean()
    df['EMA200'] = c.ewm(span=200, adjust=False).mean()

    # --- Momentum ---
    exp1 = c.ewm(span=12, adjust=False).mean()
    exp2 = c.ewm(span=26, adjust=False).mean()
    df['MACD']   = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_hist'] = df['MACD'] - df['Signal']  # histogram

    delta = c.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / (loss + 1e-9)
    df['RSI'] = 100 - (100 / (1 + rs))

    # --- Stochastic %K / %D (entry timing) ---
    low14  = l.rolling(14).min()
    high14 = h.rolling(14).max()
    df['Stoch_K'] = 100 * (c - low14) / (high14 - low14 + 1e-9)
    df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()

    # --- ADX (trend strength) ---
    tr   = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    dm_p = (h - h.shift()).clip(lower=0)
    dm_m = (l.shift() - l).clip(lower=0)
    dm_p[dm_p < dm_m] = 0
    dm_m[dm_m < dm_p] = 0
    atr14  = tr.rolling(14).mean()
    di_p   = 100 * dm_p.rolling(14).mean() / (atr14 + 1e-9)
    di_m   = 100 * dm_m.rolling(14).mean() / (atr14 + 1e-9)
    dx     = 100 * (di_p - di_m).abs() / (di_p + di_m + 1e-9)
    df['ADX']  = dx.rolling(14).mean()
    df['DI_p'] = di_p
    df['DI_m'] = di_m

    # --- Bollinger Bands ---
    bb_mid       = c.rolling(20).mean()
    bb_std       = c.rolling(20).std()
    df['BB_upper'] = bb_mid + 2 * bb_std
    df['BB_lower'] = bb_mid - 2 * bb_std
    df['BB_pct']   = (c - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'] + 1e-9)
    df['BB_width']  = (df['BB_upper'] - df['BB_lower']) / (bb_mid + 1e-9)
    # Bollinger squeeze = width ต่ำกว่า 20-period median
    df['BB_squeeze'] = df['BB_width'] < df['BB_width'].rolling(20).median()

    # --- Volatility ---
    df['ATR']     = atr14
    df['ATR_pct'] = df['ATR'] / (c + 1e-9)

    # --- Volume ---
    df['Vol_MA']    = v.rolling(20).mean()
    df['Vol_Spike'] = v > df['Vol_MA'] * 1.5

    # --- Breakout (52-week high proximity) ---
    df['HH_20']    = c.rolling(20).max()
    df['HH_52w']   = c.rolling(252).max()
    df['Breakout'] = c >= df['HH_20']
    df['Near52w']  = c >= df['HH_52w'] * 0.95   # ภายใน 5% ของ 52w high

    # --- RSI Divergence (bearish: ราคาสูงขึ้นแต่ RSI ต่ำลง) ---
    price_up = c.diff(10) > 0
    rsi_down = df['RSI'].diff(10) < -5
    df['RSI_bear_div'] = price_up & rsi_down

    # --- Slope ---
    df['Slope50'] = df['EMA50'].diff(5)

    # --- Support levels (swing low ใน 20 วัน) ---
    df['SwingLow20'] = l.rolling(20).min()

    return df.dropna()


def hard_filter(r: pd.Series) -> bool:
    """กรองคุณภาพขั้นต่ำ — fail any = reject"""
    if float(r['Close']) < float(r['EMA200']):
        return False                        # downtrend ระยะยาว
    if float(r['ATR_pct']) > 0.08:
        return False                        # volatile เกินไป
    if float(r['RSI']) > 78:
        return False                        # overbought มาก
    if float(r['RSI']) < 30:
        return False                        # ร่วงแรง อย่าเพิ่งเข้า
    if float(r['ADX']) < 15:
        return False                        # ไม่มี trend เลย (sideways)
    return True


def score_row(r: pd.Series, rs_vs_spy: float = 0.0):
    score = 0
    reasons = []
    penalties = []

    # ── Trend (35 pts) ──────────────────────────────────────
    if float(r['Close']) > float(r['EMA50']) > float(r['EMA200']):
        score += 20; reasons.append("Uptrend EMA aligned")
    elif float(r['Close']) > float(r['EMA200']):
        score += 8                          # partial trend

    if float(r['ADX']) > 25 and float(r['DI_p']) > float(r['DI_m']):
        score += 15; reasons.append(f"Strong trend ADX={r['ADX']:.0f}")
    elif float(r['ADX']) > 20:
        score += 7

    # ── Momentum (25 pts) ───────────────────────────────────
    if float(r['MACD']) > float(r['Signal']) and float(r['MACD_hist']) > 0:
        score += 12; reasons.append("MACD bullish")

    rsi = float(r['RSI'])
    if 50 < rsi < 65:
        score += 10; reasons.append(f"RSI healthy {rsi:.0f}")
    elif 45 < rsi <= 50:
        score += 5
    elif rsi >= 70:
        score -= 5; penalties.append("RSI high")

    stoch_k = float(r.get('Stoch_K', 50))
    stoch_d = float(r.get('Stoch_D', 50))
    if stoch_k > stoch_d and 40 < stoch_k < 80:
        score += 8; reasons.append("Stochastic bullish cross")
    elif stoch_k > 80:
        score -= 3; penalties.append("Stochastic overbought")

    # ── Breakout + Bollinger (20 pts) ────────────────────────
    if bool(r.get('Breakout', False)):
        score += 12; reasons.append("20-day breakout")
    if bool(r.get('Near52w', False)):
        score += 5; reasons.append("Near 52w high")
    if bool(r.get('BB_squeeze', False)) and bool(r.get('Breakout', False)):
        score += 8; reasons.append("BB squeeze breakout")

    bb_pct = float(r.get('BB_pct', 0.5))
    if bb_pct > 0.8:
        score -= 4; penalties.append("Upper BB extended")

    # ── Volume (10 pts) ──────────────────────────────────────
    if bool(r.get('Vol_Spike', False)):
        score += 10; reasons.append("Volume surge")

    # ── Slope + RS (10 pts) ──────────────────────────────────
    if float(r.get('Slope50', 0)) > 0:
        score += 5
    if rs_vs_spy > 0.05:
        score += 10; reasons.append("Outperform SPY >5%")
    elif rs_vs_spy > 0:
        score += 5

    # ── Penalties ────────────────────────────────────────────
    if bool(r.get('RSI_bear_div', False)):
        score -= 10; penalties.append("Bearish RSI divergence")

    return float(score), reasons, penalties


def decision(score: float) -> str:
    if score >= 75:   return "STRONG BUY"
    elif score >= 58: return "BUY"
    elif score >= 42: return "WAIT"
    return "NO TRADE"


def risk_model(r: pd.Series):
    """Dynamic TP/SL ตาม volatility regime"""
    atr   = float(r['ATR'])
    entry = float(r['Close'])
    swing_low = float(r.get('SwingLow20', entry - atr * 1.5))

    atr_pct = float(r.get('ATR_pct', 0.02))

    # ปรับ multiplier ตาม regime
    if atr_pct < 0.015:       # low vol
        tp_mult, sl_mult = 3.0, 1.0
    elif atr_pct < 0.035:     # normal
        tp_mult, sl_mult = 2.5, 1.2
    else:                      # high vol
        tp_mult, sl_mult = 2.0, 1.5

    tp = entry + atr * tp_mult
    # SL = max(ATR-based, swing low)
    sl_atr  = entry - atr * sl_mult
    sl = max(sl_atr, swing_low * 0.995)  # อย่าให้ต่ำกว่า swing low มาก

    rr = (tp - entry) / max(entry - sl, 1e-9)
    return float(tp), float(sl), float(rr)


def backtest_winrate(df: pd.DataFrame):
    """
    คืนค่า: winrate, avg_profit_pct, avg_loss_pct, expectancy
    """
    wins = 0; total = 0
    profits = []; losses = []

    MAX_HOLD = 15  # force exit หลัง 15 วัน

    for i in range(60, len(df) - MAX_HOLD):
        r = df.iloc[i]
        score, _, _ = score_row(r, 0.0)
        if score < 58:
            continue

        entry   = float(r['Close'])
        atr     = float(r['ATR'])
        atr_pct = float(r.get('ATR_pct', 0.02))

        if atr_pct < 0.015:
            tp_m, sl_m = 3.0, 1.0
        elif atr_pct < 0.035:
            tp_m, sl_m = 2.5, 1.2
        else:
            tp_m, sl_m = 2.0, 1.5

        tp = entry + atr * tp_m
        sl = entry - atr * sl_m

        future  = df.iloc[i+1 : i+1+MAX_HOLD]
        hit_tp  = False; hit_sl = False; exit_price = float(future['Close'].iloc[-1])

        for _, fr in future.iterrows():
            if float(fr['Low']) <= sl:
                hit_sl = True; exit_price = sl; break
            if float(fr['High']) >= tp:
                hit_tp = True; exit_price = tp; break

        pnl_pct = (exit_price - entry) / entry * 100
        total += 1

        if hit_tp and not hit_sl:
            wins += 1; profits.append(pnl_pct)
        else:
            losses.append(pnl_pct)

    if total == 0:
        return 50.0, 0.0, 0.0, 0.0

    winrate    = wins / total * 100
    avg_profit = float(np.mean(profits)) if profits else 0.0
    avg_loss   = float(np.mean(losses))  if losses  else 0.0
    lossrate   = 100 - winrate
    expectancy = (winrate/100 * avg_profit) + (lossrate/100 * avg_loss)

    return float(winrate), float(avg_profit), float(avg_loss), float(expectancy)
