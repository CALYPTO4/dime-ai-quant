import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

def add_indicators(df):
    c = df['Close']
    df['EMA20'] = c.ewm(span=20).mean()
    df['EMA50'] = c.ewm(span=50).mean()

    exp1 = c.ewm(span=12).mean()
    exp2 = c.ewm(span=26).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9).mean()

    df['Momentum'] = df['MACD'] - df['Signal']
    df['RSI'] = 50

    df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
    df['Volatility'] = df['ATR'] / df['Close']
    df['Vol_Force'] = df['Volume'] / df['Volume'].rolling(20).mean()
    df['Trend'] = (df['Close'] > df['EMA50']).astype(int)

    return df.dropna()

def score_row(r):
    score = 0
    if r['Trend'] == 1: score += 25
    if r['Momentum'] > 0: score += 20
    if r['Vol_Force'] > 1.2: score += 15
    return score

def decision(score):
    if score >= 60: return "BUY"
    elif score >= 40: return "WAIT"
    return "NO TRADE"

def smart_exit(r):
    tp = r['Close'] + r['ATR'] * 2
    sl = r['Close'] - r['ATR'] * 1.2
    rr = (tp - r['Close']) / (r['Close'] - sl + 1e-9)
    return tp, sl, rr

def train_model(df):
    df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
    df = df.dropna()

    X = df[['Momentum','Volatility','Vol_Force']]
    y = df['Target']

    model = RandomForestClassifier()
    model.fit(X, y)

    return model

def predict_prob(model, r):
    return model.predict_proba([[r['Momentum'], r['Volatility'], r['Vol_Force']]])[0][1]

def backtest(df):
    wins, total = 0, 0
    for i in range(len(df)-1):
        if df.iloc[i]['Momentum'] > 0:
            total += 1
            if df.iloc[i+1]['Close'] > df.iloc[i]['Close']:
                wins += 1
    return (wins/total*100) if total else 0