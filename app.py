import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- ページ設定 ---
st.set_page_config(page_title="Chief Dealer Dashboard Pro", layout="wide")

# --- カスタムCSS ---
st.markdown("""
    <style>
    .metric-card {
        background-color: #1e1e1e; border-radius: 4px; padding: 12px;
        border-left: 6px solid #333; margin-bottom: 10px; color: white;
    }
    .status-good { border-left-color: #00bfff; background-color: #001a33; }
    .status-stable { border-left-color: #00ff00; }
    .status-warning { border-left-color: #ff4500; }
    .status-critical { border-left-color: #ff0000; background-color: #3d0000; }
    .price-text { font-size: 1.8rem; font-weight: bold; line-height: 1.2; }
    .label-text { font-size: 0.9rem; color: #aaa; }
    </style>
""", unsafe_allow_html=True)

# --- 銘柄リスト定義（大幅拡張） ---
ASSETS = {
    "為替": {
        "USD/JPY": "USDJPY=X", "EUR/USD": "EURUSD=X", "EUR/JPY": "EURJPY=X",
        "GBP/USD": "GBPUSD=X", "GBP/JPY": "GBPJPY=X",
        "AUD/USD": "AUDUSD=X", "AUD/JPY": "AUDJPY=X"
    },
    "通貨指数": {
        "USD Index": "UUP", "JPY Index(FXY)": "FXY"
    },
    "米国株/ハイテク": {
        "S&P500": "^GSPC", "NYダウ": "^DJI", "SOX指数": "^SOX", "Nasdaq100": "^NDX"
    },
    "欧州/アジア株": {
        "日経225": "^N225", "独DAX": "^GDAXI", "英FTSE": "^FTSE", "上海総合": "000001.SS"
    },
    "金利/VIX": {
        "米10年債": "^TNX", "米2年債(Fed期待)": "^ZVQ", "VIX指数": "^VIX"
    },
    "ｺﾓﾃﾞｨﾃｨ/他": {
        "ゴールド": "GC=F", "原油": "CL=F", "ハイイールド債": "HYG"
    }
}

def get_advanced_status(z_score, return_val):
    if z_score < 1.0: return "平常時", "🟢", "status-stable"
    if return_val > 0: return "良好・過熱", "🔵", "status-good"
    return ("急落・警戒" if z_score > 2.0 else "注意・下落"), ("🔴" if z_score > 2.0 else "🟠"), ("status-critical" if z_score > 2.0 else "status-warning")

@st.cache_data(ttl=600)
def fetch_all_data(_tickers):
    # Close価格を一括取得
    data = yf.download(list(_tickers), period="1y", interval="1d", progress=False)['Close']
    return data

# --- メイン処理 ---
st.title("🛡️ Strategic Market Dashboard Pro")
tabs = st.tabs(["📊 総合パネル", "💱 為替/IMM", "📈 金利/VIX", "📉 株式/指数詳細"])

tickers_map = {name: ticker for cat in ASSETS.values() for name, ticker in cat.items()}

try:
    prices_df = fetch_all_data(list(tickers_map.values()))
    results = {}
    
    for name, ticker in tickers_map.items():
        if ticker in prices_df:
            series = prices_df[ticker].dropna()
            if series.empty: continue
            
            rets = np.log(series / series.shift(1))
            vol = rets.rolling(20).std() * np.sqrt(252)
            z = (vol.iloc[-1] - vol.mean()) / vol.std() if not vol.empty else 0
            curr_p = series.iloc[-1]
            change = (curr_p / series.iloc[-2] - 1) * 100
            
            status, icon, css_class = get_advanced_status(z, change)
            is_pips_pair = any(target in name for target in ["EUR/USD", "GBP/USD", "AUD/USD"])
            fmt = ",.4f" if is_pips_pair else ",.2f"
            
            results[name] = {"price": curr_p, "change": change, "status": status, "icon": icon, "class": css_class, "history": series, "fmt": fmt}

    with tabs[0]:
        st.sidebar.header("表示銘柄の選択")
        options = list(results.keys())
        default_sel = [x for x in ["USD/JPY", "S&P500", "日経225", "VIX指数", "USD Index", "SOX指数"] if x in options]
        selected = st.sidebar.multiselect("ウォッチリストに追加", options, default=default_sel)
        
        cols = st.columns(4)
        for i, name in enumerate(selected):
            res = results.get(name)
            if res:
                with cols[i % 4]:
                    st.markdown(f"""
                        <div class="metric-card {res['class']}">
                            <div class="label-text">{name}</div>
                            <div class="price-text">{res['price']:{res['fmt']}}</div>
                            <div style="color: {'#ff4b4b' if res['change'] >= 0 else '#00ff00'};">
                                {'▲' if res['change'] >= 0 else '▼'} {abs(res['change']):.2f}%
                            </div>
                            <div style="font-size: 0.85rem; font-weight: bold; margin-top:5px;">{res['icon']} {res['status']}</div>
                        </div>
                    """, unsafe_allow_html=True)

    with tabs[3]:
        st.subheader("Global Equity Indices")
        # 4列のチャート表示
        idx_cols = st.columns(2)
        target_indices = ["S&P500", "NYダウ", "SOX指数", "日経225", "独DAX", "英FTSE", "上海総合"]
        
        for i, name in enumerate(target_indices):
            res = results.get(name)
            if res:
                with idx_cols[i % 2]:
                    st.write(f"### {name}")
                    st.line_chart(res["history"].tail(60))

except Exception as e:
    st.error(f"システムエラーが発生しました: {e}")