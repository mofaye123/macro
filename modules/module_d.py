import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import timedelta

# ==========================================
# 7. 模块 D: 实际利率与通胀预期
# ==========================================
def render_module_d(df_raw):
    """
    D模块: 实际利率与通胀预期
    逻辑:
    1. 实际利率 (Real Rates): 名义 - 通胀预期。它是“真实”的资金成本。越低越好。
    2. 通胀预期 (Breakeven): MID_BEST 逻辑 (太高=通胀失控，太低=通缩衰退)
    """
    df = df_raw.copy()
    required_cols = ['DFII10', 'DFII5', 'T10YIE']
    if df.dropna(subset=required_cols).empty:
        st.warning("D模块数据不足（实际利率/通胀预期），请稍后刷新。")
        return
    df = df.dropna(subset=required_cols)

    def prev_week_row(frame, days=7):
        target = frame.index[-1] - pd.Timedelta(days=days)
        idx = frame.index.get_indexer([target], method='nearest')[0]
        return frame.iloc[idx]
    
    # --- 1. 因子计算 ---
    # 1.1 实际利率得分 (越低越好)
    # 逻辑: 实际利率飙升是风险资产最大的杀手 (参考2022年)
    def get_real_rate_score(series):
        # 同样使用反向排名：值越高，排名越低，分数越低
        return series.rolling(1260, min_periods=1).rank(pct=True, ascending=False) * 100
    
    df['Score_Real_10Y'] = get_real_rate_score(df['DFII10'])
    df['Score_Real_5Y'] = get_real_rate_score(df['DFII5'])

    # 1.2 通胀预期得分 (MID_BEST 逻辑)
    # 美联储目标是 2%，市场通常允许在 2.0% - 2.5% 之间
    # Target: 2.1%, 舒适区间: [1.5%, 2.7%]
    def get_inflation_score(series, target=2.1, tolerance=0.6):
        deviation = (series - target).abs()
        score = 100 - (deviation / tolerance * 80)
        return score.clip(0, 100)
    
    df['Score_Breakeven'] = get_inflation_score(df['T10YIE'], target=2.1, tolerance=0.6)

    # --- 2. 综合得分 ---
    df['Total_Score'] = (
        df['Score_Real_10Y'] * 0.40 + 
        df['Score_Real_5Y'] * 0.30 +
        df['Score_Breakeven'] * 0.30
    )

    # --- 3. 页面展示 ---
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    prev_week = prev_week_row(df)

    # KPI
    c1, c2, c3, c4 = st.columns(4)
    score_color = "#09ab3b" if latest['Total_Score'] > 50 else "#ff2b2b"
    
    c1.markdown(f"""
        <div class="metric-card">
        <div class="metric-label">D模块综合得分 (日频)</div>
        <div class="metric-value" style="color: {score_color}">{latest['Total_Score']:.1f}</div>
        <div class="metric-label">vs上周: {latest['Total_Score'] - prev_week['Total_Score']:.1f}</div>
        </div>
    """, unsafe_allow_html=True)

    # 实际利率
    c2.metric("10Y 实际利率 (TIPS)", f"{latest['DFII10']:.2f}%", f"{(latest['DFII10']-prev_week['DFII10'])*100:.0f} bps(vs上周)", delta_color="inverse")
    
    # 通胀预期 (Breakeven)
    be_val = latest['T10YIE']
    # 离2.1%越远越危险
    be_color = "normal" if 1.8 < be_val < 2.5 else "off"
    c3.metric("10Y 通胀预期 (Breakeven)", f"{be_val:.2f}%", f"{(be_val-prev_week['T10YIE'])*100:.0f} bps(vs上周)", delta_color=be_color)
    
    c4.metric("5Y 实际利率", f"{latest['DFII5']:.2f}%", f"{(latest['DFII5']-prev_week['DFII5'])*100:.0f} bps(vs上周)", delta_color="inverse")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("##### 🧩 因子细分得分")
    
    s1, s2, s3 = st.columns(3)
    s1.markdown(f"""<div class="sub-card"><div class="sub-label">10Y 真实资金成本 (40%)</div><div class="sub-value" style="color:{'#09ab3b' if latest['Score_Real_10Y']>50 else '#ff2b2b'}">{latest['Score_Real_10Y']:.1f}</div></div>""", unsafe_allow_html=True)
    s2.markdown(f"""<div class="sub-card"><div class="sub-label">5Y 真实资金成本 (30%)</div><div class="sub-value" style="color:{'#09ab3b' if latest['Score_Real_5Y']>50 else '#ff2b2b'}">{latest['Score_Real_5Y']:.1f}</div></div>""", unsafe_allow_html=True)
    s3.markdown(f"""<div class="sub-card"><div class="sub-label">通胀预期锚定度 (30%)</div><div class="sub-value" style="color:{'#09ab3b' if latest['Score_Breakeven']>50 else '#ff2b2b'}">{latest['Score_Breakeven']:.1f}</div></div>""", unsafe_allow_html=True)

    st.divider()

    # --- 图表 ---
    col1, col2 = st.columns(2)

    # 图1: 实际利率趋势
    with col1:
        fig_real = go.Figure()
        df_view = df[df.index >= '2020-01-01']
        fig_real.add_trace(go.Scatter(x=df_view.index, y=df_view['DFII10'], name='10Y Real Rate',
                                    line=dict(color='#d97706', width=2), fill='tozeroy', fillcolor='rgba(217, 119, 6, 0.1)'))
        fig_real.add_hline(y=2.0, line_dash="dash", line_color="red", annotation_text="高压线 (>2%)")
        fig_real.add_hline(y=0.0, line_dash="dash", line_color="green", annotation_text="宽松区 (<0%)")
        
        fig_real.update_layout(title="10Y 实际利率 (资金的真实价格)", height=350,
                             yaxis_title="Real Rate (%)", hovermode="x unified",
                               paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_real, use_container_width=True)

    # 图2: 通胀预期锚定区间 
    with col2:
        fig_be = go.Figure()
        fig_be.add_trace(go.Scatter(x=df_view.index, y=df_view['T10YIE'], name='通胀预期',
                                  line=dict(color='#8884d8', width=2)))
        
        # 舒适带 (1.8 - 2.5)
        fig_be.add_hrect(y0=1.8, y1=2.5, fillcolor="green", opacity=0.1, line_width=0, annotation_text="舒适区 (Goldilocks)")
        fig_be.add_hline(y=2.1, line_dash="dot", line_color="green")
        
        fig_be.update_layout(title="10Y 通胀预期 (Breakeven)", height=350,
                             yaxis_title="Inflation Exp (%)", hovermode="x unified",
                               paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_be, use_container_width=True)

    # 百科
        st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📚 D模块：因子专业定义与量化逻辑 (点击展开)", expanded=False):
        st.markdown("""
        <div class="glossary-box" style="border-left: 4px solid #6c5ce7; background-color: #f8f6ff;">
            <div class="glossary-title" style="color: #6c5ce7;">📊 核心量化模型逻辑 (Methodology)</div>
            <div class="glossary-content">
                D模块剥离了名义利率中的“水分”，直击资金最硬核的成本。<br>
                <b>1. 实际利率 (Real Rate)：</b> 公式为 <code>名义利率 - 通胀预期</code>。这是企业和个人经过通胀调整后的真实还款压力。该因子权重最高，且越低得分越高。<br>
                <b>2. 通胀预期 (Breakeven)：</b> 采用 <b>MID_BEST</b> 模型。
                <br>&nbsp;&nbsp; <b>目标 (Target)</b>：2.1% (美联储的长期目标)。
                <br>&nbsp;&nbsp; <b>失锚 (De-anchoring)</b>：如果预期跌破 1.5% (通缩/萧条) 或 突破 2.7% (通胀失控)，模型都会给予低分惩罚。
            </div>
        </div>

        <div class="glossary-box">
            <div class="glossary-title">1. 10Y 实际利率 (10Y Real Yield) - 权重 40%</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> TIPS (通胀保值债券) 的收益率。<br>
                <span class="glossary-label">专业解读：</span> 金融条件的标尺。因为名义利率高不可怕，如果通胀也高，实际还款压力其实不大。但如果“名义高、通胀低”（高实际利率），那就是对企业的最大绞杀。
            </div>
            <div class="logic-row">
                <span class="bullish">⬇️ 下行 (<0.5%) = 🟢 利好 (资金成本极低/刺激)</span>
                <span class="bearish">⬆️ 飙升 (>2.0%) = 🔴 利空 (强力紧缩/杀估值)</span>
            </div>
        </div>
        
        <div class="glossary-box">
            <div class="glossary-title">2. 5Y 实际利率 (5Y Real Yield) - 权重 30%</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> 中期真实融资成本。<br>
                <span class="glossary-label">专业解读：</span> 相比10Y，5Y实际利率对实体经济（如车贷、商业贷款）的敏感度更高。它是观察中期紧缩压力的窗口。
            </div>
            <div class="logic-row">
                <span class="bullish">⬇️ 下行 = 🟢 利好 (信贷需求恢复)</span>
                <span class="bearish">⬆️ 上行 = 🔴 利空 (实体经济承压)</span>
            </div>
        </div>

        <div class="glossary-box">
            <div class="glossary-title">3. 10Y Breakeven (盈亏平衡通胀率) - 权重 30%</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> 市场交易出来的未来10年平均通胀预期。<br>
                <span class="glossary-label">专业解读：</span> 美联储信誉的温度计。它不在于越低越好，而在于锚定。只要它稳定在 2.0%-2.5% 之间，美联储就敢降息（利好）；如果它失控飙升，美联储就必须加息杀通胀（利空）。
            </div>
            <div class="logic-row">
                <span class="bullish">锚定区间 (2.0-2.5%) = 🟢 中性利好 (央行掌控局面)</span>
                <span class="bearish">向上/向下失锚 = 🔴 双向利空 (通胀失控 or 通缩衰退)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        

        st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📄 查看 原始数据明细"):
        st.dataframe(df.sort_index(ascending=False))
        
