import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ==========================================
# 0. 網頁基礎配置
# ==========================================
st.set_page_config(page_title="全球量化儀表板 v5", layout="wide")
st.title("🚀 股票量化分析與儀表板 v5")
st.markdown("本系統 *數據為yfinance提供**，技術指標分析 **僅供參考**！")

# ==========================================
# 1. 側邊欄：市場選擇與代碼自動補完
# ==========================================
st.sidebar.header("📥 1. 選擇市場與輸入代碼")
market = st.sidebar.selectbox("選擇市場", ["台股 (上市)", "台股 (上櫃)", "美股", "日股"])
raw_code = st.sidebar.text_input("輸入股票/ETF代碼 (例如: 2330, VOO, 7203)", value="2330")
period = st.sidebar.selectbox("觀察時間範圍", ["5d", "1mo", "3mo", "6mo", "1y"])

ticker_code = raw_code.strip()
if market == "台股 (上市)":
    ticker_code = f"{ticker_code}.TW"
elif market == "台股 (上櫃)":
    ticker_code = f"{ticker_code}.TWO"
elif market == "日股":
    ticker_code = f"{ticker_code}.T"

st.sidebar.info(f"系統最終查詢代碼: `{ticker_code}`")

# ==========================================
# 2. 原生指標計算核心
# ==========================================
def calculate_all_advanced_indicators(df):
    # A. 移動平均線 (SMA)
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['VolMA10'] = df['Volume'].rolling(window=10).mean()
    
    # B. 布林通道 (BBands) - 20日均線 +/- 2倍標準差
    std_20 = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['MA20'] + (std_20 * 2)  # 上軌 (壓力線)
    df['BB_Lower'] = df['MA20'] - (std_20 * 2)  # 下軌 (支撐線)
    
    # C. KD 隨機指標 (9, 3, 3)
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
    
    # D. RSI 相對強弱指標 (14日)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI14'] = (100 - (100 / (1 + rs))).fillna(50)
    
    # E. MACD 指標 (12, 26, 9)
    df['UpMove'] = df['High'].diff()
    df['DownMove'] = df['Low'].shift(1) - df['Low']
    
    # 計算 +DM 和 -DM
    df['PlusDM'] = np.where((df['UpMove'] > df['DownMove']) & (df['UpMove'] > 0), df['UpMove'], 0)
    df['MinusDM'] = np.where((df['DownMove'] > df['UpMove']) & (df['DownMove'] > 0), df['DownMove'], 0)
    
    # 🟢 修正後的 TR 原生矩陣寫法：
    df['TR'] = pd.concat([
        df['High'] - df['Low'], 
        (df['High'] - df['Close'].shift(1)).abs(), 
        (df['Low'] - df['Close'].shift(1)).abs()
    ], axis=1).max(axis=1)
    
    # 用平滑移動平均計算 14 日總和
    tr_14 = df['TR'].rolling(window=14).sum()
    df['PlusDI'] = (df['PlusDM'].rolling(window=14).sum() / tr_14 * 100).fillna(0)
    df['MinusDI'] = (df['MinusDM'].rolling(window=14).sum() / tr_14 * 100).fillna(0)
    df['DX'] = ((df['PlusDI'] - df['MinusDI']).abs() / (df['PlusDI'] + df['MinusDI']) * 100).fillna(0)
    df['ADX'] = df['DX'].rolling(window=14).mean().fillna(0)
    
    # G. 20日 乖離率 BIAS
    df['BIAS20'] = ((df['Close'] - df['MA20']) / df['MA20']) * 100
    
    return df

