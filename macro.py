import ssl
# 1. 强制忽略 SSL 证书验证
ssl._create_default_https_context = ssl._create_unverified_context

import streamlit as st
import pandas as pd
from fredapi import Fred
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==========================================
# 0. 核心配置API
# ==========================================
API_KEY = st.secrets["FRED_API_KEY"]

# ==========================================
# 1. 页面配置 & UI
# ==========================================
st.set_page_config(page_title="宏观金融环境量化", layout="wide", page_icon="📈")
st.markdown("""
<style>
    /* 1. 核心大卡片 (白底 + 阴影) */
    .metric-card {
        background-color: #ffffff; 
        border: 1px solid #e0e0e0; 
        padding: 20px; 
        border-radius: 10px; 
        text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .metric-value {font-size: 26px; font-weight: bold; color: #333333;}
    .metric-label {font-size: 14px; color: #666666;}
    
    /* 2. 细分小卡片 (浅灰底) */
    .sub-card {
        background-color: #f8f9fa; 
        border: 1px solid #e0e0e0; 
        padding: 15px; 
        border-radius: 8px; 
        text-align: center;
    }
    .sub-value {font-size: 20px; font-weight: bold; color: #333333;}
    .sub-label {font-size: 12px; color: #666666;}
    
    /* 3. 因子百科样式 */
    .glossary-box {
        background-color: #f0f2f6;
        padding: 18px;
        border-radius: 6px;
        margin-bottom: 15px;
        border-left: 4px solid #33CFFF;
        border: 1px solid #e0e0e0;
    }
    .glossary-title { 
        font-weight: bold; color: #31333F; font-size: 16px; margin-bottom: 8px; 
        border-bottom: 1px solid #d0d0d0; padding-bottom: 5px;
        letter-spacing: 0.5px;
    }
    .glossary-content { 
        color: #424242; font-size: 14px; line-height: 1.6; margin-bottom: 8px;
    }
    .glossary-label { color: #0068c9; font-weight: bold; font-size: 14px; }
    
    .logic-row {
        display: flex; justify-content: space-between; 
        background-color: #ffffff;
        padding: 8px 15px; border-radius: 4px; margin-top: 8px;
        font-size: 13px; font-weight: bold; border: 1px solid #e0e0e0;
    }
    .bullish { color: #09ab3b; } 
    .bearish { color: #ff2b2b; } 
    .neutral { color: #888; font-style: italic; }

    

    /*  Tabs 美化 (加大字体版)  */
    button[data-baseweb="tab"] { 
        font-size: 26px !important;  /* 增大到 26px */
        font-weight: 700 !important; /* 粗体 */
        padding: 15px 40px !important; /* 增加内边距 */
        color: #888 !important; 
    }
    button[data-baseweb="tab"][aria-selected="true"] { 
        color: #000 !important; 
        font-weight: 900 !important; /* 选中时特粗 */
        border-bottom: none !important; 
    }
    [data-testid="stMetricValue"] { font-size: 24px; color: #333 !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 数据获取引擎
# ==========================================
@st.cache_data(ttl=3600)
def get_fred_data(api_key, series_ids, start_date='2010-01-01'): 
    if not api_key: return pd.DataFrame()
    fred = Fred(api_key=api_key)
    data = {}
    try:
        for name, series_id in series_ids.items():
            series = fred.get_series(series_id, observation_start=start_date)
            data[name] = series
        return pd.DataFrame(data).fillna(method='ffill')
    except Exception as e:
        st.error(f"API Error: {e}")
        return pd.DataFrame()
    
        
# ==========================================
# 3. 模块 A: 系统流动性 (周频)
# ==========================================
def render_module_a(df_all):
  

    df_raw = df_all[df_all.index >= '2020-01-01'].copy()

    df = pd.DataFrame()
    df['WALCL'] = df_raw['WALCL'].resample('W-WED').last() 
    df['WTREGEN'] = df_raw['WTREGEN'].resample('W-WED').mean()
    df['RRPONTSYD'] = df_raw['RRPONTSYD'].resample('W-WED').mean()
    df['WRESBAL'] = df_raw['WRESBAL'].resample('W-WED').mean()
    df = df.fillna(method='ffill').dropna()

    if df['RRPONTSYD'].mean() < 10000:
        df['RRP_Clean'] = df['RRPONTSYD'] * 1000
    else:
        df['RRP_Clean'] = df['RRPONTSYD']

    df['Net_Liquidity'] = df['WALCL'] - df['WTREGEN'] - df['RRP_Clean']
    
    def get_score(series):
        return series.diff(13).rank(pct=True) * 100
    
    df['Score_Reserves'] = get_score(df['WRESBAL'])
    df['Score_NetLiq'] = get_score(df['Net_Liquidity'])
    df['Score_TGA'] = get_score(-df['WTREGEN'])
    df['Score_RRP'] = get_score(-df['RRP_Clean']) 
    
    df['Total_Score'] = (
        df['Score_NetLiq'] * 0.5 + df['Score_TGA'] * 0.2 + 
        df['Score_RRP'] * 0.2 + df['Score_Reserves'] * 0.1
    )

    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 核心指标
    c1, c2, c3, c4 = st.columns(4)
    score_color = "#09ab3b" if latest['Total_Score'] > 50 else "#ff2b2b"
    c1.markdown(f"""
        <div class="metric-card"><div class="metric-label">A模块综合得分（周频）</div>
        <div class="metric-value" style="color: {score_color}">{latest['Total_Score']:.1f}</div></div>
    """, unsafe_allow_html=True)
    
    c2.metric("净流动性 (Net Liq)", f"${latest['Net_Liquidity']/1000000:.2f} T", 
              f"{(latest['Net_Liquidity'] - prev['Net_Liquidity'])/1000:.0f} B (vs上周)", delta_color="normal")
    c3.metric("Fed 总资产", f"${latest['WALCL']/1000000:.2f} T", 
              f"{(latest['WALCL'] - prev['WALCL'])/1000:.0f} B (vs上周)", delta_color="normal")
    c4.metric("逆回购 (RRP)", f"${latest['RRP_Clean']/1000:.0f} B", 
              f"{(latest['RRP_Clean'] - prev['RRP_Clean'])/1000:.0f} B (vs上周)", delta_color="normal")

    # 细分得分
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("##### 🧩 因子细分得分 (贡献度分析)")
    sub1, sub2, sub3, sub4 = st.columns(4)
    def sub_score_card(label, value):
        color = "#09ab3b" if value > 50 else "#ff2b2b"
        return f"""<div class="sub-card"><div class="sub-label">{label}</div><div class="sub-value" style="color: {color}">{value:.1f}</div></div>"""

    sub1.markdown(sub_score_card("Net Liq 得分 (50%)", latest['Score_NetLiq']), unsafe_allow_html=True)
    sub2.markdown(sub_score_card("TGA 得分 (20%)", latest['Score_TGA']), unsafe_allow_html=True)
    sub3.markdown(sub_score_card("RRP 得分 (20%)", latest['Score_RRP']), unsafe_allow_html=True)
    sub4.markdown(sub_score_card("准备金得分 (10%)", latest['Score_Reserves']), unsafe_allow_html=True)

    # 图表
    st.divider()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Total_Score'], name='A模块体系流动性分数', line=dict(color='#09ab3b', width=2), yaxis='y2'))
    fig.add_trace(go.Scatter(x=df.index, y=df['Net_Liquidity'], name='Net Liquidity ($ 规模)', line=dict(color='#33CFFF', width=2), fill='tozeroy', fillcolor='rgba(51, 207, 255, 0.1)'))
    
    y_min, y_max = df['Net_Liquidity'].min() * 0.95, df['Net_Liquidity'].max() * 1.02
    fig.update_layout(title="A模块得分 vs 市场净流动性趋势", height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='black'),
        yaxis=dict(title='Amount ($)', showgrid=False, range=[y_min, y_max]),
        yaxis2=dict(title='Score (0-100)', overlaying='y', side='right', range=[0, 100], showgrid=True, gridcolor='#e0e0e0'), hovermode="x unified", legend=dict(orientation="h", y=1.1, x=0))
    st.plotly_chart(fig, use_container_width=True)

    
    # TGA 曲线
    # 原始数据 WTREGEN 单位是 Million，除以 1000 变 Billion
    fig_tga = go.Figure()
    fig_tga.add_trace(go.Scatter(x=df.index, y=df['WTREGEN']/1000, name='TGA 余额 ($B)', 
                                 line=dict(color='#d97706', width=2), fill='tozeroy', fillcolor='rgba(217, 119, 6, 0.1)'))
    
    # 阈值线 (4000亿 和 8000亿)
    fig_tga.add_hline(y=400, line_dash="dash", line_color="#09ab3b", annotation_text="利好区 (<400B)", annotation_position="bottom right")
    fig_tga.add_hline(y=800, line_dash="dash", line_color="#ff2b2b", annotation_text="警戒区 (>800B)", annotation_position="top right")

    fig_tga.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='black'),
                          title="TGA 余额趋势 ($B)", hovermode="x unified", yaxis_title="Billions ($)")
    st.plotly_chart(fig_tga, use_container_width=True)

    # 百科
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📚 A模块：因子专业定义与市场逻辑 (点击展开)", expanded=False):
        st.markdown("""
        <div class="glossary-box" style="border-left: 4px solid #6c5ce7; background-color: #f8f6ff;">
            <div class="glossary-title" style="color: #6c5ce7;">📊 核心量化模型逻辑 (Methodology)</div>
            <div class="glossary-content">
                本模块得分基于动量趋势 + 历史分位双重校验，满分 100 分（50分=中性）：<br>
                <b>1. 数据清洗：</b> 所有数据统一重采样为周频（Week-Ending Wednesday），剔除日间噪音。<br>
                <b>2. 趋势因子：</b> 采用 13周（即一个季度）的滚动变化量，捕捉中期流动性拐点。<br>
                <b>3. 历史打分：</b> 将当前趋势置于历史数据中进行百分位排名 (Percentile Rank)。例如得分 90 表示当前流动性环境优于历史上 90% 的时期。<br>
                <b>4. 权重模型：</b>
                <br>&nbsp;&nbsp;• <b>Fed净流动性 </b>：50% - 核心权重，代表真实购买力。
                <br>&nbsp;&nbsp;• <b>TGA，RRP </b>：各 20% - 辅助权重，代表资金分流压力。
                <br>&nbsp;&nbsp;• <b>银行准备金 </b>：10% - 基础权重，代表银行体系安全垫。
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="glossary-box">
            <div class="glossary-title">1. 银行准备金 (Bank Reserves / WRESBAL)</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> 商业银行存放在美联储的现金储备。<br>
                <span class="glossary-label">专业解读：</span> 这是金融体系的<b>“基础血液”</b>。它代表了银行体系内部可用的即时流动性。准备金越充裕，银行应对挤兑的能力越强，同时也具备更强的信贷扩张（放贷）潜力。
            </div>
            <div class="logic-row">
                <span class="bullish">⬆️ 上升 = 🟢 利好 (信贷扩张潜力增加)</span>
                <span class="bearish">⬇️ 下降 = 🔴 利空 (流动性缓冲变薄)</span>
            </div>
        </div>
        <div class="glossary-box">
            <div class="glossary-title">2. Fed 净流动性 (Net Liquidity)</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> 美联储资产负债表总规模 - (TGA账户余额 + ON RRP余额)。<br>
                <span class="glossary-label">专业解读：</span> 这是目前市场最关注的<b>“真实流动性”</b>指标。虽然美联储的总资产可能很高，但如果钱被锁在TGA（财政部）或ON RRP（逆回购）里，市场是拿不到这笔钱的。<br>
            </div>
            <div class="logic-row">
                <span class="bullish">⬆️ 上升 = 🟢 利好 (真实流动性增加)</span>
                <span class="bearish">⬇️ 下降 = 🔴 利空 (真实流动性收缩)</span>
            </div>
        </div>
        <div class="glossary-box">
            <div class="glossary-title">3. TGA (Treasury General Account)</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> 美国财政部在美联储的“存款账户”（政府的钱包）。<br>
                <span class="glossary-label">专业解读：</span> 这是一个<b>“流动性抽水机”</b>。当政府发债存钱或收税时，资金从市场流向 TGA（抽水）；当政府花钱时，资金回流市场（注水）。<br>
                <span class="glossary-label">实战阈值：</span><br>
                &nbsp;&nbsp;• <b>&lt; 4000亿美元：</b> 🟢 资金回流市场 (利好)<br>
                &nbsp;&nbsp;• <b>4000 - 8000亿：</b> ⚪ 中性震荡<br>
                &nbsp;&nbsp;• <b>&gt; 8000亿美元：</b> 🔴 流动性枯竭/回购紧缩风险 (利空)<br>
                <span class="glossary-label">关键规则：</span> 若 <b>TGA↑ 且 SOFR↑</b>，市场即入<b>危险区</b> (政府抽水+银行抢钱 = 崩盘前兆)。
            </div>
            <div class="logic-row">
                <span class="bearish">⬆️ 上升 = 🔴 利空 (资金被抽走)</span>
                <span class="bullish">⬇️ 下降 = 🟢 利好 (资金回流市场)</span>
            </div>
        </div>
        <div class="glossary-box">
            <div class="glossary-title">4. ON RRP 用量 (Overnight Reverse Repurchase Agreements)</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> 隔夜逆回购协议，即货币市场基金等机构把多余的现金借给美联储，换取利息。<br>
                <span class="glossary-label">专业解读：</span> 这是一个<b>“资金蓄水池”或“闲置资金停车场”</b>。当ON RRP用量很高时，说明市场上资金过剩但缺乏好的投资标的。
            </div>
            <div class="logic-row">
                <span class="bearish">⬆️ 上升 = 🔴 利空 (资金闲置/空转)</span>
                <span class="bullish">⬇️ 下降 = 🟢 利好 (资金重新激活)</span>
            </div>
        </div>
        <div class="glossary-box" style="border-left: 4px solid #888;">
            <div class="glossary-title">5. Fed 总资产 (Fed Total Assets) [仅展示]</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> 美联储资产负债表的总规模 (WALCL)。<br>
                <span class="glossary-label">专业解读：</span> 代表了央行资产负债表的扩张(QE)与收缩(QT)周期。它是大周期的水位，但短期对市场的影响常被 TGA/RRP 对冲。
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📄 查看 原始数据明细"):
        st.dataframe(df.sort_index(ascending=False))

# ==========================================
# 4. 模块 B: 资金价格与走廊摩擦
# ==========================================
def render_module_b(df_raw):
    """
    B模块: 资金价格与走廊摩擦 
    
    核心逻辑:
    1. 政策制度 (40%): 利率趋势 + 绝对水平判别
    2. 摩擦压力 (60%): 天花板/地板/分裂 + SRF预警
    """
    df = df_raw.copy().dropna()
    
    # ========================================
    # Part 1: 政策利率制度评分
    # ========================================
    
    # 1.1 计算13周移动平均 (政策趋势)
    df['SOFR_MA13'] = df['SOFR'].rolling(65, min_periods=1).mean()  # 13周*5天
    df['SOFR_Trend'] = df['SOFR_MA13'].diff(21)  # 1个月变化率
    
    # 1.2 趋势评分 (下降=宽松=高分)
    df['Score_Trend'] = df['SOFR_Trend'].rolling(1260, min_periods=1).rank(pct=True, ascending=False) * 100
    
    # 1.3 绝对水平制度调整
    def get_regime_bonus(sofr):
        """根据利率绝对水平给予奖惩"""
        if sofr < 1.0:    return 20   # 极度宽松 (零利率时代)
        elif sofr < 2.5:  return 10   # 宽松
        elif sofr > 5.0:  return -20  # 极度紧缩
        elif sofr > 4.0:  return -10  # 紧缩
        else:             return 0    # 中性 (2.5-4.0%)
    
    df['Regime_Bonus'] = df['SOFR'].apply(get_regime_bonus)
    
    # 1.4 政策得分 (0-100)
    df['Score_Policy'] = (df['Score_Trend'] + df['Regime_Bonus']).clip(0, 100)
    
    # ========================================
    # Part 2: 走廊摩擦压力评分
    # ========================================
    
    # 2.1 摩擦因子1: SOFR-IORB (天花板穿透监控)
    df['F1_Spread'] = df['SOFR'] - df['IORB']
    df['F1_Baseline'] = df['F1_Spread'].rolling(126, min_periods=1).median()
    df['F1_Dev'] = df['F1_Spread'] - df['F1_Baseline']
    
    #  只惩罚正向穿透
    df['F1_Penalty'] = df['F1_Dev'].clip(lower=0)  # 负数归零
    df['Score_F1'] = df['F1_Penalty'].rolling(1260, min_periods=1).rank(pct=True, ascending=False) * 100
    
    # 2.2 摩擦因子2: SOFR-RRP (地板距离监控)
    df['F2_Spread'] = df['SOFR'] - df['RRPONTSYAWARD']
    df['F2_Baseline'] = df['F2_Spread'].rolling(126, min_periods=1).median()
    df['F2_Dev'] = (df['F2_Spread'] - df['F2_Baseline']).abs()  # 双向监控
    df['Score_F2'] = df['F2_Dev'].rolling(1260, min_periods=1).rank(pct=True, ascending=False) * 100
    
    # 2.3 摩擦因子3: TGCR-SOFR (回购市场分裂)
    df['F3_Spread'] = df['TGCRRATE'] - df['SOFR']
    df['F3_Baseline'] = df['F3_Spread'].rolling(126, min_periods=1).median()
    df['F3_Dev'] = (df['F3_Spread'] - df['F3_Baseline']).abs()
    df['Score_F3'] = df['F3_Dev'].rolling(1260, min_periods=1).rank(pct=True, ascending=False) * 100
    
    # 2.4 SRF预警因子 
    def get_srf_score(srf_value):
        """SRF用量越高，得分越低"""
        if srf_value == 0:
            return 100  # 无使用 = 最佳
        elif srf_value < 10:   # <100亿 (单位B)
            return 80
        elif srf_value < 25:  # 100-250亿
            return 50
        elif srf_value < 50:  # 250-500亿
            return 20
        else:
            return 0   # >500亿 = 危机
    
    df['Score_SRF'] = df['RPONTSYD'].apply(get_srf_score)
    
    # 2.5 动态权重逻辑
    def get_friction_weights(srf_value):
        """SRF暴涨时提升其权重"""
        if srf_value > 10:  # 非正常模式
            return {'F1': 0.15, 'F2': 0.15, 'F3': 0.10, 'SRF': 0.60}
        else:  # 正常模式
            return {'F1': 0.33, 'F2': 0.33, 'F3': 0.33, 'SRF': 0}
    
    # 2.6 计算摩擦压力分数
    df['Score_Friction'] = df.apply(
        lambda row: (
            row['Score_F1'] * get_friction_weights(row['RPONTSYD'])['F1'] +
            row['Score_F2'] * get_friction_weights(row['RPONTSYD'])['F2'] +
            row['Score_F3'] * get_friction_weights(row['RPONTSYD'])['F3'] +
            row['Score_SRF'] * get_friction_weights(row['RPONTSYD'])['SRF']
        ), axis=1
    )
    
    # ========================================
    # Part 3: B模块综合得分
    # ========================================
    df['Total_Score'] = (
        df['Score_Policy'] * 0.40 +    # 政策趋势 40%
        df['Score_Friction'] * 0.60    # 摩擦压力 60%
    )
    
    # ========================================
    # Part 4: 可视化展示
    # ========================================
    df_view = df[df.index >= '2021-01-01'].copy()
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # --- KPI 卡片 ---
    c1, c2, c3, c4 = st.columns(4)
    
    score_color = "#09ab3b" if latest['Total_Score'] > 50 else "#ff2b2b"
    c1.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">B模块综合得分(日频)</div>
            <div class="metric-value" style="color: {score_color}">{latest['Total_Score']:.1f}</div>
        </div>
    """, unsafe_allow_html=True)
    
    c2.metric(
        "担保隔夜融资利率(SOFR)", 
        f"{latest['SOFR']:.2f}%", 
        f"{(latest['SOFR'] - prev['SOFR']):.2f}%", 
        delta_color="inverse"
    )
    
    spread_val_bps = latest['F1_Spread'] * 100
    prev_spread_bps = prev['F1_Spread'] * 100
    c3.metric(
        "走廊摩擦 (SOFR - IORB)", 
        f"{spread_val_bps:.1f} bps", 
        f"{(spread_val_bps - prev_spread_bps):.1f} bps", 
        delta_color="inverse"
    )
    
    # SRF显示优化
    srf_val = latest['RPONTSYD']
    if srf_val == 0:
        srf_str, srf_color = "$0 B", "off"
    elif srf_val > 10:
        srf_str, srf_color = f"${srf_val:.1f} B", "inverse"
    else:
        srf_str, srf_color = f"${srf_val:.0f} B", "inverse"
    
    c4.metric("急救室用量 (SRF)", srf_str, 
              f"{(latest['RPONTSYD'] - prev['RPONTSYD']):.0f}", 
              delta_color=srf_color)
    
    # --- 细分得分 ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("##### 🧩 因子细分得分 (贡献度分析)")
    sub1, sub2, sub3, sub4, sub5 = st.columns(5)
    
    def sub_score_card(label, value):
        color = "#09ab3b" if value > 50 else "#ff2b2b"
        return f"""<div class="sub-card"><div class="sub-label">{label}</div>
                   <div class="sub-value" style="color: {color}">{value:.1f}</div></div>"""
    
    sub1.markdown(sub_score_card("政策制度 (40%)", latest['Score_Policy']), unsafe_allow_html=True)
    sub2.markdown(sub_score_card("摩擦压力 (60%)", latest['Score_Friction']), unsafe_allow_html=True)
    sub3.markdown(sub_score_card("SRF预警", latest['Score_SRF']), unsafe_allow_html=True)
    
    st.divider()
    
    # --- 图表1: 综合得分趋势 ---
    fig_score = go.Figure()
    fig_score.add_trace(go.Scatter(
        x=df_view.index, y=df_view['Total_Score'], 
        name='B模块综合得分', 
        line=dict(color='#09ab3b', width=2), 
        fill='tozeroy', fillcolor='rgba(9, 171, 59, 0.1)'
    ))
    fig_score.add_hline(y=50, line_dash="dash", line_color="#888", 
                        annotation_text="中性线 (50)", annotation_position="right")
    fig_score.update_layout(
        height=300, 
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        title="B模块综合得分: 得分越高 = 环境越宽松 | 得分越低 = 环境越紧缩",
        hovermode="x unified",
        yaxis=dict(range=[0, 100], title='Score', showgrid=True)
    )
    st.plotly_chart(fig_score, use_container_width=True)
    
    # --- 图表2: 利率走廊 ---
    fig_corridor = go.Figure()
    fig_corridor.add_trace(go.Scatter(x=df_view.index, y=df_view['IORB'], 
                                      name='天花板 (IORB)', 
                                      line=dict(color='#ff2b2b', width=2, dash='dash')))
    fig_corridor.add_trace(go.Scatter(x=df_view.index, y=df_view['RRPONTSYAWARD'], 
                                      name='地板 (RRP)', 
                                      line=dict(color='#09ab3b', width=2, dash='dash')))
    fig_corridor.add_trace(go.Scatter(x=df_view.index, y=df_view['SOFR'], 
                                      name='市场利率 (SOFR)', 
                                      line=dict(color='#0068c9', width=3)))
    fig_corridor.add_trace(go.Scatter(x=df_view.index, y=df_view['SOFR_MA13'], 
                                      name='SOFR 趋势 (13周MA)', 
                                      line=dict(color='#a855f7', width=1.5, dash='dot')))
    
    y_min = min(df_view['IORB'].min(), df_view['SOFR'].min(), df_view['RRPONTSYAWARD'].min()) - 0.5
    y_max = max(df_view['IORB'].max(), df_view['SOFR'].max(), df_view['RRPONTSYAWARD'].max()) + 0.5
    
    fig_corridor.update_layout(
        height=400, 
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        title="利率走廊监控: 观察 SOFR 是否突破天花板或远离地板",
        hovermode="x unified",
        yaxis=dict(range=[y_min, y_max], title='Rate (%)', showgrid=True),
        legend=dict(orientation="h", y=1.1, x=0)
    )
    st.plotly_chart(fig_corridor, use_container_width=True)
    
    # --- 图表3: 天花板摩擦 (优化版) ---
    pos_spread = (df_view['F1_Spread'] * 100).clip(lower=0)
    neg_spread = (df_view['F1_Spread'] * 100).clip(upper=0)
    
    fig_spread = go.Figure()
    fig_spread.add_trace(go.Scatter(
        x=df_view.index, y=pos_spread, 
        name='危险区 (SOFR > IORB)', 
        line=dict(color='#ff2b2b', width=2), 
        fill='tozeroy', fillcolor='rgba(255, 43, 43, 0.5)'
    ))
    fig_spread.add_trace(go.Scatter(
        x=df_view.index, y=neg_spread, 
        name='安全区 (SOFR < IORB)', 
        line=dict(color='#09ab3b', width=2), 
        fill='tozeroy', fillcolor='rgba(9, 171, 59, 0.2)'
    ))
    
    fig_spread.update_layout(
        height=350,
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        title="走廊摩擦(SOFR - IORB): 红灯 = 缺钱 (SOFR突破天花板) | 绿灯 = 正常",
        hovermode="x unified",
        yaxis=dict(title='Spread (bps)', showgrid=True, zeroline=True)
    )
    st.plotly_chart(fig_spread, use_container_width=True)
    
    # --- 图表4: SRF 预警仪表盘 ---
    fig_srf = go.Figure()
    fig_srf.add_trace(go.Scatter(
        x=df_view.index, y=df_view['RPONTSYD'], 
        name='SRF 用量', 
        line=dict(color='#ff6b6b', width=2),
        fill='tozeroy', fillcolor='rgba(255, 107, 107, 0.2)'
    ))
    
    # 阈值线
    fig_srf.add_hline(y=10, line_dash="dash", line_color="#ffa500", 
                      annotation_text="警戒线 (100亿)", annotation_position="right")
    fig_srf.add_hline(y=50, line_dash="dash", line_color="#ff2b2b", 
                      annotation_text="危机线 (500亿)", annotation_position="right")
    
    fig_srf.update_layout(
        height=350,
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        title="SRF 急救室用量: 用量越高 = 压力越大 | 暴涨后骤降 = 救助成功",
        hovermode="x unified",
        yaxis=dict(title='Billions ($)', showgrid=True)
    )
    st.plotly_chart(fig_srf, use_container_width=True)
    
    # 百科
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📚 B模块：因子专业定义与市场逻辑 (点击展开)", expanded=False):
        st.markdown("""
        <div class="glossary-box" style="border-left: 4px solid #6c5ce7; background-color: #f8f6ff;">
            <div class="glossary-title" style="color: #6c5ce7;">📊 核心量化模型逻辑 (Methodology)</div>
            <div class="glossary-content">
                本模块得分旨在量化资金成本与传导顺畅度，采用两层加权模型：<br>
                <b>总分 = 政策制度得分 (40%) + 摩擦压力得分 (60%)</b><br><br>
                <b>1. 政策制度 (Policy Regime)：</b> 
                <br>&nbsp;&nbsp; 结合利率绝对水平（低利率加分）与 13周变化趋势（降息趋势加分）。<br>
                <b>2. 摩擦压力 (Market Friction)：</b> 
                <br>&nbsp;&nbsp; <b>基准偏离度 (Z-Score思路)</b>：计算 SOFR/TGCR 相对其 126天移动中枢的偏离程度。
                <br>&nbsp;&nbsp; <b>非对称惩罚</b>：仅当 SOFR 突破天花板 (IORB) 时给予重罚，正常波动不扣分。
                <br>&nbsp;&nbsp; <b>动态权重 </b>：一旦监测到 SRF 用量激增，模型自动进入“非正常模式”，将 SRF 在摩擦压力权重从 0% 提至 60%，迅速拉低总分以发出警报。
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="glossary-box">
            <div class="glossary-title">1. EFFR (联邦基金利率)</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> 无抵押隔夜资金价格 (政策锚)。<br>
                <span class="glossary-label">专业解读：</span> 这是美联储政策利率的“靶心”，代表了无风险的基准融资成本。
            </div>
            <div class="logic-row">
                <span class="bullish">⬇️ 下降 = 🟢 更松 (降息周期)</span>
                <span class="bearish">⬆️ 上升 = 🔴 更紧 (加息周期)</span>
            </div>
        </div>

        <div class="glossary-box">
            <div class="glossary-title">2. SOFR (担保隔夜融资利率)</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> 有抵押隔夜回购资金价格 (市场真实价格)。<br>
                <span class="glossary-label">专业解读：</span> 用国债做抵押借钱的成本。它是回购市场的核心定价基准。
            </div>
            <div class="logic-row">
                <span class="bullish">⬇️ 下降 = 🟢 更松 (资金成本下降)</span>
                <span class="bearish">⬆️ 上升 = 🔴 更紧 (资金成本上升)</span>
            </div>
        </div>

        <div class="glossary-box">
            <div class="glossary-title">3. IORB (准备金利息率)</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> 准备金利率 (政策天花板)。<br>
                <span class="glossary-label">专业解读：</span> 银行把钱存在美联储能拿到的无风险利息。理论上，银行不应以低于此利率把钱借给别人。
            </div>
            <div class="logic-row">
                <span class="bullish">⬇️ 下降 = 🟢 更松 (政策放松)</span>
                <span class="bearish">⬆️ 上升 = 🔴 更紧 (政策收紧)</span>
            </div>
        </div>

        <div class="glossary-box">
            <div class="glossary-title">4. RRP Award Rate (逆回购利率)</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> 逆回购利率 (政策地板)。<br>
                <span class="glossary-label">专业解读：</span> 机构把钱借给美联储能拿到的利息。这是市场利率的下限。
            </div>
            <div class="logic-row">
                <span class="bullish">⬇️ 下降 = 🟢 更松 (政策放松)</span>
                <span class="bearish">⬆️ 上升 = 🔴 更紧 (政策收紧)</span>
            </div>
        </div>

        <div class="glossary-box">
            <div class="glossary-title">5. SRF (常备回购便利)（正常时不计权）</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> 银行向美联储申请紧急贷款的金额 (Standing Repo Facility)。<br>
                <span class="glossary-label">专业解读：</span> 这是回购市场压力的<b>最重要实时信号</b>。监测银行是否启用了紧急贷款。<br>
                <span class="glossary-label">实战阈值：</span><br>
                &nbsp;&nbsp;• <b>&lt; 100亿美元：</b> 🟢 正常 (中性策略)<br>
                &nbsp;&nbsp;• <b>100 - 500亿美元：</b> 🟡 压力酝酿 (开始配置黄金/BTC)<br>
                &nbsp;&nbsp;• <b>&gt; 500亿美元：</b> 🔴 财政部失能 (准备迎接大放水救助/Risk On)
            </div>
            <div class="logic-row">
                <span class="bullish">⬇️ 用量低/零 = 🟢 更松 (资金充裕)</span>
                <span class="bearish">⬆️ 暴涨后崩盘 = 🟢 注入成功 (做多风险资产)</span>
            </div>
        </div>
        
        <div class="glossary-box">
            <div class="glossary-title">6. TGCR (第三方一般担保回购利率)</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> 三方回购一般抵押品利率。<br>
                <span class="glossary-label">专业解读：</span> 代表最标准、最优质的抵押品融资成本。
            </div>
            <div class="logic-row">
                <span class="bullish">⬇️ 下降 = 🟢 更松</span>
                <span class="bearish">⬆️ 上升 = 🔴 更紧</span>
            </div>
        </div>

        <div class="glossary-box">
            <div class="glossary-title">7. 走廊摩擦 1 (SOFR - IORB)</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> SOFR 相对于 IORB 的异常偏离 (穿顶监测)。<br>
                <span class="glossary-label">专业解读：</span> 只要 SOFR 冲破 IORB (正值)，就说明市场上的钱比央行的钱还贵，流动性告急。
            </div>
            <div class="logic-row">
                <span class="bullish">⬇️ 偏离度低 (负值) = 🟢 更松 (越负越好)</span>
                <span class="bearish">⬆️ 偏离度高 (正值) = 🔴 更紧 (极度紧缺)</span>
            </div>
        </div>

        <div class="glossary-box">
            <div class="glossary-title">8. 走廊摩擦 2 (SOFR - RRP)</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> SOFR 相对于地板的平均分布偏离 (离地监测)。<br>
                <span class="glossary-label">专业解读：</span> 监测资金是否开始脱离“地板区”。
            </div>
            <div class="logic-row">
                <span class="bullish">⬇️ 偏离度低 = 🟢 更松 (越贴近地板越好)</span>
                <span class="bearish">⬆️ 偏离度高 = 🔴 更紧 (开始收紧)</span>
            </div>
        </div>

        <div class="glossary-box">
            <div class="glossary-title">9. 抵押品/回购摩擦 (TGCR - SOFR)</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> 两条回购利率的分层/传导偏离。<br>
                <span class="glossary-label">专业解读：</span> 反映回购市场内部是否存在“血管堵塞”，资金传导是否顺畅。
            </div>
            <div class="logic-row">
                <span class="bullish">⬇️ 偏离度低 = 🟢 更松 (越接近0越好)</span>
                <span class="bearish">⬆️ 偏离度高 = 🔴 更紧 (传导不畅)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📄 查看 原始数据明细"):
        st.dataframe(df.sort_index(ascending=False))
# ==========================================
# 6. 模块 C: 国债曲线与期限结构
# ==========================================
def render_module_c(df_raw):
    """
    C模块: 国债曲线与期限结构
    逻辑:
    1. 绝对利率 (Level): 低 = 松 (Risk-On) | 高 = 紧
    2. 期限利差 (Slope): MID_BEST 逻辑 (适度正斜率最好，倒挂或过陡都扣分)
    """
    df = df_raw.copy().dropna()

    # --- 1. 因子计算 ---
    # 1.1 绝对利率得分 (越低越好 -> 宽松)
    # 使用过去5年(1260天)的分位数排名反转
    def get_level_score(series):
        return series.rolling(1260, min_periods=1).rank(pct=True, ascending=False) * 100

    df['Score_10Y'] = get_level_score(df['DGS10'])
    df['Score_2Y'] = get_level_score(df['DGS2'])
    df['Score_30Y'] = get_level_score(df['DGS30'])

    # 1.2 曲线斜率得分 (MID_BEST 逻辑)
    # 目标: 50bps (0.5%), 容忍带: +/- 150bps
    # 逻辑: 距离目标越近分越高，倒挂(负值)或过陡(>2%)都低分
    def get_slope_score(series, target=0.5, tolerance=1.5):
        # 计算距离目标的绝对偏差
        deviation = (series - target).abs()
        # 归一化: 偏差越大，分数越低。
        # 简单线性衰减模型: Score = 100 - (deviation / tolerance * 80)
        score = 100 - (deviation / tolerance * 80) 
        return score.clip(0, 100)

    df['Score_Curve_2s10s'] = get_slope_score(df['T10Y2Y'], target=0.5, tolerance=1.5) # 10Y-2Y
    df['Score_Curve_3m10s'] = get_slope_score(df['T10Y3M'], target=0.75, tolerance=2.0) # 10Y-3M

    # --- 2. 综合得分 ---
    # 权重: 曲线形态(利差)通常比绝对水平更能预测衰退/复苏
    df['Total_Score'] = (
        df['Score_Curve_2s10s'] * 0.30 + 
        df['Score_Curve_3m10s'] * 0.30 +
        df['Score_10Y'] * 0.20 +
        df['Score_2Y'] * 0.10 +
        df['Score_30Y'] * 0.10
    )

    # --- 3. 页面展示 ---
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # KPI 卡片
    c1, c2, c3, c4 = st.columns(4)
    score_color = "#09ab3b" if latest['Total_Score'] > 50 else "#ff2b2b"
    
    c1.markdown(f"""
        <div class="metric-card"><div class="metric-label">C模块综合得分 (日频)</div>
        <div class="metric-value" style="color: {score_color}">{latest['Total_Score']:.1f}</div></div>
    """, unsafe_allow_html=True)

    c2.metric("10Y 基准利率", f"{latest['DGS10']:.2f}%", f"{(latest['DGS10']-prev['DGS10'])*100:.0f} bps", delta_color="inverse")
    
    # 利差颜色逻辑: 倒挂(负数)为红
    spread_2s10s = latest['T10Y2Y']
    s_color = "normal" if spread_2s10s > 0 else "inverse"
    c3.metric("10Y-2Y 关键利差", f"{spread_2s10s:.2f}%", f"{(spread_2s10s-prev['T10Y2Y'])*100:.0f} bps", delta_color=s_color)
    
    c4.metric("30Y 长端利率", f"{latest['DGS30']:.2f}%", f"{(latest['DGS30']-prev['DGS30'])*100:.0f} bps", delta_color="inverse")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("##### 🧩 因子细分得分")
    
    s1, s2, s3, s4, s5 = st.columns(5)
    def sub_card(label, val):
        col = "#09ab3b" if val > 50 else "#ff2b2b"
        return f"""<div class="sub-card"><div class="sub-label">{label}</div><div class="sub-value" style="color:{col}">{val:.1f}</div></div>"""
    
    s1.markdown(sub_card("10Y-2Y 形态 (30%)", latest['Score_Curve_2s10s']), unsafe_allow_html=True)
    s2.markdown(sub_card("10Y-3M 形态 (30%)", latest['Score_Curve_3m10s']), unsafe_allow_html=True)
    s3.markdown(sub_card("10Y 水平 (20%)", latest['Score_10Y']), unsafe_allow_html=True)
    s4.markdown(sub_card("2Y 水平 (10%)", latest['Score_2Y']), unsafe_allow_html=True)
    s5.markdown(sub_card("30Y 水平 (10%)", latest['Score_30Y']), unsafe_allow_html=True)

    st.divider()

    # --- 图表区 ---
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        fig_curve = go.Figure()
        
        # 1. 定义全期限列表 (X轴)
        terms_label = ['1M', '3M', '6M', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '20Y', '30Y']
        # 2. 对应的列名 (确保 series_ids 里有这些 key)
        terms_col = ['DGS1MO', 'DGS3MO', 'DGS6MO', 'DGS1', 'DGS2', 'DGS3', 'DGS5', 'DGS7', 'DGS10', 'DGS20', 'DGS30']
        
        # 3. 提取当前数据 (处理可能存在的 NaN，如果某期限没数据则不画点)
        current_rates = [latest.get(col, None) for col in terms_col]
        
        # 4. 绘制当前曲线
        fig_curve.add_trace(go.Scatter(
            x=terms_label, 
            y=current_rates, 
            mode='lines+markers', 
            name='当前曲线 (Now)', 
            line=dict(color='#0068c9', width=3, shape='spline'), # shape='spline' 让线条更平滑
            marker=dict(size=8)
        ))
        
        # 5. 绘制对比曲线 (例如：1个月前)
        try:
            ago_idx = df.index.get_loc(latest.name - timedelta(days=30), method='nearest')
            ago_row = df.iloc[ago_idx]
            ago_rates = [ago_row.get(col, None) for col in terms_col]
            
            fig_curve.add_trace(go.Scatter(
                x=terms_label, 
                y=ago_rates, 
                mode='lines+markers', 
                name='1个月前 (Last Month)', 
                line=dict(color='#a0a0a0', width=2, dash='dot', shape='spline'),
                opacity=0.6
            ))
        except:
            pass

        fig_curve.update_layout(
            title="🇺🇸 美债全期限收益率曲线 (Full Yield Curve)", 
            height=400,
            yaxis_title="Yield (%)", 
            hovermode="x unified",
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(title="Maturity")
        )
        st.plotly_chart(fig_curve, use_container_width=True)

    # 图2: 10Y-2Y 历史走势 (倒挂监测)
    with col_chart2:
        df_view = df[df.index >= '2020-01-01']
        fig_spread = go.Figure()
        
        # 绘制 0轴
        fig_spread.add_hline(y=0, line_color="black", line_width=1)
        
        # 倒挂区域填红
        fig_spread.add_trace(go.Scatter(x=df_view.index, y=df_view['T10Y2Y'], name='10Y-2Y Spread',
                                      line=dict(color='#333'), fill='tozeroy', 
                                      fillcolor='rgba(9, 171, 59, 0.2)')) # 默认为绿
        
        # 添加红色倒挂部分 (简化显示：0轴以下为红)
        fig_spread.add_hrect(y0=-2, y1=0, fillcolor="red", opacity=0.1, line_width=0, annotation_text="倒挂警示区 (衰退)")
        
        fig_spread.update_layout(title="10Y-2Y 关键利差趋势", height=350,
                               yaxis_title="Spread (%)", hovermode="x unified",
                               paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_spread, use_container_width=True)

    # 百科
        st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📚 C模块：因子专业定义与量化逻辑 (点击展开)", expanded=False):
        st.markdown("""
        <div class="glossary-box" style="border-left: 4px solid #6c5ce7; background-color: #f8f6ff;">
            <div class="glossary-title" style="color: #6c5ce7;">📊 核心量化模型逻辑 (Methodology)</div>
            <div class="glossary-content">
                C模块关注资金的时间价值与经济预期。算法包含两种逻辑：<br>
                <b>1. 绝对水平 (Level)：</b> 采用 <b>Percentile Rank</b>。名义利率越高，融资成本越贵，得分越低。<br>
                <b>2. 曲线形态 (Slope) - MID_BEST模型：</b> 曲线并非越陡越好。
                <br>&nbsp;&nbsp;• <b>目标 (Target)</b>：利差 +50bps (0.5%) 视为最健康的“复苏/温和增长”形态。
                <br>&nbsp;&nbsp;• <b>倒挂 (Inverted)</b>：利差 < 0，预示衰退，严重扣分。
                <br>&nbsp;&nbsp;• <b>过陡 (Steep)</b>：利差 > 150bps，预示通胀失控或期限溢价过高，同样扣分。
            </div>
        </div>

        <div class="glossary-box">
            <div class="glossary-title">1. 10Y-2Y 利差 (The Yield Curve) - 权重 30%</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> 10年期利率减去2年期利率。<br>
                <span class="glossary-label">专业解读：</span> 全球第一的<b>“衰退预警指标”</b>。它反映了短端政策利率与长端增长预期的博弈。
            </div>
            <div class="logic-row">
                <span class="bullish">适度正斜率 (0-150bps) = 🟢 利好 (经济健康复苏)</span>
                <span class="bearish">负值倒挂 (<0bps) = 🔴 衰退预警 (央行紧缩过头)</span>
            </div>
        </div>

        <div class="glossary-box">
            <div class="glossary-title">2. 10Y-3M 利差 (Near-Term Forward Spread) - 权重 30%</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> 10年期利率减去3个月利率。<br>
                <span class="glossary-label">专业解读：</span> 相比10Y-2Y，美联储更看重这个指标。它直接对比了“当下现金成本”与“长期投资回报”。如果3个月利息比10年还高，银行放贷动力枯竭，信贷周期终结。
            </div>
            <div class="logic-row">
                <span class="bullish">曲线变陡 = 🟢 利好 (降息预期/复苏)</span>
                <span class="bearish">深度倒挂 = 🔴 衰退确认 (硬着陆风险极高)</span>
            </div>
        </div>

        <div class="glossary-box">
            <div class="glossary-title">3. 10Y 名义利率 (10Y Nominal Rate) - 权重 20%</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> 10年期国债收益率，全球资产定价之锚。<br>
                <span class="glossary-label">专业解读：</span> 它是DCF模型的分母。10Y利率上升，意味着未来的现金流折现到现在价值变低，直接杀估值（尤其是纳斯达克/成长股）。
            </div>
            <div class="logic-row">
                <span class="bullish">⬇️ 利率下行 = 🟢 利好 (估值扩张/分母变小)</span>
                <span class="bearish">⬆️ 利率上行 = 🔴 利空 (估值收缩/分母变大)</span>
            </div>
        </div>
        
        <div class="glossary-box">
            <div class="glossary-title">4. 2Y 名义利率 (2Y Nominal Rate) - 权重 10%</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> 对美联储未来政策路径最敏感的利率。<br>
                <span class="glossary-label">专业解读：</span> 2Y利率是美联储政策的“影子”。如果2Y利率暴涨，说明市场预期美联储将加息或维持高利率更久 (Higher for Longer)。
            </div>
            <div class="logic-row">
                <span class="bullish">⬇️ 利率下行 = 🟢 利好 (预期降息/Pivot)</span>
                <span class="bearish">⬆️ 利率上行 = 🔴 利空 (预期加息/紧缩)</span>
            </div>
        </div>

        <div class="glossary-box">
            <div class="glossary-title">5. 30Y 名义利率 (30Y Nominal Rate) - 权重 10%</div>
            <div class="glossary-content">
                <span class="glossary-label">含义：</span> 超长期限融资成本。<br>
                <span class="glossary-label">专业解读：</span> 反映了<b>“期限溢价”</b>和对美国财政赤字的担忧。如果30Y飙升，往往意味着市场担心美国发债太多或长期通胀失控。
            </div>
            <div class="logic-row">
                <span class="bullish">⬇️ 利率下行 = 🟢 利好 (通胀预期稳定)</span>
                <span class="bearish">⬆️ 利率上行 = 🔴 利空 (财政担忧/久期杀伤)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📄 查看 原始数据明细"):
        st.dataframe(df.sort_index(ascending=False))

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
    df = df_raw.copy().dropna()
    
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

    # KPI
    c1, c2, c3, c4 = st.columns(4)
    score_color = "#09ab3b" if latest['Total_Score'] > 50 else "#ff2b2b"
    
    c1.markdown(f"""
        <div class="metric-card"><div class="metric-label">D模块综合得分 (日频)</div>
        <div class="metric-value" style="color: {score_color}">{latest['Total_Score']:.1f}</div></div>
    """, unsafe_allow_html=True)

    # 实际利率
    c2.metric("10Y 实际利率 (TIPS)", f"{latest['DFII10']:.2f}%", f"{(latest['DFII10']-prev['DFII10'])*100:.0f} bps", delta_color="inverse")
    
    # 通胀预期 (Breakeven)
    be_val = latest['T10YIE']
    # 离2.1%越远越危险
    be_color = "normal" if 1.8 < be_val < 2.5 else "off"
    c3.metric("10Y 通胀预期 (Breakeven)", f"{be_val:.2f}%", f"{(be_val-prev['T10YIE'])*100:.0f} bps", delta_color=be_color)
    
    c4.metric("5Y 实际利率", f"{latest['DFII5']:.2f}%", f"{(latest['DFII5']-prev['DFII5'])*100:.0f} bps", delta_color="inverse")

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
        

# ==========================================
# Dashboard 
# ==========================================
def render_dashboard_standalone(df_all):
    
    df_raw_a = df_all[df_all.index >= '2020-01-01'].copy()
    
    df_a = pd.DataFrame()
    df_a['WALCL'] = df_raw_a['WALCL'].resample('W-WED').last() 
    df_a['WTREGEN'] = df_raw_a['WTREGEN'].resample('W-WED').mean()
    df_a['RRPONTSYD'] = df_raw_a['RRPONTSYD'].resample('W-WED').mean()
    df_a['WRESBAL'] = df_raw_a['WRESBAL'].resample('W-WED').mean()
    df_a = df_a.fillna(method='ffill').dropna()

    if df_a['RRPONTSYD'].mean() < 10000:
        df_a['RRP_Clean'] = df_a['RRPONTSYD'] * 1000
    else:
        df_a['RRP_Clean'] = df_a['RRPONTSYD']

    df_a['Net_Liquidity'] = df_a['WALCL'] - df_a['WTREGEN'] - df_a['RRP_Clean']
    
    def get_score_a(series):
        return series.diff(13).rank(pct=True) * 100
    
    df_a['Score_NetLiq'] = get_score_a(df_a['Net_Liquidity'])
    df_a['Score_TGA'] = get_score_a(-df_a['WTREGEN'])
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
    df_b['F1_Penalty'] = (df_b['F1_Spread'] - df_b['F1_Spread'].rolling(126, min_periods=1).median()).clip(lower=0)
    df_b['Score_F1'] = df_b['F1_Penalty'].rolling(1260, min_periods=1).rank(pct=True, ascending=False) * 100
    
    df_b['F2_Spread'] = df_b['SOFR'] - df_b['RRPONTSYAWARD']
    df_b['F2_Dev'] = (df_b['F2_Spread'] - df_b['F2_Spread'].rolling(126, min_periods=1).median()).abs()
    df_b['Score_F2'] = df_b['F2_Dev'].rolling(1260, min_periods=1).rank(pct=True, ascending=False) * 100
    
    df_b['F3_Spread'] = df_b['TGCRRATE'] - df_b['SOFR']
    df_b['F3_Dev'] = (df_b['F3_Spread'] - df_b['F3_Spread'].rolling(126, min_periods=1).median()).abs()
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
    
    df_c['Total_Score'] = (
        df_c['Score_Curve_2s10s']*0.3 + df_c['Score_Curve_3m10s']*0.3 + 
        df_c['Score_10Y']*0.2 + df_c['Score_2Y']*0.1 + df_c['Score_30Y']*0.1
    )


    df_d = df_all.copy().dropna()
    df_d['Score_Real_10Y'] = df_d['DFII10'].rolling(1260, min_periods=1).rank(pct=True, ascending=False) * 100
    df_d['Score_Real_5Y'] = df_d['DFII5'].rolling(1260, min_periods=1).rank(pct=True, ascending=False) * 100
    
    df_d['Score_Breakeven'] = get_slope_score(df_d['T10YIE'], 2.1, 0.6) 
    
    df_d['Total_Score'] = (
        df_d['Score_Real_10Y']*0.4 + df_d['Score_Real_5Y']*0.3 + df_d['Score_Breakeven']*0.3
    )

    # --------------------------------------------------------
    # 5. 渲染 Dashboard
    # --------------------------------------------------------

    score_a = df_a['Total_Score'].iloc[-1]
    score_b = df_b['Total_Score'].iloc[-1]
    score_c = df_c['Total_Score'].iloc[-1]
    score_d = df_d['Total_Score'].iloc[-1]
    
    prev_a = df_a['Total_Score'].iloc[-2]
    prev_b = df_b['Total_Score'].iloc[-2]
    prev_c = df_c['Total_Score'].iloc[-2]
    prev_d = df_d['Total_Score'].iloc[-2]
    
    total_score = score_a*0.3 + score_b*0.3 + score_c*0.2 + score_d*0.2
    total_prev = prev_a*0.3 + prev_b*0.3 + prev_c*0.2 + prev_d*0.2
    
    # UI 部分
    st.markdown("###  宏观环境 (Macro Dashboard)")
    col_main, col_sub = st.columns([1, 2])
    
    with col_main:
        color = "#09ab3b" if total_score > 60 else ("#ff2b2b" if total_score < 40 else "#d97706")
        st.markdown(f"""
            <div class="metric-card" style="border-top: 6px solid {color}; padding: 30px;">
                <div class="metric-label" style="font-size: 18px;">宏观综合得分</div>
                <div class="metric-value" style="font-size: 48px; color: {color}">{total_score:.1f}</div>
                <div class="metric-label">vs上期: {total_score - total_prev:+.1f}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with col_sub:
        c1, c2, c3, c4 = st.columns(4)
        def kpi(col, label, val, prev_v):
            c = "#09ab3b" if val > 50 else "#ff2b2b"
            col.metric(label, f"{val:.1f}", f"{val - prev_v:.1f}")
            
        kpi(c1, "A.流动性 (30%)", score_a, prev_a)
        kpi(c2, "B.资金面 (30%)", score_b, prev_b)
        kpi(c3, "C.国债结构 (20%)", score_c, prev_c)
        kpi(c4, "D.实际利率 (20%)", score_d, prev_d)
        
        st.markdown("<br>", unsafe_allow_html=True)
        k1, k2, k3, k4 = st.columns(4)
        if (df_all['WTREGEN'].iloc[-1] - df_all['WTREGEN'].iloc[-5]) > 0: k1.error("TGA抽水（周）") 
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
        
        # 计算日频的历史总分
        s_total = s_a*0.3 + s_b*0.3 + s_c*0.2 + s_d*0.2
        recent = idx[idx >= (datetime.now() - timedelta(days=360))]
        
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
        
        # 4. C (橙色虚线) - 新增
        fig_trend.add_trace(go.Scatter(x=recent, y=s_c.loc[recent], name='C.国债', 
                                       line=dict(color='#d97706', width=1.5, dash='dot')))
        
        # 5. D (红色虚线) - 新增
        fig_trend.add_trace(go.Scatter(x=recent, y=s_d.loc[recent], name='D.实际利率', 
                                       line=dict(color='#ff2b2b', width=1.5, dash='dot')))
        
        fig_trend.update_layout(height=350, margin=dict(l=0,r=0,t=10,b=0), legend=dict(orientation="h", y=1.1), hovermode="x unified")
        st.plotly_chart(fig_trend, use_container_width=True)

    with c_right:
        # 1. 获取最新数据状态
        latest_tga = df_all['WTREGEN'].iloc[-1]
        prev_tga = df_all['WTREGEN'].iloc[-5] # 一周前
        latest_srf = df_all['RPONTSYD'].iloc[-1]
        latest_sofr = df_all['SOFR'].iloc[-1]
        prev_sofr = df_all['SOFR'].iloc[-20] # 一个月前
        
        # 2. 智能逻辑判断
        # TGA 变动 (下降为好)
        tga_down = (latest_tga - prev_tga) < 0 
        # SRF 状态 (低位 < 50亿 算忽略不计)
        srf_low = latest_srf < 5
        # SOFR 状态 (月度变化 < 5bp 算稳定)
        sofr_stable = abs(latest_sofr - prev_sofr) < 0.05
        
        # 3. 生成结论
        if tga_down and srf_low and sofr_stable:
            status_text = "🟢 流动性状态：NET INFLOW (净流入)"
            status_color = "#09ab3b"
        elif (not tga_down) or (not srf_low) or (latest_sofr - prev_sofr > 0.05):
            # 只要有一个坏因子冒头，就倾向于流出/压力
            status_text = "🔴 流动性状态：NET OUTFLOW (净流出/压力)"
            status_color = "#ff2b2b"
        else:
            status_text = "⚪ 流动性状态：NEUTRAL (震荡)"
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
            title="(流入：TGA下降，SRF低位，SOFR稳定/ 流出：TGA上升，SRF高企，SOFR攀升)", height=350, 
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
        
    # --- 🔥 新增：真理检验区 (Score vs SP500 vs BTC) ---
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

# ==========================================
# 5. 主程序入口
# ==========================================
st.title("宏观金融环境模块因子量化")

series_ids = {
    'WALCL': 'WALCL', 'WTREGEN': 'WTREGEN', 'RRPONTSYD': 'RRPONTSYD', 'WRESBAL': 'WRESBAL',
    'DFF': 'DFF', 'SOFR': 'SOFR', 'IORB': 'IORB', 
    'RRPONTSYAWARD': 'RRPONTSYAWARD', 'TGCRRATE': 'TGCRRATE', 'RPONTSYD': 'RPONTSYD',
    'DGS1MO': 'DGS1MO', 'DGS3MO': 'DGS3MO', 'DGS6MO': 'DGS6MO', 'DGS1': 'DGS1', 'DGS2': 'DGS2', 
    'DGS3': 'DGS3', 'DGS5': 'DGS5', 'DGS7': 'DGS7', 'DGS10': 'DGS10', 'DGS20': 'DGS20', 'DGS30': 'DGS30',
    'T10Y2Y': 'T10Y2Y', 'T10Y3M': 'T10Y3M',
    'DFII10': 'DFII10', 'DFII5': 'DFII5', 'T10YIE': 'T10YIE',
    'SP500': 'SP500',
    'CBBTCUSD': 'CBBTCUSD', 
}

with st.spinner('正在同步美联储全量数据...'):
    df_all = get_fred_data(API_KEY, series_ids, start_date='2010-01-01')

if not df_all.empty:
    latest_date = df_all.index[-1]
    date_display = f"{datetime.now().strftime('%Y-%m-%d')} (实时)" if latest_date > datetime.now() else latest_date.strftime('%Y-%m-%d')
    st.markdown(f"#### 📅 数据截至: **{date_display}**")
    st.markdown("---")

    # 定义 Tabs
    tab_dash, tab1, tab2, tab3, tab4 = st.tabs([
        " DASHBOARD", 
        "A. 系统流动性", 
        "B. 资金价格与摩擦",
        "C. 国债期限结构",
        "D. 实际利率与通胀"
    ])
    
    with tab_dash:
        render_dashboard_standalone(df_all)
    with tab1:
        render_module_a(df_all)
    with tab2:
        render_module_b(df_all)
    with tab3:
        render_module_c(df_all)
    with tab4:
        render_module_d(df_all)
else:
    st.error("数据加载失败，请检查网络或 API Key。")
