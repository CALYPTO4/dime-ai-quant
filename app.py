import streamlit as st
from scanner import scan_market

st.set_page_config(layout="wide")
st.title("🧠 Dime AI Pro — Top 1 Selector")

tickers = st.text_input("หุ้น (comma)", "AAPL,MSFT,NVDA,TSLA")

def style_action(a):
    if "STRONG BUY" in a: return "🟢", "green"
    if "BUY" in a: return "🟩", "lime"
    if "WAIT" in a: return "🟡", "orange"
    return "🔴", "red"

@st.cache_data(ttl=600)
def run_scan(t):
    return scan_market(t)

if st.button("🚀 คัดตัวเดียวที่ดีที่สุด"):
    lst = tuple([x.strip().upper() for x in tickers.split(",") if x.strip()])

    with st.spinner("Scanning..."):
        res = run_scan(lst)

    r = res[0]
    st.markdown("---")

    icon, color = style_action(r['action'])
    st.markdown(f"## {icon} {r['ticker']}  \n### <span style='color:{color}'>{r['action']}</span>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Score", f"{r.get('score',0):.1f}")
    c2.metric("Confidence", f"{r.get('confidence',0):.0f}%")
    c3.metric("RR", f"{r.get('rr',0):.2f}")

    if "price" in r:
        st.write(f"Price: {r['price']:.2f}")
        st.success(f"TP: {r['tp']:.2f}")
        st.error(f"SL: {r['sl']:.2f}")

    st.write("Reasons:", r.get("reasons","-"))
