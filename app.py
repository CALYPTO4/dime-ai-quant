import streamlit as st
import pandas as pd
from scanner import scan_market, scan_all

st.set_page_config(layout="wide")

st.title("🧠 Dime AI Pro System")

# -------- Sidebar --------
page = st.sidebar.radio(
    "เลือกหน้า",
    ["🥇 Top 1 Signal", "📊 Market Overview"]
)

tickers = st.sidebar.text_input(
    "หุ้น (comma)",
    "AAPL,MSFT,NVDA,TSLA"
)

ticker_list = tuple([x.strip().upper() for x in tickers.split(",") if x.strip()])


def style_action(a):
    if "STRONG BUY" in a: return "🟢", "green"
    if "BUY" in a: return "🟩", "lime"
    if "WAIT" in a: return "🟡", "orange"
    return "🔴", "red"


@st.cache_data(ttl=600)
def run_top(t):
    return scan_market(t)


@st.cache_data(ttl=600)
def run_all(t):
    return scan_all(t)


# =========================
# 🥇 PAGE 1: TOP 1
# =========================
if page == "🥇 Top 1 Signal":

    if st.button("🚀 คัดตัวเดียว"):
        res = run_top(ticker_list)

        r = res[0]

        icon, color = style_action(r['action'])

        st.markdown("---")

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


# =========================
# 📊 PAGE 2: MARKET OVERVIEW
# =========================
if page == "📊 Market Overview":

    if st.button("📊 วิเคราะห์ทั้งหมด"):

        data = run_all(ticker_list)

        if not data:
            st.warning("ไม่มีสัญญาณ")
            st.stop()

        df = pd.DataFrame(data)

        # 🎨 แปลง Action เป็น icon
        df['Signal'] = df['action'].apply(lambda x: style_action(x)[0] + " " + x)

        # เลือกคอลัมน์
        df_show = df[[
            'ticker', 'Signal', 'score', 'confidence', 'rr'
        ]].rename(columns={
            'ticker': 'Ticker',
            'score': 'Score',
            'confidence': 'Confidence',
            'rr': 'RR'
        })

        st.subheader("📋 ตารางเปรียบเทียบ")

        st.dataframe(
            df_show.sort_values(by="Score", ascending=False),
            use_container_width=True
        )

        st.markdown("---")

        st.subheader("📊 เปรียบเทียบ Score")

        st.bar_chart(
            df.set_index('ticker')['score']
        )
