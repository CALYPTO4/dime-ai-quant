import yfinance as yf
import pandas as pd
from engine import *

def safe_download(ticker):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df is None or df.empty:
            return None
        return df
    except Exception as e:
        print(f"Download error {ticker}: {e}")
        return None


def analyze(ticker):
    df = safe_download(ticker)

    if df is None or len(df) < 60:
        return None

    try:
        df = add_indicators(df)
        df = df.dropna()

        if len(df) < 50:
            return None

        model = train_model(df)

        last = df.iloc[-1]

        score = score_row(last)

        prob = predict_prob(model, last)
        score += (prob - 0.5) * 20

        action = decision(score)

        tp, sl, rr = smart_exit(last)

        winrate = backtest(df)

        return {
            "ticker": ticker,
            "score": float(score),
            "action": action,
            "tp": float(tp),
            "sl": float(sl),
            "winrate": float(winrate)
        }

    except Exception as e:
        print(f"Analyze error {ticker}: {e}")
        return None


def scan_market(tickers):
    results = []

    for t in tickers:
        r = analyze(t)
        if r:
            results.append(r)

    # 🔥 fallback ถ้าไม่มีผลลัพธ์เลย
    if not results:
        return [{
            "ticker": "NO DATA",
            "score": 0,
            "action": "ERROR",
            "tp": 0,
            "sl": 0,
            "winrate": 0
        }]

    return sorted(results, key=lambda x: x['score'], reverse=True)
