import streamlit as st
from scanner import scan_market

st.set_page_config(layout="wide")
st.title("🧠 Dime AI v8 - Quant Web (Stable)")

tickers = st.text_input("หุ้น (comma)", "AAPL,MSFT,NVDA")

if st.button("Run Scan"):
    ticker_list = [t.strip().upper() for t in tickers.split(",")]

    with st.spinner("🔍 Scanning market..."):
        results = scan_market(ticker_list)

    st.success("✅ Scan Complete")

    for r in results[:5]:
        st.markdown("---")

        st.subheader(f"{r['ticker']} | {r['action']}")

        st.write(f"Score: {r['score']:.1f}")
        st.write(f"Winrate: {r['winrate']:.1f}%")

        st.write(f"TP: {r['tp']:.2f}")
        st.write(f"SL: {r['sl']:.2f}")
