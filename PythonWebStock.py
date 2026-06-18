import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz  # 🌍 全球多市場動態時區核心庫

# ==========================================
# 0. 網頁基礎配置
# ==========================================
st.set_page_config(page_title="全球量化儀表板 v7.0", layout="wide")
st.title("🚀 全球股票量化分析與教學儀表板 v7.0")
st.markdown("本系統 **數據為yfinance提供**，技術指標分析 **僅供參考**！")

# ==========================================
# 1. 側邊欄：常用清單與市場選擇 (V7.1 雙層動態聯動版)
# ==========================================
st.sidebar.header("🎯 1. 常用股票群組選單")

# 📥 【主管專屬核心配置區】你和朋友的清單直接在這裡分開寫死
cascading_stock_pool = {
    "👤 短中線查詢": {
        "自訂輸入 (手動輸入代碼)": "CUSTOM",        
        "野村臺灣科技 (00935.TW)": "00935.TW",
        "統一台灣主動 (00981A.TW)": "00981A.TW",
        "統一全球主動 (00988A.TW)": "00988A.TW",
        "元大台灣50正2 (00631L)": "00631L.TW",
        "群益台灣正2 (00685L)": "00685L.TW",
        "富邦NASDAQ正2 (00670L)": "00670L.TW"
    },
    "👥 蘇大衛用清單": {
        "自訂輸入 (手動輸入代碼)": "CUSTOM",
        "微軟 (MSFT)": "MSFT",
        "輝達 (NVDA)": "NVDA",
        "Alphabet (Google)": "GOOG",
        "Spac (SPCX)": "SPCX",
        "追蹤標普500 (VOO)": "VOO"
    },
    "🔥 長線查詢": {
        "自訂輸入 (手動輸入代碼)": "CUSTOM",
        "台積電 (2330.TW)": "2330.TW",
        "群益高股息 (00919.TW)": "00919.TW",
        "美國科技研發 (00971.TW)": "00971.TW",
        "富邦NASDAQ (00662.TW)": "00662.TW",
        "國泰費半 (00830.TW)": "00830.TW"
        
    },
    "🇯🇵 日股觀測站": {
        "自訂輸入 (手動輸入代碼)": "CUSTOM",
        "日本商社 (00955.TWO)": "00955.TWO",
        "日本半導體 (00954.TW)": "00954.TW",
        "東京電子 (8035.T)": "8035.T",
        "愛德萬測試 (6857.T)": "6857.T",
        "KIOXIA (285A.T)": "285A.T",
        "富邦日本正2 (00640L.TW)": "00640L.TW",
        "元大日經225 (00661.TW)": "00661.TW",
        "Cover (Holo)": "5253.T",
        "Anycolor (彩虹)": "5032.T"
    }
}

# 🎛️ 第一層選單：先選擇你是誰，或想看哪個群組
selected_group = st.sidebar.selectbox("選擇股票群組 (A 欄)", list(cascading_stock_pool.keys()))

# 🔄 動態撈取該群組對應的股票清單
available_stocks = cascading_stock_pool[selected_group]

# 🎛️ 第二層選單：根據第一層的結果，動態顯示對應的股票 (預設選第一個選項)
selected_stock_name = st.sidebar.selectbox(f"選擇 {selected_group} 的股票 (B 欄)", list(available_stocks.keys()))

# 取得最終要查詢的代碼
fav_code = available_stocks[selected_stock_name]

st.sidebar.write("---")
st.sidebar.header("📥 2. 手動微調市場與代碼")

# 連動市場與預設代碼判定邏輯 (完全相容原系統)
if fav_code != "CUSTOM":
    if ".TWO" in fav_code:
        default_market = "台股 (上櫃)"
        default_code = fav_code.replace(".TWO", "")
    elif ".TW" in fav_code:
        default_market = "台股 (上市)"
        default_code = fav_code.replace(".TW", "")
    elif ".T" in fav_code:
        default_market = "日股"
        default_code = fav_code.replace(".T", "")
    else:
        default_market = "美股"
        default_code = fav_code
else:
    default_market = "台股 (上市)"
    default_code = "2330"

