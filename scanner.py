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
def get_market_regime(spy_df) -> dict:
    """เช็ค market regime จาก SPY"""
    if spy_df is None or len(spy_df) < 60:
        return {"bull": True, "atr_regime": "normal", "score_boost": 0}

    spy = add_indicators(spy_df.copy())
    r = spy.iloc[-1]
    is_bull = float(r['Close']) > float(r['EMA200']) and float(r['EMA50']) > float(r['EMA200'])
    spy_atr_pct = float(r['ATR_pct'])

    return {
        "bull": is_bull,
        "atr_regime": "high" if spy_atr_pct > 0.015 else "normal",
        "score_boost": 5 if is_bull else -10   # bear market = ยาก
    }


def analyze(ticker: str, spy_df: pd.DataFrame, market_regime: dict):
    df = safe_download(ticker, "1y", "1d")
    if df is None or len(df) < 120:
        return None

    df = add_indicators(df)
    r  = df.iloc[-1]

    if not hard_filter(r):
        return None

    rs = relative_strength(df, spy_df) if spy_df is not None else 0.0

    # Multi-timeframe
    d = analyze_tf(ticker, "1d", "1y")
    w = analyze_tf(ticker, "1wk", "2y")
    m = analyze_tf(ticker, "1mo", "5y")

    if not d:
        return None

    # ── Multi-timeframe consensus ──────────────────────────
    tf_scores = [
        d['score'],
        w['score'] if w else 0,
        m['score'] if m else 0
    ]
    tf_bullish = sum(1 for s in tf_scores if s >= 42)

    base_score, reasons, penalties = score_row(r, rs)

    # Weighted combination
    total_score = (
        base_score      * 0.55 +
        (w['score'] if w else 0) * 0.28 +
        (m['score'] if m else 0) * 0.17
    )

    # Consensus penalty/bonus
    if tf_bullish == 3:
        total_score += 8; reasons.append("All TF aligned")
    elif tf_bullish == 1:
        total_score -= 10; penalties.append("Only 1 TF bullish")
    
    # Monthly bearish cap
    if m and m['score'] < 35:
        total_score = min(total_score, 60)
        penalties.append("Monthly bearish cap")

    # Market regime adjustment
    total_score += market_regime.get("score_boost", 0)

    # News sentiment
    try:
        news = yf.Ticker(ticker).news[:5]
        ns = 0
        for n in news:
            t = n.get('title','').lower()
            if any(x in t for x in ["upgrade","growth","beat","buy","record"]): ns += 1
            if any(x in t for x in ["downgrade","miss","cut","lawsuit","fraud"]): ns -= 1
        total_score += ns * 3  # ลดจาก 5 → 3 (news เชื่อไม่ได้เต็มที่)
    except Exception:
        pass

    tp, sl, rr = risk_model(r)
    winrate, avg_profit, avg_loss, expectancy = backtest_winrate(df)

    # Confidence = ถ่วงน้ำหนัก score + winrate + expectancy
    confidence = total_score * 0.5 + winrate * 0.3 + min(max(expectancy * 5, 0), 20)
    confidence = float(max(30, min(95, confidence)))

    metrics = extract_metrics(r, rs)

    return {
        "ticker":      ticker,
        "price":       float(r['Close']),
        "score":       float(total_score),
        "confidence":  confidence,
        "winrate":     float(winrate),
        "expectancy":  float(expectancy),
        "avg_profit":  float(avg_profit),
        "avg_loss":    float(avg_loss),
        "action":      decision(total_score),
        "tp":          float(tp),
        "sl":          float(sl),
        "rr":          float(rr),
        "reasons":     ", ".join(reasons),
        "penalties":   ", ".join(penalties),
        "tf_consensus": tf_bullish,
        "d_action": d["action"], "d_conf": d["confidence"],
        "w_action": (w["action"] if w else "NA"), "w_conf": (w["confidence"] if w else 0),
        "m_action": (m["action"] if m else "NA"), "m_conf": (m["confidence"] if m else 0),
        **metrics
    }


# scan_all ต้องส่ง market_regime เข้าไปด้วย
def scan_all(tickers):
    spy = safe_download("SPY", "1y", "1d")
    regime = get_market_regime(spy)
    results = []
    for t in tickers:
        try:
            r = analyze(t, spy, regime)
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
