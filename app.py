import streamlit as st
from scanner import scan_market

st.set_page_config(layout="wide")
st.title("🧠 Dime AI v8 - Quant Web")

tickers = st.text_input("หุ้น (comma)", "AAPL,MSFT,NVDA")

if st.button("Run Scan"):
    ticker_list = [t.strip().upper() for t in tickers.split(",")]

    with st.spinner("Scanning..."):
        results = scan_market(ticker_list)

    for r in results[:5]:
        st.markdown("---")
        st.subheader(f"{r['ticker']} | {r['action']}")
        st.write(f"Score: {r['score']:.1f}")
        st.write(f"Winrate: {r['winrate']:.1f}%")
        st.write(f"TP: {r['tp']:.2f} | SL: {r['sl']:.2f}")