import streamlit as st
import pandas as pd
import altair as alt
import yfinance as yf

from scanner import scan_market, scan_all
from watchlists import WATCHLISTS

st.set_page_config(layout="wide")
st.title("📊 Dime AI — Trading Dashboard")

# ---------- Sidebar ----------
page = st.sidebar.radio("หน้า", ["📊 Dashboard", "🥇 Top 1"])

wl_name = st.sidebar.selectbox("Watchlist", list(WATCHLISTS.keys()))
default_list = WATCHLISTS[wl_name]

custom = st.sidebar.text_area(
    "แก้ไขรายการหุ้น (comma)",
    ",".join(default_list)
)

tickers = tuple([x.strip().upper() for x in custom.split(",") if x.strip()])

min_score = st.sidebar.slider("ขั้นต่ำ Score", 0, 100, 40)
only_buy = st.sidebar.checkbox("แสดงเฉพาะ BUY/STRONG BUY", True)

# ---------- Utils ----------
def style_action(a):
    if "STRONG BUY" in a: return "🟢", "green"
    if "BUY" in a: return "🟩", "lime"
    if "WAIT" in a: return "🟡", "orange"
    return "🔴", "red"

@st.cache_data(ttl=600)
def run_all_cached(t):
    return scan_all(t)

@st.cache_data(ttl=600)
def run_top_cached(t):
    return scan_market(t)

@st.cache_data(ttl=600)
def load_price(ticker):
    df = yf.download(ticker, period="6mo", interval="1d", progress=False)
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    c = df['Close']
    df['EMA20'] = c.ewm(span=20).mean()
    df['EMA50'] = c.ewm(span=50).mean()
    exp1 = c.ewm(span=12).mean()
    exp2 = c.ewm(span=26).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9).mean()
    df = df.reset_index()
    return df

# ---------- PAGE: DASHBOARD ----------
if page == "📊 Dashboard":

    if st.button("🔍 Scan Dashboard"):
        data = run_all_cached(tickers)

        if not data:
            st.warning("ไม่มีสัญญาณ")
            st.stop()

        df = pd.DataFrame(data)

        # Filter
        df = df[df['score'] >= min_score]
        if only_buy:
            df = df[df['action'].isin(["BUY","STRONG BUY"])]

        if df.empty:
            st.warning("ไม่มีตัวที่ผ่าน filter")
            st.stop()

        # ---------- Heatmap ----------
        st.subheader("🟩 Market Heatmap")
        df['color'] = df['score']

        heat = alt.Chart(df).mark_rect().encode(
            x=alt.X('ticker:N', title="Ticker"),
            y=alt.value(0),
            color=alt.Color('score:Q', scale=alt.Scale(scheme='greenblue')),
            tooltip=['ticker','score','confidence','action']
        ).properties(height=80)

        st.altair_chart(heat, use_container_width=True)

        # ---------- Ranking ----------
        st.subheader("📊 Ranking")
        df_show = df[['ticker','action','score','confidence','rr']].copy()
        df_show['Signal'] = df_show['action'].apply(lambda x: style_action(x)[0] + " " + x)
        df_show = df_show.drop(columns=['action'])

        st.dataframe(
            df_show.sort_values(by="score", ascending=False),
            use_container_width=True
        )

        # ---------- Chart ----------
        st.subheader("📉 Price Chart")

        selected = st.selectbox("เลือกหุ้นดูกราฟ", df['ticker'])

        price_df = load_price(selected)

        if price_df is not None:

            base = alt.Chart(price_df).encode(x='Date:T')

            price = base.mark_line().encode(y='Close:Q')
            ema20 = base.mark_line().encode(y='EMA20:Q')
            ema50 = base.mark_line().encode(y='EMA50:Q')

            st.altair_chart(price + ema20 + ema50, use_container_width=True)

            macd = alt.Chart(price_df).mark_line().encode(
                x='Date:T',
                y='MACD:Q'
            )

            st.altair_chart(macd, use_container_width=True)

# ---------- PAGE: TOP 1 ----------
if page == "🥇 Top 1":

    if st.button("🚀 Get Best Trade"):
        res = run_top_cached(tickers)
        r = res[0]

        icon, color = style_action(r['action'])

        st.markdown(f"""
        ## {icon} {r['ticker']}
        ### <span style='color:{color}'>{r['action']}</span>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Score", f"{r.get('score',0):.1f}")
        c2.metric("Confidence", f"{r.get('confidence',0):.0f}%")
        c3.metric("RR", f"{r.get('rr',0):.2f}")

        if "price" in r:
            st.write(f"Price: {r['price']:.2f}")
            st.success(f"TP: {r['tp']:.2f}")
            st.error(f"SL: {r['sl']:.2f}")

        st.write("Reasons:", r.get("reasons","-"))
