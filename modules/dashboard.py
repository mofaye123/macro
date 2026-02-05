import streamlit as st
import pandas as pd
import numpy as np
import math
import plotly.graph_objects as go
from datetime import datetime, timedelta
from config import GEMINI_API_KEY
from google import genai

# --- [核心功能]：AI 调用函数 (使用 google-genai SDK) ---
def call_gemini_new_sdk(prompt, api_key):
        client = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})
 
        response = client.models.generate_content(
            model='gemini-3-flash-preview', 
            contents=prompt
        )
        return response.text
       

PROFESSIONAL_LIGHT_CSS = """
<style>
    :root {
        --ui-bg: #f8f9fa;
        --ui-card: #ffffff;
        --ui-border: #e5e7eb;
        --ui-text: #111827;
        --ui-subtext: #6b7280;
        --ui-accent: #2563eb;
        --ui-success: #059669;
        --ui-danger: #dc2626;
        --ui-warn: #f59e0b;
    }
    /* 1. 全局背景：极淡的灰白，护眼 */
    .stApp {
        background-color: var(--ui-bg);
        color: var(--ui-text);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* 2. 卡片样式：纯白底 + 微阴影 (Apple风格) */
    .term-card {
        background: var(--ui-card);
        border: 1px solid var(--ui-border);
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .term-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
        border-color: #d1d5db;
    }

        /* 模块卡片统一高度与底部对齐 */
    .module-card {
        min-height: 240px;
        display: flex;
        flex-direction: column;
        box-sizing: border-box;
    }
    .module-card .module-footer {
        margin-top: auto;
        min-height: 44px;
    }
    .module-card .module-desc {
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    /* 3. 字体颜色定义 (适配浅色底) */
    .text-main { color: var(--ui-text); }
    .text-dim { color: var(--ui-subtext); font-size: 0.85em; font-weight: 500; }
    .text-green { color: var(--ui-success); font-weight: 600; }
    .text-red { color: var(--ui-danger); font-weight: 600; }
    .text-gold { color: #b45309; font-weight: 700; }
    .text-blue { color: var(--ui-accent); }
    
    /* 4. 进度条容器 */
    .progress-bg {
        width: 100%; height: 8px; background: #f3f4f6; border-radius: 4px; margin-top: 12px; overflow: hidden;
    }
    .progress-bar { height: 100%; border-radius: 4px; }
    
    /* 5. 状态胶囊 */
    .status-pill {
        display: inline-flex; align-items: center; gap: 6px;
        padding: 6px 14px; border-radius: 20px;
        font-size: 12px; font-weight: 600;
        margin-right: 8px; margin-bottom: 8px;
        border: 1px solid;
    }
    .pill-danger { background: #fef2f2; color: #dc2626; border-color: #fecaca; }
    .pill-success { background: #ecfdf5; color: #059669; border-color: #a7f3d0; }

    /* AI 报告样式 */
    .ai-report-container {
        background-color: #f0fdf4; border: 1px solid #bbf7d0;
        border-radius: 12px; padding: 25px; margin-bottom: 30px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
    }
    .ai-report-title {
        color: #166534; font-size: 18px; font-weight: 800; margin-bottom: 15px; 
        display: flex; align-items: center; gap: 10px;
        border-bottom: 1px solid #dcfce7; padding-bottom: 10px;
    }
    .ai-content { font-family: 'Georgia', serif; font-size: 15px; line-height: 1.7; color: #14532d; }

    /* 模块卡片可点击样式 */
    a.module-link { text-decoration: none; color: inherit; display: block; width: 100%; }
    a.module-link * { cursor: pointer; }
    a.module-link:hover .term-card {
        transform: translateY(-3px);
        box-shadow: 0 12px 22px rgba(15,23,42,0.12);
        border-color: #cbd5e1;
    }
    a.module-link:hover { transform: translateY(-2px); }
    a.module-link .term-card { transition: transform 0.2s, box-shadow 0.2s; }
    
    /* 隐藏 Streamlit 默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* 保留顶部栏以显示侧边栏展开按钮 */
    header {visibility: visible;}
    
    code { background: transparent !important; color: inherit !important; padding: 0 !important; }
</style>
"""

