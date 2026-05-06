import numpy as np
import pandas as pd

# ---------- Indicators ----------
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    # Flatten MultiIndex (yfinance บางครั้งส่งมา)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    c = df['Close'].astype(float)
    h = df['High'].astype(float)
    l = df['Low'].astype(float)
    v = df['Volume'].astype(float)

    # Trend
    df['EMA20'] = c.ewm(span=20, adjust=False).mean()
    df['EMA50'] = c.ewm(span=50, adjust=False).mean()
    df['EMA200'] = c.ewm(span=200, adjust=False).mean()

    # Momentum
    exp1 = c.ewm(span=12, adjust=False).mean()
    exp2 = c.ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    df['RSI'] = 100 - (100/(1+rs))

    # Volatility
    df['ATR'] = (h - l).rolling(14).mean()
    df['ATR_pct'] = df['ATR'] / (c + 1e-9)

    # Volume
    df['Vol_MA'] = v.rolling(20).mean()
    df['Vol_Spike'] = (v.values > (df['Vol_MA'].values * 1.5))

    # Breakout
    df['HH_20'] = c.rolling(20).max()
    df['Breakout'] = c >= df['HH_20']

    # Slope
    df['Slope50'] = df['EMA50'].diff(5)

    return df.dropna()

# ---------- Rules ----------
def hard_filter(r: pd.Series) -> bool:
    # คุณภาพขั้นต่ำ
    if r['Close'] < r['EMA200']:
        return False
    if r['ATR_pct'] > 0.08:
        return False
    if r['RSI'] > 75:
        return False
    return True

def score_row(r: pd.Series, rs_vs_spy: float = 0.0):
    score = 0
    reasons = []

    # Trend
    if r['Close'] > r['EMA50'] > r['EMA200']:
        score += 30; reasons.append("Strong Trend")

    # Momentum
    if r['MACD'] > r['Signal']:
        score += 15; reasons.append("MACD Up")

    if 45 < r['RSI'] < 65:
        score += 10

    # Breakout + Volume
    if bool(r.get('Breakout', False)):
        score += 20; reasons.append("Breakout")

    if bool(r.get('Vol_Spike', False)):
        score += 10; reasons.append("Volume Spike")

    # Slope
    if float(r.get('Slope50', 0)) > 0:
        score += 5

    # Relative Strength
    if rs_vs_spy > 0:
        score += 10; reasons.append("Outperform SPY")

    return float(score), reasons

def decision(score: float) -> str:
    if score >= 70:
        return "STRONG BUY"
    elif score >= 55:
        return "BUY"
    elif score >= 40:
        return "WAIT"
    return "NO TRADE"

def risk_model(r: pd.Series):
    atr = float(r['ATR'])
    entry = float(r['Close'])
    tp = entry + atr * 2
    sl = entry - atr * 1.2
    rr = (tp - entry) / (entry - sl + 1e-9)
    return float(tp), float(sl), float(rr)

# ---------- Backtest (rolling) ----------
def backtest_winrate(df: pd.DataFrame) -> float:
    """
    Winrate โดยใช้กฎเดียวกับ signal:
    - Trigger: score >= 55
    - TP = +2*ATR, SL = -1.2*ATR
    - Horizon: 10 วันถัดไป
    """
    wins = 0
    total = 0

    # ต้องมี buffer พอสำหรับ ATR/EMA
    for i in range(60, len(df) - 10):
        r = df.iloc[i]
        score, _ = score_row(r, 0.0)

        if score < 55:
            continue

        entry = float(r['Close'])
        atr = float(r['ATR'])
        tp = entry + atr * 2
        sl = entry - atr * 1.2

        future = df.iloc[i+1:i+11]

        hit_tp = (future['High'] >= tp).any()
        hit_sl = (future['Low'] <= sl).any()

        total += 1
        if hit_tp and not hit_sl:
            wins += 1

    if total == 0:
        return 50.0

    return float((wins / total) * 100.0)
