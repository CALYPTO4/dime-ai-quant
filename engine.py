import numpy as np
import pandas as pd

def add_indicators(df):
    c, h, l, v = df['Close'], df['High'], df['Low'], df['Volume']

    df['EMA20'] = c.ewm(span=20).mean()
    df['EMA50'] = c.ewm(span=50).mean()

    exp1 = c.ewm(span=12).mean()
    exp2 = c.ewm(span=26).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9).mean()

    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100/(1+rs))

    df['ATR'] = (h - l).rolling(14).mean()

    df['Vol_MA'] = v.rolling(20).mean()
    df['Vol_Spike'] = v > df['Vol_MA'] * 1.5

    return df.dropna()


def score_signal(r):
    score = 0
    reasons = []

    # 🔥 Trend (สำคัญสุด)
    if r['Close'] > r['EMA50']:
        score += 30
        reasons.append("Uptrend")

    # Momentum
    if r['MACD'] > r['Signal']:
        score += 20
        reasons.append("Momentum")

    # RSI กลาง (ไม่ overheat)
    if 45 < r['RSI'] < 65:
        score += 15

    # Volume confirm
    if r['Vol_Spike']:
        score += 15
        reasons.append("Volume")

    # 🔴 กันสัญญาณหลอก
    if r['RSI'] > 75:
        score -= 15
        reasons.append("Overbought")

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