# ==========================================
# Dashboard 逻辑
# ==========================================
def render_dashboard_standalone(df_all):
    # 注入 CSS
    st.markdown(PROFESSIONAL_LIGHT_CSS, unsafe_allow_html=True)

    # ----------------------------------------------------
    # 1. 核心计算逻辑 (完全保留原代码)
    # ----------------------------------------------------
    def prev_week_value(series, days=7):
        target = series.index[-1] - pd.Timedelta(days=days)
        idx = series.index.get_indexer([target], method='nearest')[0]
        return series.iloc[idx]
    df_raw_a = df_all[df_all.index >= '2020-01-01'].copy()
    
    df_a = pd.DataFrame()
    df_a['WALCL'] = df_raw_a['WALCL'].resample('W-WED').last() 
    df_a['WTREGEN'] = df_raw_a['WTREGEN'].resample('W-WED').last()
    df_a['RRPONTSYD'] = df_raw_a['RRPONTSYD'].resample('W-WED').last()
    df_a['WRESBAL'] = df_raw_a['WRESBAL'].resample('W-WED').last()
    df_a = df_a.fillna(method='ffill').dropna()

    def get_tga_penalty(tga_val):
        tga_b = tga_val / 1000 if tga_val > 10000 else tga_val
        if tga_b < 800: return 1.0  
        elif 800 <= tga_b < 850: return 0.8  
        elif 850 <= tga_b < 900: return 0.6
        else: return 0.5
    
    tga_b = df_a['WTREGEN'].where(df_a['WTREGEN'] <= 10000, df_a['WTREGEN'] / 1000)
    df_a['TGA_Penalty_Level'] = tga_b.apply(get_tga_penalty)

    def get_tga_trend_penalty(delta_b):
        if delta_b <= 0: return 1.0
        elif delta_b <= 50: return 0.95
        elif delta_b <= 100: return 0.9
        elif delta_b <= 150: return 0.8
        else: return 0.7

    df_a['TGA_Change_4W'] = tga_b.diff(4).fillna(0)
    df_a['TGA_Penalty_Trend'] = df_a['TGA_Change_4W'].apply(get_tga_trend_penalty)
    df_a['TGA_Penalty_Total'] = df_a['TGA_Penalty_Level'] * df_a['TGA_Penalty_Trend']
    if df_a['RRPONTSYD'].mean() < 10000:
        df_a['RRP_Clean'] = df_a['RRPONTSYD'] * 1000
    else:
        df_a['RRP_Clean'] = df_a['RRPONTSYD']
    df_a['Net_Liquidity'] = df_a['WALCL'] - df_a['WTREGEN'] - df_a['RRP_Clean']

    df_a['Liquidity_Sink'] = df_a['WTREGEN'] + df_a['RRP_Clean']
    df_a['Liquidity_Sink_Ratio'] = (df_a['Liquidity_Sink'] / df_a['WALCL']).clip(lower=0)
    def sink_penalty_ratio(r):
        if r < 0.10: return 1.0
        elif r < 0.15: return 0.9
        elif r < 0.20: return 0.8
        elif r < 0.25: return 0.7
        else: return 0.6
    df_a['Sink_Penalty'] = df_a['Liquidity_Sink_Ratio'].apply(sink_penalty_ratio)
    
    def rolling_percentile(series, window=156, min_periods=20):
        return series.rolling(window, min_periods=min_periods).apply(
            lambda s: s.rank(pct=True).iloc[-1],
            raw=False
        ) * 100

    def get_score_a(series):
        return rolling_percentile(series.diff(13))
    df_a['Score_NetLiq'] = get_score_a(df_a['Net_Liquidity'])
    df_a['Score_TGA'] = get_score_a(-df_a['WTREGEN'])
    df_a['Score_RRP'] = get_score_a(-df_a['RRP_Clean'])
    df_a['Score_Reserves'] = get_score_a(df_a['WRESBAL'])
    base_total_a = (df_a['Score_NetLiq']*0.45 + df_a['Score_TGA']*0.2 + df_a['Score_RRP']*0.25 + df_a['Score_Reserves']*0.1)
    df_a['Score_NetLiq_Adj'] = df_a['Score_NetLiq'] * df_a['Sink_Penalty']
    df_a['Total_Score'] = (
        df_a['Score_NetLiq_Adj'] * 0.45 +
        df_a['Score_TGA'] * 0.2 +
        df_a['Score_RRP'] * 0.25 +
        df_a['Score_Reserves'] * 0.1
    ) * df_a['TGA_Penalty_Total']

    # 模块 B
    df_b = df_all.copy().dropna() 
    df_b['SOFR_MA13'] = df_b['SOFR'].rolling(65, min_periods=1).mean()
    df_b['SOFR_Trend'] = df_b['SOFR_MA13'].diff(21)
    df_b['Score_Trend'] = df_b['SOFR_Trend'].rolling(1260, min_periods=1).rank(pct=True, ascending=False) * 100
    def get_regime_bonus(sofr):
        if sofr < 1.0: return 20
        elif sofr < 2.5: return 10
        elif sofr > 5.0: return -20
        elif sofr > 4.0: return -10
        else: return 0
    df_b['Regime_Bonus'] = df_b['SOFR'].apply(get_regime_bonus)
    df_b['Score_Policy'] = (df_b['Score_Trend'] + df_b['Regime_Bonus']).clip(0, 100)
    
    df_b['Corridor_Width'] = (df_b['IORB'] - df_b['RRPONTSYAWARD']).abs().clip(lower=0.05)

    df_b['F1_Spread'] = df_b['SOFR'] - df_b['IORB']
    df_b['F1_Ratio'] = df_b['F1_Spread'].clip(lower=0) / df_b['Corridor_Width']

    df_b['F2_Spread'] = df_b['SOFR'] - df_b['RRPONTSYAWARD']
    df_b['F2_Ratio'] = df_b['F2_Spread'].abs() / df_b['Corridor_Width']

    df_b['F3_Spread'] = df_b['TGCRRATE'] - df_b['SOFR']
    df_b['F3_Ratio'] = df_b['F3_Spread'].abs() / df_b['Corridor_Width']

    def ratio_to_score(series, max_ratio_series):
        denom = max_ratio_series.replace(0, np.nan).ffill().fillna(0.5)
        scaled = (series / denom).clip(lower=0, upper=1)
        return (1 - scaled**1.6) * 100

    df_b['F1_Max'] = df_b['F1_Ratio'].rolling(180, min_periods=60).quantile(0.85)
    df_b['F2_Max'] = df_b['F2_Ratio'].rolling(180, min_periods=60).quantile(0.85)
    df_b['F3_Max'] = df_b['F3_Ratio'].rolling(180, min_periods=60).quantile(0.85)

    df_b['Score_F1'] = ratio_to_score(df_b['F1_Ratio'], df_b['F1_Max'])
    df_b['Score_F2'] = ratio_to_score(df_b['F2_Ratio'], df_b['F2_Max'])
    df_b['Score_F3'] = ratio_to_score(df_b['F3_Ratio'], df_b['F3_Max'])

    df_b['SRF_Penalty_Base'] = 100 / (1 + np.exp(-0.6 * (df_b['RPONTSYD'] - 5)))
    df_b['SRF_Accel'] = df_b['RPONTSYD'].diff(3).clip(lower=0)
    df_b['SRF_Penalty'] = (df_b['SRF_Penalty_Base'] + (df_b['SRF_Accel'] / 20).clip(0, 1) * 35).clip(0, 100)
    df_b['Score_SRF'] = 100 - df_b['SRF_Penalty']

    df_b['SRF_Weight'] = 0.10 + 0.15 * (df_b['SRF_Penalty'] / 100)
    residual = 1 - df_b['SRF_Weight']
    df_b['Score_Friction'] = (
        df_b['Score_F1'] * residual * 0.4 +
        df_b['Score_F2'] * residual * 0.3 +
        df_b['Score_F3'] * residual * 0.3 +
        df_b['Score_SRF'] * df_b['SRF_Weight']
    )
    df_b['Total_Score'] = df_b['Score_Policy'] * 0.40 + df_b['Score_Friction'] * 0.60

    # 模块 C
    df_c = df_all.copy().dropna()
    def get_level_score(series): return series.rolling(1260, min_periods=1).rank(pct=True, ascending=False) * 100
    df_c['Score_10Y'] = get_level_score(df_c['DGS10'])
    df_c['Score_2Y'] = get_level_score(df_c['DGS2'])
    df_c['Score_30Y'] = get_level_score(df_c['DGS30'])
    def get_slope_score(series, target, tol):
        dev = (series - target).abs()
        return (100 - (dev / tol * 80)).clip(0, 100)
    df_c['Score_Curve_2s10s'] = get_slope_score(df_c['T10Y2Y'], 0.5, 1.5)
    df_c['Score_Curve_3m10s'] = get_slope_score(df_c['T10Y3M'], 0.75, 2.0)
    df_c['Total_Score1'] = (df_c['Score_Curve_2s10s']*0.3 + df_c['Score_Curve_3m10s']*0.3 + df_c['Score_10Y']*0.2 + df_c['Score_2Y']*0.1 + df_c['Score_30Y']*0.1)
    
    slope_10 = df_c['DGS10'].diff(60)
    slope_30 = df_c['DGS30'].diff(60)
    df_c['Max_Slope'] = pd.concat([slope_10, slope_30], axis=1).max(axis=1)
    def get_slope_penalty(s):
        if s > 0.50: return 0.2
        elif s > 0.30: return 0.6 
        elif s > 0.15: return 0.8
        else: return 1.0
    df_c['Penalty_Factor'] = df_c['Max_Slope'].apply(get_slope_penalty)
    df_c['Total_Score'] = df_c['Total_Score1'] * df_c['Penalty_Factor']

    # 模块 D
    df_d = df_all.copy().dropna()
    df_d['Score_Real_10Y'] = df_d['DFII10'].rolling(1260, min_periods=1).rank(pct=True, ascending=False) * 100
    df_d['Score_Real_5Y'] = df_d['DFII5'].rolling(1260, min_periods=1).rank(pct=True, ascending=False) * 100
    df_d['Score_Breakeven'] = get_slope_score(df_d['T10YIE'], 2.1, 0.6) 
    df_d['Total_Score'] = (df_d['Score_Real_10Y']*0.4 + df_d['Score_Real_5Y']*0.3 + df_d['Score_Breakeven']*0.3)

    # 模块 E
    df_e = df_all.copy()
    if 'IRSTCI01JPM156N' in df_e.columns: df_e['IRSTCI01JPM156N'] = df_e['IRSTCI01JPM156N'].fillna(method='ffill')
    df_e = df_e.fillna(method='ffill').dropna()
    df_e['Chg_USD'] = df_e['DTWEXBGS'].pct_change(63)
    df_e['Score_USD'] = (1 - df_e['Chg_USD'].rolling(1260, min_periods=1).rank(pct=True)) * 100
    df_e['Chg_DXY'] = df_e['DXY'].pct_change(63)
    df_e['Score_DXY'] = (1 - df_e['Chg_DXY'].rolling(1260, min_periods=1).rank(pct=True)) * 100
    df_e['Yen_Appreciation'] = -1 * df_e['DEXJPUS'].pct_change(63)
    df_e['Score_Yen_FX'] = (1 - df_e['Yen_Appreciation'].rolling(1260, min_periods=1).rank(pct=True)) * 100
    df_e['Score_BoJ_Rate'] = (1 - df_e['IRSTCI01JPM156N'].rolling(1260, min_periods=1).rank(pct=True)) * 100
    df_e['Score_Yen_Total'] = df_e['Score_Yen_FX'] * 0.7 + df_e['Score_BoJ_Rate'] * 0.3
    df_e['Chg_Oil'] = df_e['DCOILWTICO'].pct_change(63)
    df_e['Score_Oil'] = (1 - df_e['Chg_Oil'].rolling(1260, min_periods=1).rank(pct=True)) * 100
    df_e['Chg_Gas'] = df_e['DHHNGSP'].pct_change(63)
    df_e['Score_Gas'] = (1 - df_e['Chg_Gas'].rolling(1260, min_periods=1).rank(pct=True)) * 100
    df_e['Score_Energy'] = df_e['Score_Oil'] * 0.5 + df_e['Score_Gas'] * 0.5
    df_e['Total_Score'] = (df_e['Score_USD'] * 0.20 + df_e['Score_DXY'] * 0.20 + df_e['Score_Yen_Total'] * 0.3 + df_e['Score_Energy'] * 0.3)

    # --------------------------------------------------------
    # 2. 准备渲染数据 (获取最新值)
    # --------------------------------------------------------
    score_a = df_a['Total_Score'].iloc[-1]
    score_b = df_b['Total_Score'].iloc[-1]
    score_c = df_c['Total_Score'].iloc[-1]
    score_d = df_d['Total_Score'].iloc[-1]
    score_e = df_e['Total_Score'].iloc[-1]
    
    # 变动 (WoW/MoM 根据原逻辑)
    chg_a = score_a - df_a['Total_Score'].iloc[-2] # A为周频，直接取上周
    chg_b = score_b - prev_week_value(df_b['Total_Score'])
    chg_c = score_c - prev_week_value(df_c['Total_Score'])
    chg_d = score_d - prev_week_value(df_d['Total_Score'])
    chg_e = score_e - prev_week_value(df_e['Total_Score'])
    
    total_score = score_a*0.25 + score_b*0.25 + score_c*0.15 + score_d*0.15+score_e*0.20
    prev_total = (
        df_a['Total_Score'].iloc[-2]*0.25 +
        prev_week_value(df_b['Total_Score'])*0.25 +
        prev_week_value(df_c['Total_Score'])*0.15 +
        prev_week_value(df_d['Total_Score'])*0.15 +
        prev_week_value(df_e['Total_Score'])*0.20
    )
    total_chg = total_score - prev_total

    # Dashboard 页面不显示 AI 报告

 
    col_left, col_spacer, col_right = st.columns([1, 0.06, 2])

    with col_left:
        # --- 1. 动态仪表盘颜色逻辑 ---
        if total_score < 20:
            gauge_color = "#dc2626" # 红色
        elif total_score < 40:
            gauge_color = "#f97316" # 橙色
        elif total_score < 60:
            gauge_color = "#eab308" # 黄色
        else:
            gauge_color = "#059669" # 绿色

        # --- 2. Plotly 仪表盘 ---
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge",
            value = total_score,
            gauge = {
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#333"},
                'bar': {'color': gauge_color},
                'bgcolor': "#f3f4f6",
                'borderwidth': 0,
                'steps': [{'range': [0, 100], 'color': "#f3f4f6"}],
            }
        ))
        fig_gauge.update_layout(
            height=250, margin=dict(l=20,r=20,t=20,b=20),
            paper_bgcolor='rgba(0,0,0,0)', font={'family': "Inter"},
            annotations=[
                dict(
                    x=0.5, y=0.12, xref="paper", yref="paper",
                    text=f"<b>{total_score:.1f}</b>",
                    showarrow=False,
                    font=dict(size=56, color="#1f2937", family="Inter, -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Helvetica Neue', sans-serif")
                )
            ]
        )
        
        st.markdown(f"""<div class="term-card" style="text-align:center;"><div style="font-weight:bold; font-size:20px; color:black; text-transform:uppercase; letter-spacing:1px; margin-bottom:10px;">宏观综合得分</div></div>""", unsafe_allow_html=True)
        st.plotly_chart(fig_gauge, use_container_width=True)
        
        chg_color = "text-green" if total_chg >= 0 else "text-red"
        chg_arrow = "▲" if total_chg >= 0 else "▼"
        st.markdown(f"""<div style="text-align:center; margin-top:-5px; margin-bottom:20px;"><span class="text-dim">vs 上周: </span><span class="{chg_color}" style="font-weight:bold; font-family:monospace;">{chg_arrow} {abs(total_chg):.1f}</span></div>""", unsafe_allow_html=True)

        # 状态 Pills
        pills_html = ""
        tga_latest = df_all['WTREGEN'].iloc[-1]
        tga_prev = df_all['WTREGEN'].iloc[-9]
        # 统一到“十亿美元”尺度判断（与模型惩罚逻辑一致）
        tga_latest_b = tga_latest / 1000 if tga_latest > 10000 else tga_latest
        tga_prev_b = tga_prev / 1000 if tga_prev > 10000 else tga_prev
        tga_diff_b = tga_latest_b - tga_prev_b
        tga_is_drain = True if tga_latest_b > 800 else (tga_diff_b > 0)
        pills_html += f'<span class="status-pill {"pill-danger" if tga_is_drain else "pill-success"}">💧 TGA {"抽水" if tga_is_drain else "放水"}</span>'
        pills_html += f'<span class="status-pill {"pill-danger" if df_all["T10Y2Y"].iloc[-1] < 0 else "pill-success"}">{"📉 倒挂" if df_all["T10Y2Y"].iloc[-1] < 0 else " 10Y-2Y利差正常"}</span>'
        pills_html += f'<span class="status-pill {"pill-danger" if df_all["RPONTSYD"].iloc[-1] > 1 else "pill-success"}">{"🏦 SRF 启用" if df_all["RPONTSYD"].iloc[-1] > 1 else " SRF 闲置"}</span>'
        
        st.markdown(f"""<div style="display:flex; flex-wrap:wrap; justify-content:center;">{pills_html}</div>""", unsafe_allow_html=True)

    with col_right:
        # 趋势图 (适配浅色：深灰线)
        st.markdown("""<div class="term-card" style="height: 100%;"><div style="display:flex; justify-content:space-between; margin-bottom:9px;"><div style="font-weight:bold; font-size:20px; color:#1f2937;">综合得分趋势 (Historical Trend)</div>""", unsafe_allow_html=True)

        lookback_years = st.slider("⏱️ 观察窗口 (年)", 1, 10, 5)
        idx = df_b.index
        s_a_hist = df_a['Total_Score'].reindex(idx, method='ffill')
        s_total_hist = (s_a_hist*0.25 + df_b['Total_Score']*0.25 + df_c['Total_Score']*0.15 + df_d['Total_Score']*0.15 + df_e['Total_Score']*0.20).dropna()
        trading_days = lookback_years * 252
        recent_trend = s_total_hist.tail(trading_days)

        fig_trend = go.Figure()
        # 主线：深蓝
        fig_trend.add_trace(go.Scatter(x=recent_trend.index, y=recent_trend.values, name='综合得分', mode='lines', line=dict(color='#2563eb', width=2), fill='tozeroy', fillcolor='rgba(37, 99, 235, 0.05)'))
        # 辅线：淡灰/淡彩
        fig_trend.add_trace(go.Scatter(x=recent_trend.index, y=s_a_hist.loc[recent_trend.index], name='A.流动性', line=dict(color='#06b6d4', width=1, dash='dot'), visible='legendonly'))
        fig_trend.add_trace(go.Scatter(x=recent_trend.index, y=df_b['Total_Score'].loc[recent_trend.index], name='B.资金面', line=dict(color='#8b5cf6', width=1, dash='dot'), visible='legendonly'))
        fig_trend.add_trace(go.Scatter(x=recent_trend.index, y=df_c['Total_Score'].loc[recent_trend.index], name='C.国债', line=dict(color='#f59e0b', width=1, dash='dot'), visible='legendonly'))
        fig_trend.add_trace(go.Scatter(x=recent_trend.index, y=df_d['Total_Score'].loc[recent_trend.index], name='D.利率', line=dict(color='#ec4899', width=1, dash='dot'), visible='legendonly'))
        fig_trend.add_trace(go.Scatter(x=recent_trend.index, y=df_e['Total_Score'].loc[recent_trend.index], name='E.外部', line=dict(color='#10b981', width=1, dash='dot'), visible='legendonly'))
        
        
        fig_trend.update_layout(
            height=300,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0,r=0,t=10,b=0),
            xaxis=dict(showgrid=False, tickfont=dict(color='#9ca3af')),
            yaxis=dict(showgrid=True, gridcolor='#f3f4f6', zeroline=False, tickfont=dict(color='#9ca3af')),
            hovermode="x unified",
            legend=dict(orientation="h", y=1.1, font=dict(color="#4b5563"))
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # 4. 模块卡片区域 (HTML 生成) - 修复缩进问题
    # --------------------------------------------------------
    def section_header(title):
        st.markdown(
            f"""<div style="display:flex; align-items:center; margin: 30px 0 20px 0;">
            <div style="width:8px; height:8px; background:#2563eb; border-radius:50%; margin-right:10px;"></div>
            <div style="font-size:16px; font-weight:700; color:#1f2937; letter-spacing:1px;">{title}</div>
            <div style="flex:1; height:1px; background:#e5e7eb; margin-left:15px;"></div></div>""",
            unsafe_allow_html=True
        )

    section_header("模块因子")

    def create_card_html(mod_id, title, sub, score, change, weight, desc, link=None):
        color_cls = "text-green" if score >= 60 else ("text-gold" if score >= 40 else "text-red")
        bar_color = "#059669" if score >= 60 else ("#eab308" if score >= 40 else "#dc2626")
        arrow = "▲" if change >= 0 else "▼"
        chg_cls = "text-green" if change >= 0 else "text-red"
        
        card_html = f"""<div class="term-card module-card"><div style="display:flex; justify-content:space-between; margin-bottom:10px;"><div><span style="background:#f3f4f6; color:#4b5563; font-size:10px; padding:2px 6px; border-radius:4px; font-weight:600;">MOD {mod_id}</span><span class="text-dim" style="text-transform:uppercase; margin-left:5px; font-size:10px;">{sub}</span><div style="font-size:16px; font-weight:bold; color:#111827; margin-top:5px;">{title}</div></div><div class="text-dim" style="font-family:monospace;">{weight}</div></div><div style="display:flex; align-items:baseline; gap:10px;"><span style="font-size:32px; font-weight:bold; color:#111827;">{score:.1f}</span><span class="{chg_cls}" style="font-size:12px; font-family:monospace;">{arrow} {abs(change):.1f}</span></div><div class="progress-bg"><div class="progress-bar" style="width: {score}%; background: {bar_color};"></div></div><div class="module-footer" style="margin-top:15px; padding-top:10px; border-top:1px solid #f3f4f6; font-size:11px; color:#6b7280; display:flex; align-items:center;"><div style="width:6px; height:6px; background:{bar_color}; border-radius:50%; margin-right:6px;"></div><span class="module-desc">{desc}</span></div></div>"""
        if link:
            return f"""<a class="module-link" href="{link}" target="_self">{card_html}</a>"""
        return card_html

    # 动态文案
    tga_curr = df_all['WTREGEN'].iloc[-1]
    tga_penalty_now = df_a['TGA_Penalty_Total'].iloc[-1] if 'TGA_Penalty_Total' in df_a.columns else 1.0
    sink_penalty_now = df_a['Sink_Penalty'].iloc[-1] if 'Sink_Penalty' in df_a.columns else 1.0
    if tga_curr >= 800000:
        desc_a = f"TGA水位过高 ({tga_curr/1000:.0f}B) · 惩罚 {tga_penalty_now:.2f}x / 吸收惩罚 {sink_penalty_now:.2f}x"
    else:
        desc_a = f"吸收惩罚 {sink_penalty_now:.2f}x" if sink_penalty_now < 0.9 else ("净流动性回落" if score_a < 40 else "净流动性趋势平稳")
    desc_b = "SOFR 突破 IORB" if df_all['SOFR'].iloc[-1] > df_all['IORB'].iloc[-1] else "回购市场利率控制良好"
    desc_c = f"长端动量惩罚 ({df_c['Penalty_Factor'].iloc[-1]}x)" if df_c['Penalty_Factor'].iloc[-1] < 1.0 else ("深度倒挂 >50bps" if df_all['T10Y2Y'].iloc[-1] < -0.5 else "期限结构健康")
    desc_d = f"通胀预期 {df_all['T10YIE'].iloc[-1]:.2f}%"
    desc_e = "美元指数强势压制" if df_e['Chg_DXY'].iloc[-1] > 0.02 else "外部汇率环境相对宽松"

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.markdown(create_card_html("A", "系统流动性", "Liquidity", score_a, chg_a, "25%", desc_a, link="?nav=module_a"), unsafe_allow_html=True)
    with c2: st.markdown(create_card_html("B", "资金价格", "Funding", score_b, chg_b, "25%", desc_b, link="?nav=module_b"), unsafe_allow_html=True)
    with c3: st.markdown(create_card_html("C", "国债结构", "Yield Curve", score_c, chg_c, "15%", desc_c, link="?nav=module_c"), unsafe_allow_html=True)
    with c4: st.markdown(create_card_html("D", "实际利率", "Real Rates", score_d, chg_d, "15%", desc_d, link="?nav=module_d"), unsafe_allow_html=True)
    with c5: st.markdown(create_card_html("E", "外部冲击", "External", score_e, chg_e, "20%", desc_e, link="?nav=module_e"), unsafe_allow_html=True)
    # --------------------------------------------------------
    # 5. 参考图表 (TGA/SOFR联动 & 真理检验)
    # --------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("参考图表")
    col_chart_1, col_chart_2 = st.columns(2)
    
    with col_chart_1:
        # TGA / SOFR / SRF 资金联动监测
        latest_tga = df_all['WTREGEN'].iloc[-1]
        prev_tga_week = df_all['WTREGEN'].iloc[-8]
        latest_srf = df_all['RPONTSYD'].iloc[-1]
        latest_sofr = df_all['SOFR'].iloc[-1]
        prev_sofr_month = df_all['SOFR'].iloc[-30]
        
        # 积分计算逻辑 (原样保留)
        score = 0
        tga_diff = (latest_tga - prev_tga_week) / 1000
        if tga_diff < -10: score += 1
        elif tga_diff > 10: score -= 1
        
        if latest_tga >= 900: score -= 3
        elif latest_tga >= 850: score -= 2
        elif latest_tga >= 800: score -= 1
            
        if latest_srf < 5: score += 1
        elif latest_srf > 50: score -= 2
        
        sofr_diff = latest_sofr - prev_sofr_month
        if sofr_diff < -0.05: score += 1
        elif sofr_diff > 0.10: score -= 1
        
        if score >= 1:
            status_text = f"🟢 NET INFLOW [积分:{score}]"
            status_color = "#34c759"
        elif score <= -1:
            status_text = f"🔴 NET OUTFLOW [积分:{score}]"
            status_color = "#ff3b30"
        else:
            status_text = "⚪ NEUTRAL"
            status_color = "#d4af37"

        st.markdown(f"""<div class="term-card"><div style="font-weight:bold; color:#111827; margin-bottom:10px;">TGA / SOFR 联动监测 <span style="color:{status_color}; margin-left:10px;">{status_text}</span></div></div>""", unsafe_allow_html=True)
        
        dview = df_all[df_all.index >= '2023-01-01']
        fig_cross = go.Figure()
        fig_cross.add_trace(go.Scatter(x=dview.index, y=dview['WTREGEN']/1000, name='TGA ($B)', fill='tozeroy', line=dict(width=0), fillcolor='rgba(128,128,128,0.15)'))
        fig_cross.add_trace(go.Scatter(x=dview.index, y=dview['SOFR'], name='SOFR (%)', yaxis='y2', line=dict(color='#0068c9', width=2)))
        fig_cross.add_trace(go.Bar(x=dview.index, y=dview['RPONTSYD'], name='SRF ($B)', yaxis='y2', marker_color='rgba(255,43,43,0.6)'))
        
        fig_cross.update_layout(
            height=300, 
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            yaxis=dict(title="TGA ($B)", showgrid=False, title_font=dict(color='#374151'), tickfont=dict(color='#9ca3af')),
            yaxis2=dict(title="Rate / SRF", overlaying='y', side='right', showgrid=True, gridcolor='#f3f4f6', title_font=dict(color='#374151'), tickfont=dict(color='#9ca3af')),
            xaxis=dict(showgrid=False, tickfont=dict(color='#9ca3af')),
            legend=dict(orientation="h", y=-0.2, font=dict(color="#4b5563")), 
            margin=dict(t=10, b=10, l=10, r=10), hovermode="x unified"
        )
        st.plotly_chart(fig_cross, use_container_width=True)
        

    with col_chart_2:
        # 宏观分 vs 风险资产 (真理检验)
        st.markdown(f"""<div class="term-card"><div style="font-weight:bold; color:#111827; margin-bottom:10px;">真理检验: 宏观分 vs SPX/BTC</div></div>""", unsafe_allow_html=True)
        
        valid_view = df_all[df_all.index >= (datetime.now() - timedelta(days=1080))]
        valid_score = s_total_hist.reindex(valid_view.index, method='ffill')
        
        fig_spx = go.Figure()
        fig_spx.add_trace(go.Scatter(x=valid_view.index, y=valid_score, name='宏观得分', line=dict(color='#09ab3b', width=2), fill='tozeroy', fillcolor='rgba(9,171,59,0.1)'))
        
        if 'SP500' in df_all.columns:
            fig_spx.add_trace(go.Scatter(x=valid_view.index, y=valid_view['SP500'], name='S&P 500', line=dict(color='#d4af37', width=1.5, dash='dot'), yaxis='y2'))
        if 'CBBTCUSD' in df_all.columns:
            fig_spx.add_trace(go.Scatter(x=valid_view.index, y=valid_view['CBBTCUSD'], name='Bitcoin', line=dict(color='#f7931a', width=1.5, dash='dot'), yaxis='y3'))

        fig_spx.update_layout(
            height=300,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            yaxis=dict(title="Score", range=[0,100], showgrid=False, tickfont=dict(color='#9ca3af')),
            yaxis2=dict(title="SPX", overlaying='y', side='right', showgrid=True, gridcolor='#f3f4f6', tickfont=dict(color='#d97706')),
            yaxis3=dict(overlaying='y', side='right', position=0.95, showgrid=False, tickfont=dict(color='#ea580c'), showticklabels=False),
            xaxis=dict(showgrid=False, tickfont=dict(color='#9ca3af')),
            legend=dict(orientation="h", y=-0.2, font=dict(color="#4b5563")),
            margin=dict(t=10, b=10, l=10, r=10), hovermode="x unified"
        )
        st.plotly_chart(fig_spx, use_container_width=True)

    # --------------------------------------------------------
    # 6. 风险雷达 (Text Output)
    # --------------------------------------------------------
    section_header("风险雷达")
    risk_factors = []
    
    # 逻辑判断 (原样保留)
    tga_val_check = tga_curr / 1000 if tga_curr > 10000 else tga_curr
    if tga_val_check >= 800:
        p_val, p_level = ("0.5x", "🔴") if tga_val_check >= 900 else (("0.6x", "🟠") if tga_val_check >= 850 else ("0.8x", "🟡"))
        risk_factors.append(f"{p_level} **A模块 (TGA惩罚)**: TGA 余额高达 {tga_val_check:.1f}B，触发系数 **{p_val}**，流动性剧烈抽水。")
    
    if score_a < 40:
        risk_factors.append(f"🔴 **A模块 (流动性)**: 得分过低 ({score_a:.1f})，显示 Fed 净流动性枯竭。")
    
    if df_all['RPONTSYD'].iloc[-1] > 10:
        risk_factors.append(f"🔴 **B模块 (资金面)**: 触发 **SRF 动态惩罚**。急救室用量 > 100亿。")
    elif df_all['SOFR'].iloc[-1] > df_all['IORB'].iloc[-1]:
        risk_factors.append(f"🟠 **B模块 (资金面)**: SOFR 突破天花板 (IORB)，银行间资金紧张。")
    
    if df_c['Penalty_Factor'].iloc[-1] < 1.0:
        risk_factors.append(f"🔴 **C模块 (国债)**: 触发长端利率暴涨惩罚，系数 **{df_c['Penalty_Factor'].iloc[-1]:.1f}x**。")
    elif df_all['T10Y2Y'].iloc[-1] < -0.5:
         risk_factors.append(f"🟠 **C模块 (国债)**: 收益率曲线深度倒挂 (>50bps)。")

    if df_all['DFII10'].iloc[-1] > 2.0:
        risk_factors.append(f"🟠 **D模块 (实利)**: 10Y 实际利率 > 2.0%，极度限制性区域。")

    try:
        if df_all['DEXJPUS'].pct_change(5).iloc[-1] < -0.03: 
            risk_factors.append(f"🔴 **E模块 (汇率)**: 检测到 **日元套息平仓风险** (5日暴跌 >3%)。")
    except: pass

    try:
        if df_all['DCOILWTICO'].pct_change(20).iloc[-1] > 0.15: 
            risk_factors.append(f"🟠 **E模块 (能源)**: 油价短期飙升 (>15%)，通胀风险增加。")
    except: pass

    # 渲染雷达结果 (同样使用紧凑 HTML)
    if not risk_factors:
        st.markdown("""<div class="term-card" style="border-left: 4px solid #059669; background:#ecfdf5;"><div style="color:#065f46; font-weight:bold;">✅ SYSTEM NOMINAL</div><div style="color:#374151; font-size:13px; margin-top:5px;">宏观环境相对平稳。</div></div>""", unsafe_allow_html=True)
    else:
        risks_html = "".join([f"<div style='margin-top:8px; color:#1f2937; font-size:14px;'>{r}</div>" for r in risk_factors])
        st.markdown(f"""<div class="term-card" style="border-left: 4px solid #dc2626; background:#fef2f2;"><div style="color:#991b1b; font-weight:bold;">⚠️ WARNING: {len(risk_factors)} CRITICAL RISKS DETECTED</div>{risks_html}</div>""", unsafe_allow_html=True)

    # --------------------------------------------------------
    # 7. AI 宏观分析 (风险雷达下方)
    # --------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div id="ai-macro"></div>', unsafe_allow_html=True)
    section_header("AI 宏观分析")
    st.caption("基于当前宏观因子自动生成的研究报告")

    if 'ai_report' not in st.session_state:
        st.session_state.ai_report = None

    col_left, col_right = st.columns([0.3, 0.7])
    with col_left:
        if st.button("生成AI宏观分析", type="primary", use_container_width=True):
            st.session_state.ai_request = True

    if st.session_state.get("ai_request"):
        with st.spinner("🤖 正在生成宏观研究报告..."):
            tga_val = df_all['WTREGEN'].iloc[-1]
            context = f"""
            [系统时间]: {df_all.index[-1].strftime('%Y-%m-%d')}
            [宏观综合得分]: {total_score:.1f} / 100 (周变动: {total_chg:+.1f})
            [分模块详情]:
            1. 流动性 (Module A): 得分 {score_a:.1f} | TGA: {tga_val:.1f} | RRP: {df_all['RRPONTSYD'].iloc[-1]:.1f}
            2. 资金面 (Module B): 得分 {score_b:.1f} | SOFR: {df_all['SOFR'].iloc[-1]}%
            3. 国债 (Module C): 得分 {score_c:.1f} | 10Y-2Y: {df_all['T10Y2Y'].iloc[-1]} bps
            4. 实利 (Module D): 得分 {score_d:.1f} | 10Y实际利率: {df_all['DFII10'].iloc[-1]}%
            5. 外部 (Module E): 得分 {score_e:.1f} | DXY变动: {df_e['Chg_DXY'].iloc[-1]:.2%}
            """
            
            prompt = f"""
            你是一位顶级宏观对冲基金策略师。请基于以下数据写一份【Deep Research 市场分析报告】。
            {context}
            要求：
            1. 核心观点 (The One Thing)：一句话定义当前宏观环境。
            2. 风险雷达：指出最危险的1-2个因子。
            3. 资产配置建议：对美债、美股、黄金、BTC给出建议。
            4. 风格：专业、犀利、数据驱动。
            """
            
            st.session_state.ai_report = call_gemini_new_sdk(prompt, GEMINI_API_KEY)
        st.session_state.ai_request = False

    if st.session_state.ai_report:
        st.markdown(
            f"""
            <div class="ai-report-container">
                <div class="ai-report-title">
                    <span style="font-size:24px;">🧠</span> AI 宏观研究报告
                </div>
                <div class="ai-content">
                    {st.session_state.ai_report}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("点击上方按钮生成最新 AI 宏观研究报告。")

    # 8. 说明书
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📖 Dashboard 使用说明书"):
        st.markdown("""
        <div class="glossary-box" style="border-left: 4px solid #333;">
            <div class="glossary-title">宏观量化逻辑：模块风险判断 & 动态惩罚</div>
            <div class="glossary-content">
                本模型并非简单的加权平均，而是旨在模拟宏观环境的脆弱性。核心逻辑在于识别各个模块因子风险。<br><br>
                <b>1. 常态环境 (Normal Regime)：</b><br>
                当市场平稳时，A/B/C/D/E 按照 25/25/15/15/20 的权重线性叠加，反映整体水位。<br><br>
                <b>2. 动态惩罚 - 坏的时候权重增大：</b><br>
                宏观环境危机往往由单一因子做为导火索从而引发更大规模的危机。为了捕捉这种非线性风险，模型内置了动态调控惩罚机制：
                <br>
                &nbsp;&nbsp;🛑 <b>A模块 (TGA 抽水)</b>：监测财政部账户存量。当 TGA > 800B 时触发阶梯惩罚系数 (0.8x / 0.6x / 0.5x)，即使趋势向好，高绝对水位也会强行压制得分。
                <br>
                &nbsp;&nbsp;🛑 <b>B模块 (SRF)</b>：一旦监测到银行开始使用 SRF (急救贷款)，说明流动性传导失效。此时 B 模块内部权重重组，SRF 权重瞬间拉满，直接拉低B模块总分。
                <br>
                &nbsp;&nbsp;🛑 <b>C模块 (利率急涨)</b>：市场不怕高利率，怕急涨。若 10Y/30Y 利率在 60天内快速上涨，C 模块总分会直接乘以惩罚系数 (例如 0.2-0.8x)，模拟“杀估值”效应。
                <br><br>
                <b>3. 如何解读“流入/流出”动态标题？</b><br>
                标题基于<b>积分权重制</b>判定。当 TGA 周度放水、SRF 闲置及资金成本稳定等因子贡献积分 ≥ 1 时，判定为 🟢 NET INFLOW。反之，若积分 ≤ -1 (如 TGA 高位且抽水)，则判定为 🔴 NET OUTFLOW。
                <br><br>
                <b>4. 如何使用本看板？</b><br>
                不要只看总分。请重点关注上方的风险雷达。如果出现红色警报，说明宏观环境的某一根支柱出现了裂痕，此时即便其他模块得分很高，整体环境也是极其脆弱的。
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 底部版权
    st.markdown(
        """<div style="text-align:center; color:#475569; font-size:10px; font-family:monospace; margin-top:40px; border-top:1px solid rgba(255,255,255,0.05); padding-top:20px;">QUANT_MODEL_V2.5 // INTERNAL USE ONLY // POWERED BY STREAMLIT & PLOTLY</div>""",
        unsafe_allow_html=True,
    )
