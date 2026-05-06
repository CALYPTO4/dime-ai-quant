import streamlit as st
from scanner import scan_market

st.set_page_config(layout="wide")

st.title("🧠 Dime AI Pro Signal System")

tickers = st.text_input("หุ้น", "AAPL,MSFT,NVDA")

# 🎨 สี + icon
def style_action(action):
    if "STRONG BUY" in action:
        return "🟢", "green"
    elif "BUY" in action:
        return "🟩", "lime"
    elif "WAIT" in action:
        return "🟡", "orange"
    return "🔴", "red"


@st.cache_data(ttl=600)
def run_scan(tickers):
    return scan_market(tickers)


if st.button("🚀 วิเคราะห์ขั้นสูง"):

    ticker_list = [t.strip().upper() for t in tickers.split(",")]

    with st.spinner("Analyzing market..."):
        results = run_scan(tuple(ticker_list))

    for r in results:
        st.markdown("---")

        icon, color = style_action(r['action'])

        st.markdown(f"""
        ## {icon} {r['ticker']}
        ### <span style='color:{color}'>{r['action']}</span>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)

        c1.metric("📊 Score", f"{r['score']:.1f}")
        c2.metric("🎯 Confidence", f"{r.get('confidence',50):.0f}%")
        c3.metric("⚖️ Risk/Reward", f"{r.get('rr',0):.2f}")

        st.write("💡 Reasons:", r.get("reasons","-"))

        if "tp" in r:
            st.success(f"TP: {r['tp']:.2f}")
            st.error(f"SL: {r['sl']:.2f}")