market = st.sidebar.selectbox("選擇市場", ["台股 (上市)", "台股 (上櫃)", "美股", "日股"], index=["台股 (上市)", "台股 (上櫃)", "美股", "日股"].index(default_market))
raw_code = st.sidebar.text_input("輸入股票/ETF代碼", value=default_code)
period = st.sidebar.selectbox("觀察時間範圍", ["5d", "1mo", "3mo", "6mo", "1y"], index=4)

ticker_code = raw_code.strip()
if market == "台股 (上市)" and not ticker_code.endswith(".TW"):
    ticker_code = f"{ticker_code}.TW"
elif market == "台股 (上櫃)" and not ticker_code.endswith(".TWO"):
    ticker_code = f"{ticker_code}.TWO"
elif market == "日股" and not ticker_code.endswith(".T"):
    ticker_code = f"{ticker_code}.T"

st.sidebar.info(f"系統最終查詢代碼: `{ticker_code}`")

# ==========================================
# 2. 原生指標計算核心
# ==========================================
def calculate_all_advanced_indicators(df):
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['VolMA10'] = df['Volume'].rolling(window=10).mean()
    
    std_20 = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['MA20'] + (std_20 * 2)
    df['BB_Lower'] = df['MA20'] - (std_20 * 2)
    
    low_9 = df['Low'].rolling(window=9).min()
    high_9 = df['High'].rolling(window=9).max()
    rsv = ((df['Close'] - low_9) / (high_9 - low_9) * 100).fillna(50)
    
    k_list, d_list = [], []
    current_k, current_d = 50.0, 50.0
    for r in rsv:
        current_k = (1/3) * r + (2/3) * current_k
        current_d = (1/3) * current_k + (2/3) * current_d
        k_list.append(current_k)
        d_list.append(current_d)
    df['K'], df['D'] = k_list, d_list
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI14'] = (100 - (100 / (1 + rs))).fillna(50)
    
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD_Line'] = ema12 - ema26                         
    df['MACD_Signal'] = df['MACD_Line'].ewm(span=9, adjust=False).mean() 
    df['MACD_Hist'] = df['MACD_Line'] - df['MACD_Signal']   
    
    df['UpMove'] = df['High'].diff()
    df['DownMove'] = df['Low'].shift(1) - df['Low']
    df['PlusDM'] = np.where((df['UpMove'] > df['DownMove']) & (df['UpMove'] > 0), df['UpMove'], 0)
    df['MinusDM'] = np.where((df['DownMove'] > df['UpMove']) & (df['DownMove'] > 0), df['DownMove'], 0)
    
    df['TR'] = pd.concat([
        df['High'] - df['Low'], 
        (df['High'] - df['Close'].shift(1)).abs(), 
        (df['Low'] - df['Close'].shift(1)).abs()
    ], axis=1).max(axis=1)
    
    tr_14 = df['TR'].rolling(window=14).sum()
    df['PlusDI'] = (df['PlusDM'].rolling(window=14).sum() / tr_14 * 100).fillna(0)
    df['MinusDI'] = (df['MinusDM'].rolling(window=14).sum() / tr_14 * 100).fillna(0)
    df['DX'] = ((df['PlusDI'] - df['MinusDI']).abs() / (df['PlusDI'] + df['MinusDI']) * 100).fillna(0)
    df['ADX'] = df['DX'].rolling(window=14).mean().fillna(0)
    
    df['BIAS20'] = ((df['Close'] - df['MA20']) / df['MA20']) * 100
    
    return df

