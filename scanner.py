import yfinance as yf
import time
from engine import *

def safe_download(ticker):
    for _ in range(3):
        try:
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
            if df is not None and not df.empty:
                return df
        except:
            pass
        time.sleep(1)
    return None


def analyze(ticker):
    df = safe_download(ticker)

    if df is None or len(df) < 60:
        return None

    df = add_indicators(df)

    if len(df) < 50:
        return None

    r = df.iloc[-1]

    score, reasons = score_signal(r)

    # 🔥 Filter สำคัญ (เพิ่มความแม่น)
    if r['Close'] < r['EMA50']:
        return None

    tp, sl, rr = risk_model(r)

    return {
        "ticker": ticker,
        "price": float(r['Close']),
        "score": float(score),
        "action": decision(score),
        "tp": float(tp),
        "sl": float(sl),
        "rr": float(rr),
        "reasons": ", ".join(reasons)
    }


def scan_market(tickers):
    results = []

    for t in tickers:
        r = analyze(t)
        if r:
            results.append(r)

    if not results:
        return [{"ticker": "NO SIGNAL", "score": 0, "action": "WAIT"}]

    return sorted(results, key=lambda x: x['score'], reverse=True)
