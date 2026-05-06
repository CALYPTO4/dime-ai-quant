import yfinance as yf
import time
from engine import *

# ---------- helpers ----------
def relative_strength(df, spy_df):
    try:
        r1 = df['Close'].pct_change(60).iloc[-1]
        r2 = spy_df['Close'].pct_change(60).iloc[-1]
        return float(r1 - r2)
    except:
        return 0.0

def tf_confidence(score):
    # map score -> 30..95
    return float(max(30, min(95, score)))

def analyze_tf(ticker, interval, period):
    df = safe_download(ticker, period, interval)
    if df is None or len(df) < 80:
        return None

    df = add_indicators(df)
    r = df.iloc[-1]

    score, reasons = score_row(r, 0.0)

    return {
        "score": float(score),
        "action": decision(score),
        "confidence": tf_confidence(score),
        "reasons": reasons
    }

def extract_metrics(r, rs_vs_spy):
    # แปลงเป็นค่าที่อ่านง่ายสำหรับ dashboard
    trend = int(r['Close'] > r['EMA50'] > r['EMA200'])
    momentum = int(r['MACD'] > r['Signal'])
    rsi_ok = int(45 < r['RSI'] < 65)
    breakout = int(bool(r.get('Breakout', False)))
    vol = int(bool(r.get('Vol_Spike', False)))
    slope = int(r.get('Slope50', 0) > 0)
    rs_flag = int(rs_vs_spy > 0)
    atrp = float(r.get('ATR_pct', 0))

    return {
        "trend": trend,
        "momentum": momentum,
        "rsi_ok": rsi_ok,
        "breakout": breakout,
        "volume": vol,
        "slope": slope,
        "rs": rs_flag,
        "atr_pct": atrp
    }

# ---------- main analyze ----------
def analyze(ticker, spy_df):
    df = safe_download(ticker, "1y", "1d")
    if df is None or len(df) < 120:
        return None

    df = add_indicators(df)
    r = df.iloc[-1]

    # filter คุณภาพ
    if not hard_filter(r):
        return None

    rs = relative_strength(df, spy_df)

    # TF
    d = analyze_tf(ticker, "1d", "1y")
    w = analyze_tf(ticker, "1wk", "2y")
    m = analyze_tf(ticker, "1mo", "5y")

    if not d:
        return None

    base_score, reasons = score_row(r, rs)

    total_score = (
        base_score * 0.6 +
        (w['score'] if w else 0) * 0.25 +
        (m['score'] if m else 0) * 0.15
    )

    # news (ถ้ามี)
    try:
        news = yf.Ticker(ticker).news[:5]
        ns = 0
        for n in news:
            t = n['title'].lower()
            if any(x in t for x in ["upgrade","growth","beat","buy"]): ns += 1
            if any(x in t for x in ["downgrade","miss","cut","lawsuit"]): ns -= 1
        total_score += ns * 5
    except:
        pass

    tp, sl, rr = risk_model(r)

    confidence = max(30, min(95, total_score + (rr - 1) * 5))

    metrics = extract_metrics(r, rs)

    return {
        "ticker": ticker,
        "price": float(r['Close']),
        "score": float(total_score),
        "confidence": float(confidence),
        "action": decision(total_score),
        "tp": float(tp),
        "sl": float(sl),
        "rr": float(rr),
        "reasons": ", ".join(reasons),

        # 🔥 TF outputs
        "d_action": d["action"],
        "d_conf": d["confidence"],
        "w_action": (w["action"] if w else "NA"),
        "w_conf": (w["confidence"] if w else 0),
        "m_action": (m["action"] if m else "NA"),
        "m_conf": (m["confidence"] if m else 0),

        # 🔥 metrics for table
        **metrics
    }

def scan_all(tickers):
    spy = safe_download("SPY", "1y", "1d")
    results = []
    for t in tickers:
        r = analyze(t, spy)
        if r:
            results.append(r)
    return sorted(results, key=lambda x: x['score'], reverse=True)
