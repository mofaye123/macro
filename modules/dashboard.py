import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==========================================
# Dashboard 
# ==========================================
def render_dashboard_standalone(df_all):
    
    df_raw_a = df_all[df_all.index >= '2020-01-01'].copy()
    
    df_a = pd.DataFrame()
    df_a['WALCL'] = df_raw_a['WALCL'].resample('W-WED').last() 
    df_a['WTREGEN'] = df_raw_a['WTREGEN'].resample('W-WED').last()
    df_a['RRPONTSYD'] = df_raw_a['RRPONTSYD'].resample('W-WED').last()
    df_a['WRESBAL'] = df_raw_a['WRESBAL'].resample('W-WED').last()
    df_a = df_a.fillna(method='ffill').dropna()

    def get_tga_penalty(tga_val):
        tga_b = tga_val / 1000 if tga_val > 10000 else tga_val
        
        if tga_b < 800:
            return 1.0  
        elif 800 <= tga_b < 850:
            return 0.8  
        elif 850 <= tga_b < 900:
            return 0.6
        else:
            return 0.5
    
    df_a['TGA_Penalty'] = df_a['WTREGEN'].apply(get_tga_penalty)

    if df_a['RRPONTSYD'].mean() < 10000:
        df_a['RRP_Clean'] = df_a['RRPONTSYD'] * 1000
    else:
        df_a['RRP_Clean'] = df_a['RRPONTSYD']

    df_a['Net_Liquidity'] = df_a['WALCL'] - df_a['WTREGEN'] - df_a['RRP_Clean']
    
    def get_score_a(series):
        return series.diff(13).rank(pct=True) * 100
    
    df_a['Score_NetLiq'] = get_score_a(df_a['Net_Liquidity'])
    df_a['Score_TGA'] = get_score_a(-df_a['WTREGEN']) * df_a['TGA_Penalty']
    df_a['Score_RRP'] = get_score_a(-df_a['RRP_Clean'])
    df_a['Score_Reserves'] = get_score_a(df_a['WRESBAL'])
    
    df_a['Total_Score'] = (
        df_a['Score_NetLiq'] * 0.5 + df_a['Score_TGA'] * 0.2 + 
        df_a['Score_RRP'] * 0.2 + df_a['Score_Reserves'] * 0.1
    )
    

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
    
    df_b['F1_Spread'] = df_b['SOFR'] - df_b['IORB']
    df_b['F1_Penalty'] = (df_b['F1_Spread'] - df_b['F1_Spread'].rolling(60, min_periods=1).median()).clip(lower=0)
    df_b['Score_F1'] = df_b['F1_Penalty'].rolling(1260, min_periods=1).rank(pct=True, ascending=False) * 100
    
    df_b['F2_Spread'] = df_b['SOFR'] - df_b['RRPONTSYAWARD']
    df_b['F2_Dev'] = (df_b['F2_Spread'] - df_b['F2_Spread'].rolling(60, min_periods=1).median()).abs()
    df_b['Score_F2'] = df_b['F2_Dev'].rolling(1260, min_periods=1).rank(pct=True, ascending=False) * 100
    
    df_b['F3_Spread'] = df_b['TGCRRATE'] - df_b['SOFR']
    df_b['F3_Dev'] = (df_b['F3_Spread'] - df_b['F3_Spread'].rolling(60, min_periods=1).median()).abs()
    df_b['Score_F3'] = df_b['F3_Dev'].rolling(1260, min_periods=1).rank(pct=True, ascending=False) * 100
    
    def get_srf_score(val):
        if val == 0: return 100
        elif val < 10: return 80
        elif val < 25: return 50
        elif val < 50: return 20
        else: return 0
    df_b['Score_SRF'] = df_b['RPONTSYD'].apply(get_srf_score)
    
    def get_friction_w(row):
        if row['RPONTSYD'] > 10: return {'F1':0.15, 'F2':0.15, 'F3':0.10, 'SRF':0.60}
        else: return {'F1':0.33, 'F2':0.33, 'F3':0.33, 'SRF':0}
        
    df_b['Score_Friction'] = df_b.apply(
        lambda row: (
            row['Score_F1'] * get_friction_w(row)['F1'] +
            row['Score_F2'] * get_friction_w(row)['F2'] +
            row['Score_F3'] * get_friction_w(row)['F3'] +
            row['Score_SRF'] * get_friction_w(row)['SRF']
        ), axis=1
    )
    df_b['Total_Score'] = df_b['Score_Policy'] * 0.40 + df_b['Score_Friction'] * 0.60


    df_c = df_all.copy().dropna()
    def get_level_score(series):
        return series.rolling(1260, min_periods=1).rank(pct=True, ascending=False) * 100
    df_c['Score_10Y'] = get_level_score(df_c['DGS10'])
    df_c['Score_2Y'] = get_level_score(df_c['DGS2'])
    df_c['Score_30Y'] = get_level_score(df_c['DGS30'])
    
    def get_slope_score(series, target, tol):
        dev = (series - target).abs()
        score = 100 - (dev / tol * 80)
        return score.clip(0, 100)
    df_c['Score_Curve_2s10s'] = get_slope_score(df_c['T10Y2Y'], 0.5, 1.5)
    df_c['Score_Curve_3m10s'] = get_slope_score(df_c['T10Y3M'], 0.75, 2.0)
    
    df_c['Total_Score1'] = (
        df_c['Score_Curve_2s10s']*0.3 + df_c['Score_Curve_3m10s']*0.3 + 
        df_c['Score_10Y']*0.2 + df_c['Score_2Y']*0.1 + df_c['Score_30Y']*0.1
    )

    # 10Y/30Y 双重动量惩罚
    
    slope_10 = df_c['DGS10'].diff(60)
    slope_30 = df_c['DGS30'].diff(60)
    
    df_c['Max_Slope'] = pd.concat([slope_10, slope_30], axis=1).max(axis=1)
    
    def get_slope_penalty(s):
        # s = 20天内利率上涨了多少bp
        if s > 0.50: return 0.2
        elif s > 0.30: return 0.6 
        elif s > 0.15: return 0.8
        else: return 1.0

    df_c['Penalty_Factor'] = df_c['Max_Slope'].apply(get_slope_penalty)

    # 最终分 = 基础分(Part 1) * 斜率惩罚系数
    df_c['Total_Score'] = df_c['Total_Score1'] * df_c['Penalty_Factor']


    df_d = df_all.copy().dropna()
    df_d['Score_Real_10Y'] = df_d['DFII10'].rolling(1260, min_periods=1).rank(pct=True, ascending=False) * 100
    df_d['Score_Real_5Y'] = df_d['DFII5'].rolling(1260, min_periods=1).rank(pct=True, ascending=False) * 100
    
    df_d['Score_Breakeven'] = get_slope_score(df_d['T10YIE'], 2.1, 0.6) 
    
    df_d['Total_Score'] = (
        df_d['Score_Real_10Y']*0.4 + df_d['Score_Real_5Y']*0.3 + df_d['Score_Breakeven']*0.3
    )

    df_e = df_all.copy()
    if 'IRSTCI01JPM156N' in df_e.columns:
        df_e['IRSTCI01JPM156N'] = df_e['IRSTCI01JPM156N'].fillna(method='ffill')
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

    df_e['Total_Score'] = (
        df_e['Score_USD'] * 0.20 +
        df_e['Score_DXY'] * 0.20 +
        df_e['Score_Yen_Total'] * 0.3 +
        df_e['Score_Energy'] * 0.3
    )

    # --------------------------------------------------------
    # 5. 渲染 Dashboard
    # --------------------------------------------------------

    score_a = df_a['Total_Score'].iloc[-1]
    score_b = df_b['Total_Score'].iloc[-1]
    score_c = df_c['Total_Score'].iloc[-1]
    score_d = df_d['Total_Score'].iloc[-1]
    score_e = df_e['Total_Score'].iloc[-1]
    
    prev_a = df_a['Total_Score'].iloc[-2]
    prev_b = df_b['Total_Score'].iloc[-8]
    prev_c = df_c['Total_Score'].iloc[-8]
    prev_d = df_d['Total_Score'].iloc[-8]
    prev_e = df_d['Total_Score'].iloc[-8]
    
    total_score = score_a*0.25 + score_b*0.25 + score_c*0.15 + score_d*0.15+score_e*0.20
    total_prev = prev_a*0.25 + prev_b*0.25 + prev_c*0.15 + prev_d*0.15+ prev_e*0.20
    
    # UI 部分
    st.markdown("###  宏观环境 (Macro Dashboard)")
    col_main, col_sub = st.columns([1, 2])
    
    with col_main:
        color = "#09ab3b" if total_score > 60 else ("#ff2b2b" if total_score < 40 else "#d97706")
        st.markdown(f"""
            <div class="metric-card" style="border-top: 6px solid {color}; padding: 30px;">
                <div class="metric-label" style="font-size: 18px;">宏观综合得分</div>
                <div class="metric-value" style="font-size: 48px; color: {color}">{total_score:.1f}</div>
                <div class="metric-label">vs上周: {total_score - total_prev:+.1f}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with col_sub:
        c1, c2, c3, c4, c5 = st.columns(5)
        def kpi(col, label, val, prev_v):
            c = "#09ab3b" if val > 50 else "#ff2b2b"
            col.metric(label, f"{val:.1f}", f"{val - prev_v:.1f}(vs上周)")
            
        kpi(c1, "A.流动性 (25%)", score_a, prev_a)
        kpi(c2, "B.资金面 (25%)", score_b, prev_b)
        kpi(c3, "C.国债结构 (15%)", score_c, prev_c)
        kpi(c4, "D.实际利率 (15%)", score_d, prev_d)
        kpi(c5, "E.外部冲击 (20%)", score_e, prev_e)
        
        st.markdown("<br>", unsafe_allow_html=True)
        k1, k2, k3, k4 = st.columns(4)
        if (df_all['WTREGEN'].iloc[-1] - df_all['WTREGEN'].iloc[-8]) > 0: k1.error("TGA抽水（周）") 
        else: k1.success("TGA放水（周）")
        if df_all['T10Y2Y'].iloc[-1] < 0: k2.error("10Y-2Y倒挂") 
        else: k2.success("10Y-2Y正常")
        if df_all['RPONTSYD'].iloc[-1] > 1: k3.error("SRF启用") 
        else: k3.success("SRF闲置")
        if df_all['DFII10'].iloc[-1] > 2.0: k4.error("利率高压(10Y 实际利率 >2)") 
        else: k4.success("利率适中(10Y 实际利率 <2)")

    st.divider()
    c_left, c_right = st.columns(2)
    
    with c_left:
        st.markdown("##### 综合得分趋势 ")
        fig_trend = go.Figure()
        
        idx = df_b.index
        # 将A(周频)填充到日频
        s_a = df_a['Total_Score'].reindex(idx, method='ffill')
        s_b = df_b['Total_Score']
        s_c = df_c['Total_Score']
        s_d = df_d['Total_Score']
        s_e = df_e['Total_Score']
        
        # 计算日频的历史总分
        s_total = s_a*0.25 + s_b*0.25 + s_c*0.15 + s_d*0.15 + s_e*0.2
        recent = idx[idx >= (datetime.now() - timedelta(days=1825))]
        
        # --- 这里是更新后的5条线 ---
        # 1. 总分 (粗黑)
        fig_trend.add_trace(go.Scatter(x=recent, y=s_total.loc[recent], name='综合得分', 
                                       line=dict(color='#333', width=4), fill='tozeroy', fillcolor='rgba(200,200,200,0.1)'))
        
        # 2. A (青色虚线)
        fig_trend.add_trace(go.Scatter(x=recent, y=s_a.loc[recent], name='A.流动性', 
                                       line=dict(color='#33CFFF', width=1.5, dash='dot')))
        
        # 3. B (紫色虚线)
        fig_trend.add_trace(go.Scatter(x=recent, y=s_b.loc[recent], name='B.资金面', 
                                       line=dict(color='#a855f7', width=1.5, dash='dot')))
        
        # 4. C (橙色虚线) 
        fig_trend.add_trace(go.Scatter(x=recent, y=s_c.loc[recent], name='C.国债', 
                                       line=dict(color='#d97706', width=1.5, dash='dot')))
        
        # 5. D (红色虚线) 
        fig_trend.add_trace(go.Scatter(x=recent, y=s_d.loc[recent], name='D.实际利率', 
                                       line=dict(color='#ff2b2b', width=1.5, dash='dot')))
        
        # 6. E (蓝色虚线）
        fig_trend.add_trace(go.Scatter(x=recent, y=s_e.loc[recent], name='E.外部冲击', 
                                     line=dict(color='#0068c9', width=1.5, dash='dot')))

        fig_trend.update_layout(height=380, margin=dict(l=0,r=0,t=10,b=0), legend=dict(orientation="h", y=1.1), hovermode="x unified")
        st.plotly_chart(fig_trend, use_container_width=True)


    with c_right:
        # 1. 获取最新数据
        latest_tga = df_all['WTREGEN'].iloc[-1]
        prev_tga_week = df_all['WTREGEN'].iloc[-8]
        latest_srf = df_all['RPONTSYD'].iloc[-1]
        latest_sofr = df_all['SOFR'].iloc[-1]
        prev_sofr_month = df_all['SOFR'].iloc[-30]
        
        # 2. 积分计算逻辑
        score = 0
        
        # --- 因子 A: TGA (变动趋势 + 绝对水位双控) ---
        tga_diff = (latest_tga - prev_tga_week) / 1000
        
        # 首先计算趋势分
        if tga_diff < -10: score += 1   # 周度放水
        elif tga_diff > 10: score -= 1  # 周度抽水
        
        # 【关键修正】：绝对水位强行扣分（压制趋势）
        # 即使你在放水，但只要总量在高位，就要把上面的加分扣掉甚至倒扣
        if latest_tga >= 900:
            score -= 3  # 极端枯竭：直接封死红色区间
        elif latest_tga >= 850:
            score -= 2  # 二级高压
        elif latest_tga >= 800:
            score -= 1  # 一级警戒
            
        # --- 因子 B: SRF (绝对水平) ---
        if latest_srf < 5: score += 1
        elif latest_srf > 50: score -= 2
        
        # --- 因子 C: SOFR (月度趋势) ---
        sofr_diff = latest_sofr - prev_sofr_month
        if sofr_diff < -0.05: score += 1
        elif sofr_diff > 0.10: score -= 1
        
        # 3. 最终判定映射
        if score >= 1:
            status_text = f"🟢 流动性状态：NET INFLOW (净流入) [积分:{score}]"
            status_color = "#09ab3b"
        elif score <= -1:
            status_text = f"🔴 流动性状态：NET OUTFLOW (压力/流出) [积分:{score}]"
            status_color = "#ff2b2b"
        else:
            status_text = "⚪ 流动性状态：NEUTRAL (区间震荡)"
            status_color = "#d97706"

        # 4. 渲染标题和图表
        st.markdown(f"##### TGA / SOFR / SRF 资金联动监测 <span style='color:{status_color}; font-size:16px; margin-left:10px;'>{status_text}</span>", unsafe_allow_html=True)
        
        dview = df_all[df_all.index >= '2023-01-01']
        fig_cross = go.Figure()
        
        # TGA (水位)
        fig_cross.add_trace(go.Scatter(
            x=dview.index, y=dview['WTREGEN']/1000, 
            name='TGA ($B)', 
            fill='tozeroy', line=dict(width=0), 
            fillcolor='rgba(128,128,128,0.15)'
        ))
        
        # SOFR (价格)
        fig_cross.add_trace(go.Scatter(
            x=dview.index, y=dview['SOFR'], 
            name='SOFR (%)', 
            yaxis='y2', 
            line=dict(color='#0068c9', width=2)
        ))
        
        # SRF (压力)
        fig_cross.add_trace(go.Bar(
            x=dview.index, y=dview['RPONTSYD'], 
            name='SRF ($B)', 
            yaxis='y2', 
            marker_color='rgba(255,43,43,0.6)'
        ))
        
        fig_cross.update_layout(
            title="(流入：TGA下降，SRF低位，SOFR稳定/ 流出：TGA上升，SRF高企，SOFR攀升)", height=400, 
            yaxis=dict(title="TGA ($B)", showgrid=False),
            yaxis2=dict(title="Rate / SRF", overlaying='y', side='right', showgrid=True),
            legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"), 
            margin=dict(t=50, b=50, l=10, r=10),
            hovermode="x unified"
        )
        
        # 在图表里加一个注释框，再次强调结论
        fig_cross.add_annotation(
            xref="paper", yref="paper",
            x=0.02, y=0.95,
            text=f"<b>{status_text.split('：')[1]}</b>",
            showarrow=False,
            font=dict(size=14, color=status_color),
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor=status_color,
            borderwidth=1
        )
        
        st.plotly_chart(fig_cross, use_container_width=True)
        
    # --- ：真理检验区 (Score vs SP500 vs BTC) ---
    st.divider()
    st.markdown("##### 宏观分 vs 风险资产")
    
    # 准备验证数据 (最近 1.5 年)
    valid_view = df_all[df_all.index >= (datetime.now() - timedelta(days=1080))]
    valid_score = s_total.reindex(valid_view.index, method='ffill')
    
    v_col1, v_col2 = st.columns(2)
    
    # 1. 宏观分 vs SP500
    with v_col1:
        if 'SP500' in df_all.columns:
            fig_spx = go.Figure()
            # 左轴: 分数
            fig_spx.add_trace(go.Scatter(x=valid_view.index, y=valid_score, name='宏观得分', 
                                       line=dict(color='#09ab3b', width=3), fill='tozeroy', fillcolor='rgba(9,171,59,0.1)'))
            # 右轴: SP500
            fig_spx.add_trace(go.Scatter(x=valid_view.index, y=valid_view['SP500'], name='S&P 500', 
                                       line=dict(color='#333', width=2, dash='dot'), yaxis='y2'))
            
            fig_spx.update_layout(
                title="验证 A: 宏观分 vs 美股 (SPX)", height=400,
                yaxis=dict(title="Score", range=[0,100], showgrid=False),
                yaxis2=dict(title="Price", overlaying='y', side='right', showgrid=True),
                legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"), 
                margin=dict(t=50, b=50, l=10, r=10),
                hovermode="x unified"
            )
            st.plotly_chart(fig_spx, use_container_width=True)
        else:
            st.info("数据加载中: 等待 SP500 数据...")

    # 2. 宏观分 vs BTC
    with v_col2:
        if 'CBBTCUSD' in df_all.columns:
            fig_btc = go.Figure()
            # 左轴: 分数
            fig_btc.add_trace(go.Scatter(x=valid_view.index, y=valid_score, name='宏观得分', 
                                       line=dict(color='#09ab3b', width=3), fill='tozeroy', fillcolor='rgba(9,171,59,0.1)'))
            # 右轴: BTC
            fig_btc.add_trace(go.Scatter(x=valid_view.index, y=valid_view['CBBTCUSD'], name='Bitcoin', 
                                       line=dict(color='#f7931a', width=2, dash='dot'), yaxis='y2'))
            
            fig_btc.update_layout(
                title="验证 B: 宏观分 vs 比特币 (BTC)", height=400,
                yaxis=dict(title="Score", range=[0,100], showgrid=False),
                yaxis2=dict(title="Price ($)", overlaying='y', side='right', showgrid=True),
                legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"), 
                margin=dict(t=50, b=50, l=10, r=10),
                hovermode="x unified"
            )
            st.plotly_chart(fig_btc, use_container_width=True)
        else:
            st.info("数据加载中: 等待 BTC 数据...")
    
    st.divider()
    
    
    st.markdown("##### 风险雷达")
    
    risk_factors = []

    tga_latest = df_all['WTREGEN'].iloc[-1]
    tga_b = tga_latest / 1000 if tga_latest > 10000 else tga_latest
    
    if tga_b >= 800:
        if tga_b >= 900:
            p_val, p_level = "0.5x", "🔴 "
        elif tga_b >= 850:
            p_val, p_level = "0.6x", "🟠 "
        else:
            p_val, p_level = "0.8x", "🟡 "
        
        risk_factors.append(f"{p_level} **A模块 (TGA惩罚)**: TGA 余额高达 {tga_b:.1f}B，已触发阶梯惩罚系数 **{p_val}**，流动性正在被财政部剧烈抽水。")
    
    if score_a < 40:
        risk_factors.append(f"🔴 **A模块 (流动性)**: 得分过低 ({score_a:.1f})，显示 Fed 净流动性或 TGA 正在剧烈抽水。")
    
    if df_all['RPONTSYD'].iloc[-1] > 10:
        risk_factors.append(f"🔴 **B模块 (资金面)**: 触发 **SRF 动态惩罚**。急救室用量 > 100亿，模型权重已强制倾斜至摩擦压力。")
    elif df_all['SOFR'].iloc[-1] > df_all['IORB'].iloc[-1]:
        risk_factors.append(f"🟠 **B模块 (资金面)**: SOFR 突破天花板 (IORB)，显示银行间资金紧张。")
    
    penalty_c = df_c['Penalty_Factor'].iloc[-1]
    if penalty_c < 1.0:
        discount = (1 - penalty_c) * 100
        risk_factors.append(f"🔴 **C模块 (国债)**: 触发长端利率短期暴涨惩罚机制，基础得分已乘以惩罚系数 **{penalty_c:.1f}x**。")
    elif df_all['T10Y2Y'].iloc[-1] < -0.5:
         risk_factors.append(f"🟠 **C模块 (国债)**: 收益率曲线深度倒挂 (>50bps)，强烈的衰退预警。")

    if df_all['DFII10'].iloc[-1] > 2.0:
        risk_factors.append(f"🟠 **D模块 (实利)**: 10Y 实际利率 > 2.0%，处于极度限制性区域，对风险资产估值构成重压。")

    try:
        jpy_chg_5d = df_all['DEXJPUS'].pct_change(5).iloc[-1]
        if jpy_chg_5d < -0.03: 
            risk_factors.append(f"🔴 **E模块 (汇率)**: 检测到 **日元套息平仓风险**。USD/JPY 5日内暴跌 (>3%)，警惕全球流动性冲击。")
    except:
        pass

    try:
        oil_chg_20d = df_all['DCOILWTICO'].pct_change(20).iloc[-1]
        if oil_chg_20d > 0.15: 
            risk_factors.append(f"🟠 **E模块 (能源)**: 油价短期飙升 (>15%)，通胀卷土重来风险增加。")
    except:
        pass
    # --- 渲染诊断结果 ---
    if not risk_factors:
        st.success("✅ **当前系统运行平稳**：五大模块未触发特殊惩罚机制，无明显的单一致命短板。")
    else:
        st.error(f"⚠️ **警报：模型识别到 {len(risk_factors)} 个关键风险源**")
        for risk in risk_factors:
            st.markdown(risk)

    # 2. 模型使用说明书 (动态权重的逻辑)
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