# ==========================================
# 3. 數據抓取與渲染
# ==========================================
if ticker_code:
    with st.spinner("正在向全球金融資料庫請求數據中..."):
        stock = yf.Ticker(ticker_code)
        # A 通道：抓 1y 數據做圖與技術分析，確保加載流暢
        df_raw = stock.history(period="1y") 
        # B 通道：抓 5y 長線數據跨越景氣多空循環
        df_risk_raw = stock.history(period="5y")
        
    if not df_raw.empty:
        # 🛡️ 開盤前空資料過濾機制
        if len(df_raw) > 1 and (df_raw['Volume'].iloc[-1] == 0 or pd.isna(df_raw['Open'].iloc[-1])):
            df_raw = df_raw.iloc[:-1]
            
        df_calc = calculate_all_advanced_indicators(df_raw)
        latest = df_calc.iloc[-1]
        yesterday = df_calc.iloc[-2] if len(df_calc) > 1 else latest
        
        # ==========================================
        # 📊 核心風控指標手刻運算區 (嚴謹1年熔斷防線)
        # ==========================================
        annual_volatility = None
        annual_sharpe = None
        sample_years_label = "1年期"
        has_enough_data = True
        
        if not df_risk_raw.empty:
            total_days = len(df_risk_raw)
            
            # 🛡️ 判定是否為「未滿 1 年的小鮮肉股」，少於 200 天直接封鎖長線指標
            if total_days < 200:
                has_enough_data = False
            else:
                if total_days >= 1200:
                    df_target = df_risk_raw
                    sample_years_label = "5年期"
                elif total_days >= 720:
                    df_target = df_risk_raw.tail(720)
                    sample_years_label = "3年期"
                else:
                    df_target = df_risk_raw.tail(252)
                    sample_years_label = "1年期"
                    
                try:
                    # 執行國際標準化年化風控運算
                    risk_returns = df_target['Close'].pct_change().dropna()
                    avg_daily_return = risk_returns.mean()
                    daily_std = risk_returns.std()
                    
                    # 年化標準差 (波動度)
                    annual_volatility = daily_std * np.sqrt(252) * 100
                    
                    # 國際標準年化夏普比率 (扣除台灣定存 1.5% 無風險利率常數)
                    if daily_std > 0:
                        daily_rf = 0.015 / 252
                        annual_sharpe = ((avg_daily_return - daily_rf) / daily_std) * np.sqrt(252)
                    else:
                        annual_sharpe = 0.0
                except Exception:
                    pass

        # API 限流熔斷防禦
        info = {}
        fetched_name = None
        try:
            info = stock.info
            if isinstance(info, dict):
                fetched_name = info.get('shortName') or info.get('longName')
        except Exception:
            fetched_name = None
            
        stock_display_title = f"{fetched_name} ({ticker_code})" if fetched_name else f"{market} - {raw_code.strip()}"
        st.subheader(f"📊 交易數據看板 ➔ {stock_display_title}")
        
        # 數據看板主排版 (最新價與量)
        prev_close = df_raw['Close'].iloc[-2] if len(df_raw) > 1 else latest['Close']
        change_val = latest['Close'] - prev_close
        change_pct = (change_val / prev_close) * 100
        
        m1, m2 = st.columns(2)
        m1.metric("最新收盤價 (Close)", f"{latest['Close']:.2f}", f"{change_val:+.2f} ({change_pct:+.2f}%)")
        m2.metric("今日成交量", f"{int(latest['Volume']):,}")
        
        # --- 📈 估值與風控雙大看板排版 ---
        c_val, c_risk = st.columns(2)
        
        with c_val:
            st.write("### 🔍 基本面四大估值指標")
            ev1, ev2, ev3, ev4 = st.columns(4)
            pe_ratio = info.get('trailingPE') if isinstance(info, dict) else None
            pb_ratio = info.get('priceToBook') if isinstance(info, dict) else None
            ps_ratio = info.get('priceToSalesTrailing12Months') if isinstance(info, dict) else None
            peg_ratio = info.get('pegRatio') if isinstance(info, dict) else None
            
            ev1.metric("本益比 (P/E)", f"{pe_ratio:.2f}" if pe_ratio else "N/A", help="適合常態獲利穩定公司。")
            ev2.metric("股價淨值比 (P/B)", f"{pb_ratio:.2f}" if pb_ratio else "N/A", help="適合景氣循環股、傳統產業。")
            ev3.metric("股價營收比 (P/S)", f"{ps_ratio:.2f}" if ps_ratio else "N/A", help="適合營收暴發但獲利尚未穩定的AI新創。")
            ev4.metric("本益成長比 (PEG)", f"{peg_ratio:.2f}" if peg_ratio else "N/A", help="低於1代表高成長支撐高本益比，股價並不算貴。")

        with c_risk:
            st.write(f"### 🛡️ 長線風險控網 ({sample_years_label if has_enough_data else '未滿1年多空歷史'})")
            
            if not has_enough_data:
                st.info("ℹ️ **該標的上市未滿 1 年**：歷史樣本數不足，長線風險指標不具統計參考價值，系統已自動啟動防護性留白。")
            else:
                rv1, rv2, rv3 = st.columns(3)
                beta_val = info.get('beta') if isinstance(info, dict) else None
                
                rv1.metric("Beta 震盪係數", f"{beta_val:.2f}" if beta_val else "N/A", help="大盤震盪度為 1。高於 1 代表比大盤更活潑、波動更大。")
                rv2.metric("年化波動度 (標準差)", f"{annual_volatility:.1f}%" if annual_volatility else "N/A", help=f"這檔股票在過去{sample_years_label}經歷多空大洗牌時的總體風險脾氣。")
                rv3.metric("夏普比率 (Sharpe)", f"{annual_sharpe:.2f}" if annual_sharpe else "N/A", help=f"這檔股票跨越{sample_years_label}長線循環後的風險CP值。")

        # Plotly 智慧多線圖
        slice_dict = {"5d":5, "1mo":20, "3mo":60, "6mo":120, "1y":240}
        df_chart = df_calc.tail(slice_dict.get(period, 60)).dropna(subset=['Close', 'MA5', 'MA20'])
        
        st.write("### 📈 價格、均線與布林通道走勢圖")
        columns_to_plot = ['Close', 'MA5', 'MA20', 'BB_Upper', 'BB_Lower']
        if period not in ["5d", "1mo"]:
            df_chart = df_chart.dropna(subset=['MA60'])
            columns_to_plot.append('MA60')
            
        import plotly.graph_objects as go
        fig = go.Figure()
        for col in columns_to_plot:
            dash_style = 'dash' if 'BB_' in col else 'solid'
            width_style = 1.5 if 'BB_' in col else 2.5
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart[col], mode='lines', name=col, line=dict(dash=dash_style, width=width_style)))
        fig.update_layout(margin=dict(l=20, r=20, t=20, b=20), hovermode="x unified", template="plotly_dark", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)
        
        # ==========================================
        # 4. 新手指標診斷大教室 (全數據回歸防撞車版)
        # ==========================================
        st.write("---")
        st.write("## 🎓 全方位量化指標精細診斷與白話文教學")
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("### 🏹 短線與中軌動能指標")
            st.write("---")
            
            # --- KD ---
            ck, cd = latest.get('K', 50), latest.get('D', 50)
            yk, yd = yesterday.get('K', 50), yesterday.get('D', 50)
            with st.container(border=True):
                st.markdown("📘 **KD 指標: **\n K線是衝鋒官，D線是慢指揮官。當 K線往上穿過 D線叫**黃金交叉**（買訊）；往下穿過叫**死亡交叉**（賣訊）。")
            st.write(f"📊 **當前數值**： 今天 K=`{ck:.1f}` , D=`{cd:.1f}` | 昨天 K=`{yk:.1f}` , D=`{yd:.1f}`")
            if yk < yd and ck > cd: st.success("🔥 **【📢 系統偵測：KD 黃金交叉！】** 短線多頭動能引爆！")
            elif yk > yd and ck < cd: st.error("🚨 **【📢 系統偵測：KD 死亡交叉！】** 短線需防範急跌洗盤風險！")
            
            if ck < 20: st.success("🟢 **【低檔極度超賣區 (KD < 20)】**：股價嚴重跌過頭。")
            elif 20 <= ck <= 35: st.success("🟢 **【低檔弱勢打底區 (20 ~ 35)】**：正在嘗試尋找地板。")
            elif 35 < ck < 65: st.info("🟡 **【多空常態盤整區 (35 ~ 65)】**：隨大趨勢震盪。")
            elif 65 <= ck <= 80: st.warning("🔴 **【高檔強勢鈍化區 (65 ~ 80)】**：買氣強勁，強勢股常在此上漲。")
            elif ck > 80: st.warning("🔴 **【高檔極度超買區 (KD > 80)】**：市場熱度瀕臨極限。")

            st.write("---")
            
            # --- 布林通道 ---
            c_close, c_upper, c_lower, c_ma20 = latest['Close'], latest['BB_Upper'], latest['BB_Lower'], latest['MA20']
            with st.container(border=True):
                st.markdown("📘 **布林通道: **\n95% 的時間股價只會在上下軌之間移動。")
            st.write(f"📊 **當前位置**： 上軌=`{c_upper:.2f}` | 月線=`{c_ma20:.2f}` | 下軌=`{c_lower:.2f}`")
            if c_close >= c_upper: st.warning("🚨 **【股價強勢突破上軌！】** 衝破天花板，小心散戶進場追高。")
            elif c_close <= c_lower: st.success("✅ **【股價跌破下軌支撐！】** 跌出地板線，通常很快就會被橡皮筋拉回。")
            else: st.info("ℹ️ **【通道內正常運行】** 股價在箱體內正常震盪。")

            st.write("---")
            
            # --- RSI ---
            crsi = latest.get('RSI14', 50)
            with st.container(border=True):
                st.markdown("📘 **RSI 指標: **\n檢驗投資人貪婪 or 恐慌的溫度計。")
            st.write(f"📊 **當前數值**： RSI (14日) = `{crsi:.1f}`")
            if crsi > 75: st.warning("🚨 **【極度貪婪區 (RSI > 75)】**：買氣逼近天花板。")
            elif 60 <= crsi <= 75: st.warning("📈 **【多方強勢主導 (60 ~ 75)】**：處於健康的上升軌道中。")
            elif 40 < crsi < 60: st.info("ℹ️ **【多空拉鋸常態 (40 ~ 60)】**：市場情緒穩定。")
            elif 25 <= crsi <= 40: st.success("📉 **【空方壓制打底 (25 ~ 40)】**：處於修正階段。")
            elif crsi < 25: st.success("🔥 **【極度恐慌區 (RSI < 25)】**：遍地都是便宜的血淚籌碼。")

            st.write("---")

            # --- 乖離率 ---
            cbias = latest.get('BIAS20', 0)
            with st.container(border=True):
                st.markdown("📘 **20日乖離率 (BIAS): **\n股價跟月線就像主人牽狗散步，狗跑得太遠最後一定會被扯回來。")
            st.write(f"📊 **當前數值**： 20日乖離率 = `{cbias:+.2f}%`")
            if cbias > 6: st.warning("⚠️ **正乖離過大（狗跑太遠）：** 近期高機率會往月線靠攏拉回。")
            elif cbias < -6: st.success("✅ **負乖離過大（狗落後太多）：**隨時可能出現跌深反彈。")
            else: st.info("ℹ️ 股價與月線距離適中，趨勢發展正常。")

        with col_right:
            st.markdown("### 🛡️ 中長線趨勢與籌碼指標")
            st.write("---")
            
            # --- MACD ---
            chist, yhist = latest.get('MACD_Hist', 0), yesterday.get('MACD_Hist', 0)
            with st.container(border=True):
                st.markdown("📘 **MACD 指標: **\n用來觀察中線的大波段方向。")
            
            # 🛡️ 這裡改用高優先權 st.info 元件，撐開圖層，一輩子不會再被標題撞車啃掉！
            st.info(f"📊 **當前數值**： 快線(DIF)=`{latest.get('MACD_Line',0):.2f}` | 慢線(MACD)=`{latest.get('MACD_Signal',0):.2f}` | 柱狀體(Osc)=`{chist:.2f}`")
            
            hist_delta = chist - yhist
            trend_arrow = "🔺 增加" if hist_delta > 0 else "🔻 減少"
            st.write(f"⏱️ **昨今比對**： 柱狀體動能較昨天 `{trend_arrow} ({hist_delta:+.3f})`")
            if yhist < 0 and chist > 0: st.success("🔥 **【📢 MACD 黃金交叉！】** 中線大波段多頭攻勢正式發動！")
            elif yhist > 0 and chist < 0: st.error("🚨 **【📢 MACD 死亡交叉！】** 高機率迎來週線級別的大型修正！")
            elif chist > 0:
                if hist_delta > 0: st.success("🟢 **多頭動能持續增強：** 柱狀體在零軸之上且越拉越長，大客車正全力加速！")
                else: st.warning("🟡 **多頭動能開始衰退：** 雖然在漲，但柱狀體已比昨天縮短，小心震盪。")
            else:
                if hist_delta < 0: st.error("🔴 **空頭動能持續擴大：** 柱狀體在零軸之下且越跌越深，賣壓猛烈. ")
                else: st.success("🍏 **空頭賣壓開始收斂：** 柱狀體在零軸之下 but 開始上縮，多方嘗試止跌。")

            st.write("---")
            
            # --- DMI ---
            c_pdi, c_mdi, c_adx = latest.get('PlusDI', 0), latest.get('MinusDI', 0), latest.get('ADX', 0)
            with st.container(border=True):
                st.markdown("📘 **DMI 趨勢指標: **\n +DI是買盤狠勁，-DI是賣盤砸盤力道。ADX是大戶發動引擎，ADX > 25 代表大戶正式飆車。")
            st.write(f"📊 **當前數值**： 多方+DI = `{c_pdi:.1f}` | 空方-DI = `{c_mdi:.1f}` | 引擎ADX = `{c_adx:.1f}`")
            if c_adx > 25:
                if c_pdi > c_mdi: st.success(f"🔥 **【DMI 爆發：多頭猛烈開車！】** 這是一段強悍的順風主升段！")
                else: st.error(f"🚨 **【DMI 爆發：空頭猛烈出貨！】** 法人主力不計代價瘋狂倒貨！")
            else: st.info("🟡 **【DMI 提示：大戶休兵死魚盤】** ADX 低於 25，高機率在箱型區間內反覆上下洗盤。")
                
            st.write("---")
            
            # --- 均線與流動性防禦 (V6.9 究極全天候雙向籌碼網) ---
            c_ma60 = latest['MA60']
            st.markdown("### 📦 長線戰略位置與流動性防禦")
            if c_close > c_ma60: st.info(f"🔵 **長線季線防守 ({c_ma60:.2f})：** 股價在季線之上，大趨勢安全。")
            else: st.warning(f"🟠 **長線季線套牢 ({c_ma60:.2f})：** 股價在季線之下，長線大趨勢走弱。")
            
            if "美股" in market:
                target_tz = pytz.timezone('America/New_York')
                market_label = "紐約 (美股)"
                start_defense, end_defense = "09:30", "12:00"
            elif "日股" in market:
                target_tz = pytz.timezone('Asia/Tokyo')
                market_label = "東京 (日股)"
                start_defense, end_defense = "09:00", "11:30"
            else:
                target_tz = pytz.timezone('Asia/Taipei')
                market_label = "台北 (台股)"
                start_defense, end_defense = "09:00", "11:30"
                
            current_time_local = datetime.now(target_tz)
            current_hour_minute = current_time_local.strftime("%H:%M")
            
            # 🏁 終極精細流動性決策樹
            if start_defense <= current_hour_minute <= end_defense:
                # A 區：早盤防禦時段 (隱藏量縮警告，專抓極端早盤開局暴衝)
                if latest['Volume'] >= latest['VolMA10']:
                    st.error(f"💥 **【📢 系統警報：偵測到早盤異常天量！】**\n\n當前時間僅為 {market_label} 當地 {current_hour_minute}，但今日量能 (`{int(latest['Volume']):,}`) 已突破 10日整天均量 (`{int(latest['VolMA10']):,}`)！主力大戶開局即重倉對決，請密切注意股價多空方向！")
                else:
                    st.warning(f"⏳ **【{market_label} 早盤防禦中】** 當地時間 {current_hour_minute}。已自動暫停量縮警報，防止早盤常態性量能未補造成誤判。")
            else:
                # B 區：常態交易/中盤/尾盤時段 (開啟「爆量」與「量縮」全天候雙向攔截網)
                if latest['Volume'] < (latest['VolMA10'] * 0.7): 
                    st.error(f"⚠️ **【警告：成交量嚴重萎縮！】**\n\n(檢測時間: {market_label} 當地 {current_hour_minute}) 今日總成交量僅有 `{int(latest['Volume']):,}`，遠低於均量的 70% (`{int(latest['VolMA10']*0.7):,}`)。請注意市場流動性風險，提防死魚盤或無量陰跌。")
                elif latest['Volume'] >= (latest['VolMA10'] * 1.5):
                    st.error(f"🔥 **【🚨 警告：盤中/尾盤主力異常爆量！】**\n\n(檢測時間: {market_label} 當地 {current_hour_minute}) 當前成交量已衝到 `{int(latest['Volume']):,}`，超越 10日均量的 150% (`{int(latest['VolMA10']*1.5):,}`)！這往往伴隨著法人季底作帳、重大利空/利多突發襲擊、或是尾盤不計代價的出貨與嘎空盤，請務必高度戒備！")
                else: 
                    st.success(f"🟢 **交易量能常態運行**。 (當前檢測時間: {market_label} 當地 {current_hour_minute} | 量能達均量 {int((latest['Volume']/latest['VolMA10'])*100)}%)")
