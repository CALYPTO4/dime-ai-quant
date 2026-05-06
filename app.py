import streamlit as st
import pandas as pd
import altair as alt
from scanner import scan_all
from watchlists import WATCHLISTS

st.set_page_config(layout="wide")
st.title("📊 Dime AI — Data Dashboard")

# -------- Sidebar --------
wl = st.sidebar.selectbox("Watchlist", list(WATCHLISTS.keys()))
custom = st.sidebar.text_area("Tickers", ",".join(WATCHLISTS[wl]))
tickers = tuple([x.strip().upper() for x in custom.split(",") if x.strip()])

min_score = st.sidebar.slider("Min Score", 0, 100, 40)

def style_chip(a):
    if "STRONG BUY" in a: return "🟢 STRONG BUY"
    if "BUY" in a: return "🟩 BUY"
    if "WAIT" in a: return "🟡 WAIT"
    return "🔴 NO TRADE"

@st.cache_data(ttl=600)
def run_all(t):
    return scan_all(t)

# -------- Dashboard --------
if st.button("🔍 Scan Dashboard"):

    data = run_all(tickers)
    df = pd.DataFrame(data)

    df = df[df['score'] >= min_score]
    if df.empty:
        st.warning("ไม่มีตัวที่ผ่านเงื่อนไข")
        st.stop()

    # -------- 🔥 BIG CARDS (Top 3) --------
    st.subheader("🏆 Top Signals")

    top3 = df.head(3)

    cols = st.columns(3)
    for i, r in top3.iterrows():
        with cols[i % 3]:
            color = "green" if r['action'] in ["BUY","STRONG BUY"] else "orange"
            st.markdown(f"""
            <div style="padding:15px;border-radius:12px;background:#111">
            <h3>{r['ticker']}</h3>
            <h2 style="color:{color}">{r['action']}</h2>
            <h1>{r['score']:.0f}</h1>
            <p>Confidence {r['confidence']:.0f}%</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # -------- 📊 HEATMAP --------
    st.subheader("🟩 Heatmap Score")
    heat = alt.Chart(df).mark_rect().encode(
        x='ticker:N',
        y=alt.value(0),
        color='score:Q',
        tooltip=['ticker','score','confidence']
    ).properties(height=80)
    st.altair_chart(heat, use_container_width=True)

    st.markdown("---")

    # -------- 📋 TABLE (FULL METRICS) --------
    st.subheader("📋 Full Analysis Table")

    show = df[[
        'ticker','score','confidence','rr',
        'd_action','d_conf',
        'w_action','w_conf',
        'm_action','m_conf',
        'trend','momentum','rsi_ok','breakout','volume','rs','atr_pct'
    ]].copy()

    show['Daily'] = show['d_action'] + " (" + show['d_conf'].astype(int).astype(str) + "%)"
    show['Weekly'] = show['w_action'] + " (" + show['w_conf'].astype(int).astype(str) + "%)"
    show['Monthly'] = show['m_action'] + " (" + show['m_conf'].astype(int).astype(str) + "%)"

    show = show.rename(columns={
        'ticker':'Ticker',
        'score':'Score',
        'confidence':'Confidence',
        'rr':'RR',
        'trend':'Trend',
        'momentum':'Momentum',
        'rsi_ok':'RSI_OK',
        'breakout':'Breakout',
        'volume':'Volume',
        'rs':'RS',
        'atr_pct':'ATR%'
    })

    final = show[[
        'Ticker','Score','Confidence','RR',
        'Daily','Weekly','Monthly',
        'Trend','Momentum','RSI_OK','Breakout','Volume','RS','ATR%'
    ]]

    st.dataframe(final.sort_values(by="Score", ascending=False), use_container_width=True)
