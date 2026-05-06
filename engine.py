import numpy as np
import pandas as pd

def add_indicators(df):
    # flatten columns (กัน MultiIndex จาก yfinance)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    c = df['Close'].astype(float)
    h = df['High'].astype(float)
    l = df['Low'].astype(float)
    v = df['Volume'].astype(float)

    # Trend
    df['EMA20'] = c.ewm(span=20).mean()
    df['EMA50'] = c.ewm(span=50).mean()
    df['EMA200'] = c.ewm(span=200).mean()

    # Momentum
    exp1 = c.ewm(span=12).mean()
    exp2 = c.ewm(span=26).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9).mean()

    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    df['RSI'] = 100 - (100/(1+rs))

    # Volatility
    df['ATR'] = (h - l).rolling(14).mean()
    df['ATR_pct'] = df['ATR'] / c

    # Volume
    df['Vol_MA'] = v.rolling(20).mean()
    df['Vol_Spike'] = (v.values > (df['Vol_MA'].values * 1.5))

    # Breakout
    df['HH_20'] = c.rolling(20).max()
    df['Breakout'] = c >= df['HH_20']

    # Slope (แรงของเทรนด์)
    df['Slope50'] = df['EMA50'].diff(5)

    return df.dropna()


def hard_filter(r):
    # ตัดของคุณภาพต่ำก่อนให้เหลือน้อย
    if r['Close'] < r['EMA200']:
        return False
    if r['ATR_pct'] > 0.08:   # ผันผวนเกิน
        return False
    if r['RSI'] > 75:         # overbought
        return False
    return True


def score_row(r, rs_vs_spy=0.0):
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

    # Breakout + Volume confirm
    if r['Breakout']:
        score += 20; reasons.append("Breakout")

    if r['Vol_Spike']:
        score += 10; reasons.append("Volume Spike")

    # Trend slope
    if r['Slope50'] > 0:
        score += 5

    # Relative Strength vs SPY
    if rs_vs_spy > 0:
        score += 10; reasons.append("Outperform SPY")

    return score, reasons


def decision(score):
    if score >= 70:
        return "STRONG BUY"
    elif score >= 55:
        return "BUY"
    elif score >= 40:
        return "WAIT"
    return "NO TRADE"


def risk_model(r):
    atr = r['ATR']
    tp = r['Close'] + atr * 2
    sl = r['Close'] - atr * 1.2
    rr = (tp - r['Close']) / (r['Close'] - sl + 1e-9)
    return tp, sl, rr

def backtest_winrate(df):
    wins = 0
    total = 0

    for i in range(50, len(df)-10):
        r = df.iloc[i]

        score, _ = score_row(r, 0)

        # ใช้เงื่อนไขเดียวกับ signal จริง
        if score < 55:
            continue

        entry = r['Close']
        atr = r['ATR']

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

    return (wins / total) * 100