# ==========================================
# 3. 數據抓取與渲染
# ==========================================
if ticker_code:
    with st.spinner("正在向全球金融資料庫請求數據中..."):
        stock = yf.Ticker(ticker_code)
        df_raw = stock.history(period="1y") 
        
    if not df_raw.empty:
        df_calc = calculate_all_advanced_indicators(df_raw)
        
        # 提取最新一天（今天）與前一天（昨天）的數據做時序比對
        latest = df_calc.iloc[-1]
        yesterday = df_calc.iloc[-2] if len(df_calc) > 1 else latest
        
        # =====================================================================
        # 🛡️ 【API 限流熔斷防禦】防止 Streamlit 雲端共用 IP 遭到 Yahoo 封鎖
        # =====================================================================
        info = {}
        fetched_name = None
        
        try:
            # 嘗試抓取 info，如果被 yfinance 限流鎖 IP 就在此處攔截，不讓 App 閃退
            info = stock.info
            if isinstance(info, dict):
                fetched_name = info.get('shortName') or info.get('longName')
        except Exception as e:
            # 雲端被鎖 IP 時，在後台留個紀錄，前端不噴紅字
            fetched_name = None
            
        # 智慧名稱拼裝防禦
        stock_display_title = f"{fetched_name} ({ticker_code})" if fetched_name else f"{market} - {raw_code.strip()}"
        st.subheader(f"📊 交易數據看板 ➔ {stock_display_title}")
        
        # 數據看板排版 (Metrics) - 全面改用安全 get 語法
        prev_close = df_raw['Close'].iloc[-2] if len(df_raw) > 1 else latest['Close']
        change_val = latest['Close'] - prev_close
        change_pct = (change_val / prev_close) * 100
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("最新收盤價 (Close)", f"{latest['Close']:.2f}", f"{change_val:+.2f} ({change_pct:+.2f}%)")
        m2.metric("今日成交量", f"{int(latest['Volume']):,}")
        
        # 如果 info 有被鎖，本益比與淨值比就優雅地顯示 'N/A'，絕不閃退
        pe_ratio = info.get('trailingPE') if isinstance(info, dict) else None
        pb_ratio = info.get('priceToBook') if isinstance(info, dict) else None
        
        m3.metric("本益比 (PE Ratio)", f"{pe_ratio:.2f}" if pe_ratio else "N/A")
        m4.metric("股價淨值比 (PB Ratio)", f"{pb_ratio:.2f}" if pb_ratio else "N/A")
        # =====================================================================
        
        # Plotly 智慧多線圖 (加入布林通道讓圖表層次更強)
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
        fig.update_layout(margin=dict(l=20, r=20, t=20, b=20), hovermode="x unified", xaxis=dict(title="日期"), yaxis=dict(title="價格", autorange=True, fixedrange=False), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        
        # ==========================================
        # 4. 新手指標診斷大教室 (時序升級版)
        # ==========================================
        st.write("---")
        st.write("## 🎓 全方位量化指標診斷與數據提示")
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("### 🏹 短線與中軌動能指標 (KD / RSI / 布林 / 乖離)")
            st.write("---")
            
            # --- 💡 1. KD (時序交叉提示升級) ---
            ck, cd = latest.get('K', 50), latest.get('D', 50)
            yk, yd = yesterday.get('K', 50), yesterday.get('D', 50)
            
            with st.container(border=True):
                st.markdown("📘 K線是衝鋒官，D線是慢指揮官。當 K線往上穿過 D線叫**黃金交叉**（買訊）；往下穿過叫**死亡交叉**（賣訊）。")
            
            st.write(f"📊 **當前數值**： 今天 K=`{ck:.1f}` , D=`{cd:.1f}` | 昨天 K=`{yk:.1f}` , D=`{yd:.1f}`")
            
            # 動態交叉比對大聲公
            if yk < yd and ck > cd:
                st.success("🔥 **【📢 系統偵測：KD 黃金交叉！】** 衝鋒官 K 線正式向上擊穿 D 線！短線多頭動能引爆，高機率出現連續反彈拉升！")
            elif yk > yd and ck < cd:
                st.error("🚨 **【📢 系統偵測：KD 死亡交叉！】** 衝鋒官 K 線跌破 D 線防線！短線買盤力道竭盡，需防範急跌洗盤風險！")
            
            # 原本的精細化級距判斷
            if ck < 20: st.success("🟢 **【低檔極度超賣區 (KD < 20)】**：股價嚴重跌過頭，技術性反彈蓄勢待發。")
            elif 20 <= ck <= 35: st.success("🟢 **【低檔弱勢打底區 (20 ~ 35)】**：賣壓減弱，股票正在嘗試尋找地板。")
            elif 35 < ck < 65: st.info("🟡 **【多空常態盤整區 (35 ~ 65)】**：多空雙方力量均衡，跟隨大趨勢震盪。")
            elif 65 <= ck <= 80: st.warning("🔴 **【高檔強勢鈍化區 (65 ~ 80)】**：買氣強勁，強勢股常在此區間連續鎖碼上漲。")
            elif ck > 80: st.warning("🔴 **【高檔極度超買區 (KD > 80)】**：市場熱度瀕臨極限，短線隨時有拉回風險，切勿盲目滿倉追高。")

            st.write("---")
            
            # --- 💡 2. 布林通道全新登場 (中線防守) ---
            c_close, c_upper, c_lower, c_ma20 = latest['Close'], latest['BB_Upper'], latest['BB_Lower'], latest['MA20']
            with st.container(border=True):
                st.markdown("📘 *它是利用標準差畫出來的「股價活動貨櫃」。95% 的時間股價只會在上下軌之間移動。撞上軌代表買氣爆表，撞下軌代表跌到便宜區。")
            st.write(f"📊 **當前位置**： 上軌=`{c_upper:.2f}` | 月線=`{c_ma20:.2f}` | 下軌=`{c_lower:.2f}`")
            
            if c_close >= c_upper:
                st.warning("🚨 **【股價強勢突破上軌！】** 目前股價衝破布林通道天花板，屬於極端強勢的多頭噴發，但散戶此時進場容易追在最高點，建議等待拉回中軌（月線）再布局。")
            elif c_close <= c_lower:
                st.success("✅ **【股價跌破下軌支撐！】** 股價跌出地板線，統計學上這屬於『非理性極度超跌』，通常很快就會被橡皮筋拉回通道內部，長線價值投資者會在此處尋找黃金買點。")
            else:
                st.info("ℹ️ **【通道內正常運行】** 股價在箱體內震盪。若股價站在月線之上屬於偏多，月線之下屬於偏空。")

            st.write("---")
            
            # --- 💡 3. RSI ---
            crsi = latest.get('RSI14', 50)
            with st.container(border=True):
                st.markdown("📘 檢驗投資人貪婪或恐慌的溫度計。天天大漲逼近100，天天暴跌逼近0。")
            st.write(f"📊 **當前數值**： RSI (14日) = `{crsi:.1f}`")
            if crsi > 75: st.warning("🚨 **【極度貪婪區 (RSI > 75)】**：買氣瀕臨天花板，新手需提高警覺。")
            elif 60 <= crsi <= 75: st.warning("📈 **【多方強勢主導 (60 ~ 75)】**：股票處於健康的上升軌道中。")
            elif 40 < crsi < 60: st.info("ℹ️ **【多空拉鋸常態 (40 ~ 60)】**：市場情緒穩定，無極端情緒。")
            elif 25 <= crsi <= 40: st.success("📉 **【空方壓制打底 (25 ~ 40)】**：市場情緒低迷，多方正嘗試建立防線。")
            elif crsi < 25: st.success("🔥 **【極度恐慌區 (RSI < 25)】**：非理性拋售，遍地都是便宜的血淚籌碼。")

        with col_right:
            st.markdown("### 🛡️ 中長線波段與大戶籌碼趨勢 (MACD / DMI / 均線)")
            st.write("---")
            
            # --- 💡 4. MACD (昨今動能對比修正) ---
            cmacd, csignal, chist = latest.get('MACD_Line', 0), latest.get('MACD_Signal', 0), latest.get('MACD_Hist', 0)
            ymacd, ysignal, yhist = yesterday.get('MACD_Line', 0), yesterday.get('MACD_Signal', 0), yesterday.get('MACD_Hist', 0)
            
            with st.container(border=True):
                st.markdown("📘 用來觀察中線的大波段方向。柱狀體（Hist）在零軸之上代表多頭控盤，零軸之下代表空頭沉淪。")
            
            # 修正核心：直接計算動能差，讓比較完全具體化！
            hist_delta = chist - yhist
            trend_arrow = "🔺 增加" if hist_delta > 0 else "🔻 減少"
            st.write(f"📊 **今天數據**： 快線=`{cmacd:.2f}` | 慢線=`{csignal:.2f}` | 柱狀體=`{chist:.2f}`")
            st.write(f"⏱️ **昨今比對**： 柱狀體動能較昨天 `{trend_arrow} ({hist_delta:+.3f})`")
            
            # 交叉大聲公
            if yhist < 0 and chist > 0:
                st.success("🔥 **【📢 MACD 黃金交叉！】** 柱狀體由負轉正，代表中線大波段多頭攻勢正式發動，是一張極具參考價值的波段波段門票！")
            elif yhist > 0 and chist < 0:
                st.error("🚨 **【📢 MACD 死亡交叉！】** 柱狀體由正轉負，代表中線多頭波段宣告結束，高機率迎來週線級別的大型修正！")
            elif chist > 0:
                if hist_delta > 0: st.success("🟢 **多頭動能持續增強：** 柱狀體在零軸之上且越拉越長，代表多頭大客車正在油門踩到底全力加速！")
                else: st.warning("🟡 **多頭動能開始衰退：** 雖然股價還在漲，但柱狀體已經比昨天縮短，暗示多方力道開始腳軟，小心高檔震盪。")
            else:
                if hist_delta < 0: st.error("🔴 **空頭動能持續擴大：** 柱狀體在零軸之下且越跌越深，代表空方砸盤力道猛烈，絕對不要進去接刀！")
                else: st.success("🍏 **空頭賣壓開始收斂：** 柱狀體在零軸之下但已經開始往上縮短，代表最恐怖的暴跌期可能過去，多方正嘗試止跌。")

            st.write("---")
            
            # --- 💡 5. DMI 趨勢指標 ---
            c_pdi, c_mdi, c_adx = latest.get('PlusDI', 0), latest.get('MinusDI', 0), latest.get('ADX', 0)
            with st.container(border=True):
                st.markdown("📘 +DI是買盤狠勁，-DI是賣盤砸盤力道。ADX是大戶發動引擎，ADX > 25 代表大戶正式飆車。")
            st.write(f"📊 **當前數值**： 多方+DI = `{c_pdi:.1f}` | 空方-DI = `{c_mdi:.1f}` | 引擎ADX = `{c_adx:.1f}`")
            
            if c_adx > 25:
                if c_pdi > c_mdi: st.success(f"🔥 **【DMI 爆發：多頭猛烈開車！】** 引擎 ADX (`{c_adx:.1f}`) 突破 25 且多方佔優。代表大戶大筆資金融資鎖碼，這是一段強悍的順風主升段！")
                else: st.error(f"🚨 **【DMI 爆發：空頭猛烈出貨！】** 引擎 ADX (`{c_adx:.1f}`) 突破 25 且空方壓制。代表法人主力不計代價瘋狂倒貨，進去接必套牢！")
            else:
                st.info("🟡 **【DMI 提示：大戶休兵死魚盤】** ADX 低於 25，代表目前無方向性。股價高機率在箱型區間內反覆上下洗盤。")
                
            st.write("---")
            
            # --- 💡 6. 均線與流動性防禦 ---
            c_ma60 = latest['MA60']
            st.markdown("### 📦 長線戰略位置與流動性防禦")
            if c_close > c_ma60: st.info(f"🔵 **長線季線防守 ({c_ma60:.2f})：** 股價在季線之上，法人長期保護傘依舊撐著，大趨勢安全。")
            else: st.warning(f"🟠 **長線季線套牢 ({c_ma60:.2f})：** 股價在季線之下，長線大趨勢走弱，不宜過度重倉。")
            
            current_hour_minute = datetime.now().strftime("%H:%M")
            if "09:00" <= current_hour_minute <= "11:30":
                st.warning(f"⏳ **早盤防禦中 ({current_hour_minute})**：已暫停量縮警報。")
            else:
                if latest['Volume'] < (latest['VolMA10'] * 0.7): st.error("⚠️ **警告：成交量嚴重萎縮！** 今日量能遠低於均量，新手注意流動性風險。")
                else: st.success("🟢 **交易量能正常**。")
