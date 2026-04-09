import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- ページ設定 ---
st.set_page_config(page_title="Chief Dealer Dashboard Pro", layout="wide")

# --- カスタムCSS（スマホ最適化） ---
st.markdown("""
    <style>
    .metric-card {
        background-color: #1e1e1e; border-radius: 4px; padding: 10px;
        border-left: 5px solid #333; margin-bottom: 8px; color: white;
    }
    .status-good { border-left-color: #00bfff; }
    .status-stable { border-left-color: #00ff00; }
    .status-warning { border-left-color: #ff4500; }
    .status-critical { border-left-color: #ff0000; }
    .price-text { font-size: 1.5rem; font-weight: bold; }
    .label-text { font-size: 0.8rem; color: #aaa; }
    /* スマホで指標が潰れないよう調整 */
    [data-testid="stMetric"] { background-color: #161616; padding: 10px; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- 銘柄リスト定義 ---
ASSETS = {
    "為替": {
        "USD/JPY": "USDJPY=X", "EUR/USD": "EURUSD=X", "EUR/JPY": "EURJPY=X",
        "GBP/USD": "GBPUSD=X", "GBP/JPY": "GBPJPY=X",
        "AUD/USD": "AUDUSD=X", "AUD/JPY": "AUDJPY=X"
    },
    "通貨指数": {
        "USD Index": "UUP", "JPY Index(FXY)": "FXY"
    },
    "主要指数": {
        "S&P500": "^GSPC", "NYダウ": "^DJI", "SOX指数": "^SOX", "日経225": "^N225",
        "独DAX": "^GDAXI", "英FTSE": "^FTSE", "上海総合": "000001.SS"
    },
    "金利/VIX": {
        "米10年債": "^TNX", "米2年債": "^ZVQ", "VIX指数": "^VIX"
    }
}

def get_advanced_status(z_score, return_val):
    if z_score < 1.0: return "平常時", "🟢", "status-stable"
    if return_val > 0: return "良好・過熱", "🔵", "status-good"
    return "注意・警戒", "🟠", "status-warning"

@st.cache_data(ttl=300)
def fetch_all_data(_tickers):
    try:
        data = yf.download(list(_tickers), period="1y", interval="1d", progress=False)['Close']
        return data
    except:
        return pd.DataFrame()

# --- メイン処理 ---
st.title("🛡️ Market Dashboard Mobile")
tabs = st.tabs(["📊 総合", "💱 為替", "📈 指数", "📉 金利"])

tickers_map = {name: ticker for cat in ASSETS.values() for name, ticker in cat.items()}

try:
    prices_df = fetch_all_data(list(tickers_map.values()))
    results = {}
    
    for name, ticker in tickers_map.items():
        if ticker in prices_df.columns:
            series = prices_df[ticker].dropna()
            if series.empty or len(series) < 2: continue
            
            rets = np.log(series / series.shift(1))
            vol = rets.rolling(20).std() * np.sqrt(252)
            z = (vol.iloc[-1] - vol.mean()) / vol.std() if not vol.empty else 0
            curr_p = series.iloc[-1]
            change = (curr_p / series.iloc[-2] - 1) * 100
            
            status, icon, css_class = get_advanced_status(z, change)
            is_pips_pair = any(target in name for target in ["EUR/USD", "GBP/USD", "AUD/USD"])
            fmt = ",.4f" if is_pips_pair else ",.2f"
            
            results[name] = {"price": curr_p, "change": change, "status": status, "icon": icon, "class": css_class, "history": series, "fmt": fmt}

    # --- 総合パネル ---
    with tabs[0]:
        selected = st.multiselect("ウォッチリスト", list(results.keys()), default=["USD/JPY", "S&P500", "USD Index", "VIX指数"])
        cols = st.columns(2) 
        for i, name in enumerate(selected):
            res = results.get(name)
            if res:
                with cols[i % 2]:
                    st.markdown(f"""
                        <div class="metric-card {res['class']}">
                            <div class="label-text">{name}</div>
                            <div class="price-text">{res['price']:{res['fmt']}}</div>
                            <div style="color: {'#ff4b4b' if res['change'] >= 0 else '#00ff00'};">{'▲' if res['change'] >= 0 else '▼'} {abs(res['change']):.2f}%</div>
                        </div>
                    """, unsafe_allow_html=True)

    # --- 為替詳細（スマホ最適化） ---
    with tabs[1]:
        st.subheader("FX pairs")
        for name in [n for n in results.keys() if "/" in n]:
            res = results[name]
            st.metric(name, f"{res['price']:{res['fmt']}}", f"{res['change']:.2f}%")
            st.line_chart(res['history'].tail(40), height=180)
            st.divider()

    # --- 株式指数 ---
    with tabs[2]:
        for name in ASSETS["主要指数"].keys():
            res = results.get(name)
            if res:
                st.write(f"### {name}")
                st.line_chart(res["history"].tail(60), height=200)

    # --- 金利 ---
    with tabs[3]:
        for name in ASSETS["金利/VIX"].keys():
            res = results.get(name)
            if res:
                st.write(f"### {name}")
                st.line_chart(res["history"].tail(60), height=200)

except Exception as e:
    st.error(f"データ取得中... {e}")
