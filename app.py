import streamlit as st
import pandas as pd
import altair as alt

from scanner import scan_all, scan_top1
from watchlists import WATCHLISTS

st.set_page_config(layout="wide")
st.title("📊 Dime AI — Data Dashboard")

# ---------- Sidebar ----------
page = st.sidebar.radio("Page", ["📊 Dashboard", "🥇 Top 1"])

wl = st.sidebar.selectbox("Watchlist", list(WATCHLISTS.keys()))
custom = st.sidebar.text_area("Tickers", ",".join(WATCHLISTS[wl]))
tickers = tuple([x.strip().upper() for x in custom.split(",") if x.strip()])

min_score = st.sidebar.slider("Min Score", 0, 100, 40)
only_buy = st.sidebar.checkbox("Only BUY/STRONG BUY", True)

@st.cache_data(ttl=600)
def run_all_cached(t):
    return scan_all(t)

@st.cache_data(ttl=600)
def run_top_cached(t):
    return scan_top1(t)

def style_chip(a):
    if "STRONG BUY" in a: return "🟢 STRONG BUY"
    if "BUY" in a: return "🟩 BUY"
    if "WAIT" in a: return "🟡 WAIT"
    return "🔴 NO TRADE"

# ---------- Dashboard ----------
if page == "📊 Dashboard":
    if st.button("🔍 Scan Dashboard"):
        data = run_all_cached(tickers)
        df = pd.DataFrame(data)

        if df.empty:
            st.warning("ไม่มีข้อมูล/สัญญาณ")
            st.stop()

        df = df[df['score'] >= min_score]
        if only_buy:
            df = df[df['action'].isin(["BUY","STRONG BUY"])]

        if df.empty:
            st.warning("ไม่มีตัวที่ผ่าน filter")
            st.stop()

        # ---- Top Cards ----
        st.subheader("🏆 Top Signals")
        top3 = df.head(3)
        cols = st.columns(3)

        for idx, r in top3.iterrows():
            with cols[list(top3.index).index(idx) % 3]:
                color = "green" if r['action'] in ["BUY","STRONG BUY"] else "orange"
                st.markdown(f"""
                <div style="padding:16px;border-radius:14px;background:#111">
                <h3>{r['ticker']}</h3>
                <h2 style="color:{color}">{r['action']}</h2>
                <h1>{r['score']:.0f}</h1>
                <p>Confidence {r['confidence']:.0f}%</p>
                <p>Winrate {r['winrate']:.0f}%</p>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        # ---- Heatmap ----
        st.subheader("🟩 Heatmap Score")
        heat = alt.Chart(df).mark_rect().encode(
            x='ticker:N',
            y=alt.value(0),
            color='score:Q',
            tooltip=['ticker','score','confidence','winrate']
        ).properties(height=90)
        st.altair_chart(heat, use_container_width=True)

        st.markdown("---")

        # ---- Full Table ----
        st.subheader("📋 Full Analysis")

        show = df[[
            'ticker','score','confidence','winrate','rr',
            'd_action','d_conf','w_action','w_conf','m_action','m_conf',
            'trend','momentum','rsi_ok','breakout','volume','rs','atr_pct'
        ]].copy()

        show['Daily'] = show['d_action'] + " (" + show['d_conf'].astype(int).astype(str) + "%)"
        show['Weekly'] = show['w_action'] + " (" + show['w_conf'].astype(int).astype(str) + "%)"
        show['Monthly'] = show['m_action'] + " (" + show['m_conf'].astype(int).astype(str) + "%)"

        show = show.rename(columns={
            'ticker':'Ticker',
            'score':'Score',
            'confidence':'Confidence',
            'winrate':'Winrate %',
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
            'Ticker','Score','Confidence','Winrate %','RR',
            'Daily','Weekly','Monthly',
            'Trend','Momentum','RSI_OK','Breakout','Volume','RS','ATR%'
        ]]

        st.dataframe(final.sort_values(by="Score", ascending=False), use_container_width=True)

# ---------- Top 1 ----------
if page == "🥇 Top 1":
    if st.button("🚀 Get Best Trade"):
        res = run_top_cached(tickers)
        r = res[0]

        st.markdown(f"""
        ## {r['ticker']}
        ### {style_chip(r['action'])}
        """)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Score", f"{r.get('score',0):.1f}")
        c2.metric("Confidence", f"{r.get('confidence',0):.0f}%")
        c3.metric("Winrate", f"{r.get('winrate',0):.0f}%")
        c4.metric("RR", f"{r.get('rr',0):.2f}")

        if "price" in r:
            st.write(f"Price: {r['price']:.2f}")
            st.success(f"TP: {r['tp']:.2f}")
            st.error(f"SL: {r['sl']:.2f}")

        st.write("Reasons:", r.get("reasons","-"))
