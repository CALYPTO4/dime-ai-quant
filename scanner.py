import yfinance as yf
from engine import *

def analyze(ticker):
    df = yf.download(ticker, period="1y", interval="1d", progress=False)

    if df.empty:
        return None

    df = add_indicators(df)

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
        "score": score,
        "action": action,
        "tp": tp,
        "sl": sl,
        "winrate": winrate
    }

def scan_market(tickers):
    results = []
    for t in tickers:
        try:
            r = analyze(t)
            if r:
                results.append(r)
        except:
            pass
    return sorted(results, key=lambda x: x['score'], reverse=True)