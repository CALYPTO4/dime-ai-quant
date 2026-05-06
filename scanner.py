import yfinance as yf
import time
from engine import *

# --------- utils ---------
def safe_download(ticker, period="1y", interval="1d"):
    for _ in range(3):
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False)
            if df is not None and not df.empty:
                return df
        except:
            pass
        time.sleep(1)
    return None


def get_news_sentiment(ticker):
    try:
        news = yf.Ticker(ticker).news[:5]
        score = 0
        for n in news:
            t = n['title'].lower()
            if any(x in t for x in ["upgrade","growth","beat","buy"]):
                score += 1
            if any(x in t for x in ["downgrade","miss","cut","lawsuit"]):
                score -= 1
        return score
    except:
        return 0


def relative_strength(df, spy_df):
    # เทียบผลตอบแทนช่วงเดียวกัน (ประมาณ 60 วัน)
    try:
        r1 = df['Close'].pct_change(60).iloc[-1]
        r2 = spy_df['Close'].pct_change(60).iloc[-1]
        return float(r1 - r2)
    except:
        return 0.0


def analyze_tf(ticker, interval, period):
    df = safe_download(ticker, period, interval)
    if df is None or len(df) < 80:
        return None

    df = add_indicators(df)
    r = df.iloc[-1]
    score, reasons = score_row(r, 0.0)

    return {"score": score, "reasons": reasons}


# --------- main analyze ---------
def analyze(ticker, spy_df):
    # Daily สำหรับตัวจริง + RS
    df = safe_download(ticker, "1y", "1d")
    if df is None or len(df) < 120:
        return None

    df = add_indicators(df)
    r = df.iloc[-1]

    # Hard filter ก่อน
    if not hard_filter(r):
        return None

    rs = relative_strength(df, spy_df)

    # Multi-TF
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

    # News
    news = get_news_sentiment(ticker)
    total_score += news * 5

    # Risk
    tp, sl, rr = risk_model(r)

    # Confidence: normalize + rr bonus
    confidence = max(30, min(95, total_score + (rr - 1) * 5))

    return {
        "ticker": ticker,
        "price": float(r['Close']),
        "score": float(total_score),
        "confidence": float(confidence),
        "action": decision(total_score),
        "tp": float(tp),
        "sl": float(sl),
        "rr": float(rr),
        "reasons": ", ".join(reasons)
    }


def scan_market(tickers):
    # ใช้ SPY เป็น benchmark RS
    spy = safe_download("SPY", "1y", "1d")
    if spy is None:
        spy = None

    results = []
    for t in tickers:
        r = analyze(t, spy)
        if r:
            results.append(r)

    if not results:
        return [{"ticker": "NO SIGNAL", "action": "WAIT", "score": 0, "confidence": 0}]

    # 🥇 เอา “ตัวเดียวที่ดีที่สุด”
    best = sorted(results, key=lambda x: x['score'], reverse=True)[0]
    return [best]

def scan_all(tickers):
    spy = safe_download("SPY", "1y", "1d")
    results = []

    for t in tickers:
        r = analyze(t, spy)
        if r:
            results.append(r)

    if not results:
        return []

    return sorted(results, key=lambda x: x['score'], reverse=True)
