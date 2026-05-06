import time
import yfinance as yf
import pandas as pd

from engine import (
    add_indicators, hard_filter, score_row, decision,
    risk_model, backtest_winrate
)

# ---------- Download ----------
def safe_download(ticker: str, period="1y", interval="1d"):
    for _ in range(3):
        try:
            df = yf.download(
                ticker,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True
            )
            if df is not None and not df.empty:
                return df
        except Exception:
            pass
        time.sleep(1)
    return None

# ---------- Helpers ----------
def relative_strength(df: pd.DataFrame, spy_df: pd.DataFrame) -> float:
    try:
        r1 = df['Close'].pct_change(60).iloc[-1]
        r2 = spy_df['Close'].pct_change(60).iloc[-1]
        return float(r1 - r2)
    except Exception:
        return 0.0

def tf_confidence(score: float) -> float:
    return float(max(30, min(95, score)))

def analyze_tf(ticker: str, interval: str, period: str):
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

def extract_metrics(r: pd.Series, rs_vs_spy: float):
    return {
        "trend": int(r['Close'] > r['EMA50'] > r['EMA200']),
        "momentum": int(r['MACD'] > r['Signal']),
        "rsi_ok": int(45 < r['RSI'] < 65),
        "breakout": int(bool(r.get('Breakout', False))),
        "volume": int(bool(r.get('Vol_Spike', False))),
        "slope": int(r.get('Slope50', 0) > 0),
        "rs": int(rs_vs_spy > 0),
        "atr_pct": float(r.get('ATR_pct', 0))
    }

# ---------- Main analyze ----------
def analyze(ticker: str, spy_df: pd.DataFrame):
    df = safe_download(ticker, "1y", "1d")
    if df is None or len(df) < 120:
        return None

    df = add_indicators(df)
    r = df.iloc[-1]

    # Filter
    if not hard_filter(r):
        return None

    # Relative Strength
    rs = relative_strength(df, spy_df) if spy_df is not None else 0.0

    # Multi-timeframe
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

    # News sentiment (lightweight)
    try:
        news = yf.Ticker(ticker).news[:5]
        ns = 0
        for n in news:
            t = n['title'].lower()
            if any(x in t for x in ["upgrade","growth","beat","buy"]): ns += 1
            if any(x in t for x in ["downgrade","miss","cut","lawsuit"]): ns -= 1
        total_score += ns * 5
    except Exception:
        pass

    # Risk
    tp, sl, rr = risk_model(r)

    # Backtest Winrate
    winrate = backtest_winrate(df)

    # Final Confidence = score + winrate
    confidence = total_score * 0.6 + winrate * 0.4
    confidence = float(max(30, min(95, confidence)))

    metrics = extract_metrics(r, rs)

    return {
        "ticker": ticker,
        "price": float(r['Close']),
        "score": float(total_score),
        "confidence": confidence,
        "winrate": float(winrate),
        "action": decision(total_score),
        "tp": float(tp),
        "sl": float(sl),
        "rr": float(rr),
        "reasons": ", ".join(reasons),

        # TF
        "d_action": d["action"], "d_conf": d["confidence"],
        "w_action": (w["action"] if w else "NA"), "w_conf": (w["confidence"] if w else 0),
        "m_action": (m["action"] if m else "NA"), "m_conf": (m["confidence"] if m else 0),

        # metrics
        **metrics
    }

# ---------- Scan ----------
def scan_all(tickers):
    spy = safe_download("SPY", "1y", "1d")
    results = []
    for t in tickers:
        try:
            r = analyze(t, spy)
            if r:
                results.append(r)
        except Exception:
            continue
    return sorted(results, key=lambda x: x['score'], reverse=True)

def scan_top1(tickers):
    res = scan_all(tickers)
    if not res:
        return [{"ticker":"NO SIGNAL","score":0,"confidence":0,"winrate":0,"action":"WAIT"}]
    return [res[0]]
