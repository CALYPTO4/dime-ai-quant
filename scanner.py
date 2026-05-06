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
    # 🔥 วิเคราะห์ 3 timeframe
    daily = analyze_tf(ticker, "1d", "1y")
    weekly = analyze_tf(ticker, "1wk", "2y")
    monthly = analyze_tf(ticker, "1mo", "5y")

    if not daily:
        return None

    # 🔥 รวมคะแนน
    total_score = (
        daily['score'] * 0.5 +
        (weekly['score'] if weekly else 0) * 0.3 +
        (monthly['score'] if monthly else 0) * 0.2
    )

    confidence = min(95, max(30, total_score))

    final_action = decision(total_score)

    # 🔥 ดึงข้อมูล price/TP/SL จาก daily
    df = safe_download(ticker)
    if df is None:
        return None

    df = add_indicators(df)
    r = df.iloc[-1]

    tp, sl, rr = risk_model(r)

    return {
        "ticker": ticker,
        "price": float(r['Close']),
        "score": float(total_score),
        "confidence": float(confidence),
        "action": final_action,
        "tp": float(tp),
        "sl": float(sl),
        "rr": float(rr),
        "reasons": ", ".join(daily['reasons'])
    }
    
def analyze_tf(ticker, interval, period):

    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            progress=False
        )

        if df is None or len(df) < 50:
            return None

        df = add_indicators(df)
        r = df.iloc[-1]

        score, reasons = score_signal(r)

        return {
            "score": score,
            "action": decision(score),
            "reasons": reasons
        }

    except:
        return None

def scan_market(tickers):
    results = []

    for t in tickers:
        r = analyze(t)
        if r:
            results.append(r)

    if not results:
        return [{"ticker": "NO SIGNAL", "score": 0, "action": "WAIT"}]

    return sorted(results, key=lambda x: x['score'], reverse=True)
