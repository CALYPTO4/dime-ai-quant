import streamlit as st
from scanner import scan_market

st.set_page_config(layout="wide")
st.title("🧠 Dime AI Cloud v2 (Stable + Focused)")

tickers = st.text_input("หุ้นที่ต้องการวิเคราะห์", "AAPL,MSFT,NVDA")

@st.cache_data(ttl=600)
def run_scan(tickers):
    return scan_market(tickers)

if st.button("🔍 วิเคราะห์"):
    ticker_list = [t.strip().upper() for t in tickers.split(",")]

    with st.spinner("Analyzing..."):
        results = run_scan(tuple(ticker_list))

    for r in results:
        st.markdown("---")
        st.subheader(f"{r['ticker']} | {r['action']}")
        st.write(f"Score: {r['score']:.1f}")

        if "price" in r:
            st.write(f"Price: {r['price']:.2f}")
            st.write(f"TP: {r['tp']:.2f} | SL: {r['sl']:.2f}")
            st.write(f"RR: {r['rr']:.2f}")
            st.write(f"Reasons: {r['reasons']}")
