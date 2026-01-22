import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def render_module_e(df_all):
   
    # 1. 数据准备
    df = df_all.copy()
    
    df['IRSTCI01JPM156N'] = df['IRSTCI01JPM156N'].fillna(method='ffill')
        
    df = df.fillna(method='ffill').dropna()

    # ==========================================
    # 2. 因子计算 
    # ==========================================
    
    # 美元 (涨=坏)
    df['Chg_USD'] = df['DTWEXBGS'].pct_change(63) 
    df['Score_USD'] = (1 - df['Chg_USD'].rolling(1260, min_periods=1).rank(pct=True)) * 100

    df['Chg_DXY'] = df['DTWEXAFEGS'].pct_change(63)
    df['Score_DXY'] = (1 - df['Chg_DXY'].rolling(1260, min_periods=1).rank(pct=True)) * 100
    
    # 日元 (USD/JPY 跌 = 坏)
    df['Yen_Appreciation'] = -1 * df['DEXJPUS'].pct_change(63)
    df['Score_Yen_FX'] = (1 - df['Yen_Appreciation'].rolling(1260, min_periods=1).rank(pct=True)) * 100
    
    # BoJ 利率 (高=坏)
    df['Score_BoJ_Rate'] = (1 - df['IRSTCI01JPM156N'].rolling(1260, min_periods=1).rank(pct=True)) * 100
    df['Score_Yen_Total'] = df['Score_Yen_FX'] * 0.7 + df['Score_BoJ_Rate'] * 0.3

    df['Chg_Oil'] = df['DCOILWTICO'].pct_change(63)
    df['Score_Oil'] = (1 - df['Chg_Oil'].rolling(1260, min_periods=1).rank(pct=True)) * 100
    
    df['Chg_Gas'] = df['DHHNGSP'].pct_change(63)
    df['Score_Gas'] = (1 - df['Chg_Gas'].rolling(1260, min_periods=1).rank(pct=True)) * 100
    
    df['Score_Energy'] = df['Score_Oil'] * 0.5 + df['Score_Gas'] * 0.5

    # 3. 综合得分
    df['Total_Score'] = (
        df['Score_USD'] * 0.2 +
        df['Score_DXY'] * 0.2 +
        df['Score_Yen_Total'] * 0.3 +
        df['Score_Energy'] * 0.3
    )

    # 4. 展示
    df_view = df[df.index >= '2020-01-01'].copy()
    
    latest = df.iloc[-1]
    prev_week = df.iloc[-8]

    c1, c2, c3, c4 = st.columns(4)
    
    score_color = "#09ab3b" if latest['Total_Score'] > 50 else "#ff2b2b"
    c1.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">E模块综合得分 (日频)</div>
            <div class="metric-value" style="color: {score_color}">{latest['Total_Score']:.1f}</div>
            <div class="metric-label">vs上周: {latest['Total_Score'] - prev_week['Total_Score']:.1f}</div>
        </div>
    """, unsafe_allow_html=True)

    c2.metric("DXY Index (Major)", f"{latest['DTWEXAFEGS']:.2f}", 
                  f"{(latest['DTWEXAFEGS'] - prev_week['DTWEXAFEGS']):.2f}(vs上周)", delta_color="inverse")
    c3.metric("BoJ Rate", f"{latest['IRSTCI01JPM156N']:.3f}%", f"{(latest['IRSTCI01JPM156N'] - prev_week['IRSTCI01JPM156N']):.3f}% (vs上周)", delta_color="inverse")
    c4.metric("WTI 原油", f"${latest['DCOILWTICO']:.1f}", f"{(latest['DCOILWTICO'] - prev_week['DCOILWTICO']):.1f} (vs上周)", delta_color="inverse")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("##### 🧩 因子细分得分")
    s1, s2, s3, s4 = st.columns(4)
    def sub_card(label, val):
        col = "#09ab3b" if val > 50 else "#ff2b2b"
        return f"""<div class="sub-card"><div class="sub-label">{label}</div><div class="sub-value" style="color:{col}">{val:.1f}</div></div>"""
    s1.markdown(sub_card("美元流动性 (20%)", latest['Score_USD']), unsafe_allow_html=True)
    s2.markdown(sub_card("DXY Major (20%)", latest['Score_DXY']), unsafe_allow_html=True) 
    s3.markdown(sub_card("日元套息压力 (30%)", latest['Score_Yen_Total']), unsafe_allow_html=True)      
    s4.markdown(sub_card("能源成本压力 (30%)", latest['Score_Energy']), unsafe_allow_html=True)

    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        fig_jp = go.Figure()
        fig_jp.add_trace(go.Scatter(x=df_view.index, y=df_view['DEXJPUS'], name='USD/JPY', line=dict(color='#0068c9', width=2)))
        fig_jp.add_trace(go.Scatter(x=df_view.index, y=df_view['IRSTCI01JPM156N'], name='BoJ Rate', line=dict(color='#ff2b2b', width=2, dash='dot'), yaxis='y2'))
        fig_jp.update_layout(title="日元：汇率 vs 利率", height=350, yaxis2=dict(overlaying='y', side='right'), hovermode="x unified")
        st.plotly_chart(fig_jp, use_container_width=True)
    
    with col2:
        fig_usd = go.Figure()
        if 'DTWEXAFEGS' in df_view.columns:
            fig_usd.add_trace(go.Scatter(x=df_view.index, y=df_view['DTWEXAFEGS'], name='DXY (Major)', line=dict(color='#2ca02c', width=2)))
        fig_usd.add_trace(go.Scatter(x=df_view.index, y=df_view['DTWEXBGS'], name='Broad USD', line=dict(color='#888', width=2, dash='dot'), yaxis='y2'))
        
        fig_usd.update_layout(height=350, title="美元指数", 
                              yaxis=dict(title='DXY Index'), yaxis2=dict(title='Broad Index', overlaying='y', side='right', showgrid=False),
                              hovermode="x unified", legend=dict(orientation="h", y=1.1), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_usd, use_container_width=True)

    
    st.markdown("<br>", unsafe_allow_html=True) 
    st.markdown("######  E模块综合得分趋势")
    
    fig_sc = go.Figure()
    fig_sc.add_trace(go.Scatter(x=df_view.index, y=df_view['Total_Score'], name='E模块得分', line=dict(color='#d97706', width=2), fill='tozeroy', fillcolor='rgba(217, 119, 6, 0.1)'))
    fig_sc.add_hline(y=50, line_dash="dash", line_color="#888")
    
    fig_sc.update_layout(
        height=350, 
        yaxis=dict(range=[0,100]), 
        hovermode="x unified", 
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=30, b=0) 
    )
    
    st.plotly_chart(fig_sc, use_container_width=True)

    
    # --- 百科 ---
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📚 E模块：因子专业定义与市场逻辑 (点击展开)", expanded=False):
        st.markdown("""
        <div class="glossary-box" style="border-left: 4px solid #d97706; background-color: #fff8e1;">
            <div class="glossary-title" style="color: #d97706;">📊 核心量化模型逻辑 (Methodology)</div>
            <div class="glossary-content">
                本模块得分基于63天动量趋势 + 历史分位，满分 100 分（50分=中性）：<br>
                <b>1. 日元 (The Carry Trade Anchor)：</b> 监测全球融资成本是否上升（利率）以及是否发生平仓（汇率）。<br>
                <b>2. 美元 (Global Liquidity)：</b> 监测全球美元流动性的松紧。<br>
                <b>3. 能源 (Input Cost)：</b> 监测通胀输入的压力。
            </div>
        </div>
        
        <div class="glossary-box">
            <div class="glossary-title">1. 美元广义指数 (Broad Dollar Index) - 权重 20%</div>
            <div class="glossary-content">
                <span class="glossary-label">成分：</span> 包含人民币、墨西哥比索等主要贸易伙伴货币。<br>
                <span class="glossary-label">意义：</span> <b>实体属性。</b> 它反映了美国出口的竞争力和全球（尤其是新兴市场）的美元偿债压力。
            </div>
            <div class="logic-row">
                <span class="bullish">⬇️ 下行 = 🟢 利好 (流动性宽松)</span>
                <span class="bearish">⬆️ 上升 = 🔴 利空 (流动性紧缩)</span>
            </div>
        </div>

        <div class="glossary-box">
            <div class="glossary-title">1. DXY Major Index (核心美元) - 权重 20%</div>
            <div class="glossary-content">
                <span class="glossary-label">成分：</span> 欧元(57%)、日元(13%)、英镑(11%)等发达国家货币。<br>
                <span class="glossary-label">意义：</span> <b>金融属性。</b> 它是全球对冲基金、衍生品交易的锚。DXY 飙升通常代表金融市场的“去杠杆”和“美元荒”。
            </div>
            <div class="logic-row">
                <span class="bullish">⬇️ 下行 = 🟢 利好 (流动性宽松)</span>
                <span class="bearish">⬆️ 上升 = 🔴 利空 (流动性紧缩)</span>
            </div>
        </div>


        <div class="glossary-box">
            <div class="glossary-title">2. 日元套息 (Yen Carry Trade) - 权重 30%</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> 包含 <b>USD/JPY 汇率</b> 和 <b>BoJ 利率</b>。<br>
                <span class="glossary-label">专业解读：</span> 日元是借钱成本最低的货币。如果日元暴涨或央行加息，会导致套息交易平仓，引发崩盘。
            </div>
            <div class="logic-row">
                <span class="bullish">USD/JPY ⬆️ 上升 (日元贬值) = 🟢 利好 (利好套息)</span>
                <span class="bearish">USD/JPY ⬇️ 下行 (日元升值) = 🔴 利空 (平仓风险)</span>
            </div>
        </div>

        <div class="glossary-box">
            <div class="glossary-title">3. 能源成本 (Energy Cost) - 权重 30%</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> 原油与天然气价格变化。<br>
                <span class="glossary-label">专业解读：</span> 能源价格急涨会推高通胀，迫使央行紧缩。
            </div>
            <div class="logic-row">
                <span class="bullish">⬇️ 下行/平稳 = 🟢 利好 (通胀温和)</span>
                <span class="bearish">⬆️ 飙升 = 🔴 利空 (滞胀风险)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📄 查看 原始数据明细"):
        st.dataframe(df_view.sort_index(ascending=False))
