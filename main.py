# main.py
import streamlit as st
from datetime import datetime
import pandas as pd

# 1. 导入配置和数据引擎
from config import API_KEY, GEMINI_API_KEY, SERIES_IDS, CSS_STYLE
from data_engine import get_mixed_data

# 2. 导入各个业务模块
from modules.dashboard import render_dashboard_standalone
from modules.module_a import render_module_a
from modules.module_b import render_module_b
from modules.module_c import render_module_c
from modules.module_d import render_module_d
from modules.module_e import render_module_e

# ==========================================
# 页面初始化
# ==========================================
st.set_page_config(page_title="宏观金融环境量化", layout="wide", page_icon="📈")
st.markdown(CSS_STYLE, unsafe_allow_html=True)

# ==========================================
# 数据加载
# ==========================================
with st.spinner('正在同步美联储全量数据...'):
    df_all = get_mixed_data(API_KEY, SERIES_IDS, start_date='2010-01-01')

# ==========================================
# 主逻辑
# ==========================================
if not df_all.empty:
    # 定义导航（支持卡片跳转）
    nav_items = [
        ("DASHBOARD", "dashboard"),
        ("A. 系统流动性", "module_a"),
        ("B. 资金价格与摩擦", "module_b"),
        ("C. 国债期限结构", "module_c"),
        ("D. 实际利率与通胀", "module_d"),
        ("E. 外部冲击与汇率", "module_e"),
        
    ]
    nav_labels = [n[0] for n in nav_items]
    nav_slug_map = {n[0]: n[1] for n in nav_items}
    nav_label_map = {n[1]: n[0] for n in nav_items}

    # 如果卡片点击带了 nav 参数，优先切换
    nav_param = st.query_params.get("nav", None)
    if nav_param in nav_label_map:
        st.session_state.nav_choice = nav_label_map[nav_param]
        st.query_params.clear()

    if "nav_choice" not in st.session_state:
        st.session_state.nav_choice = nav_items[0][0]

    nav_choice = st.session_state.nav_choice

    # 顶部标题 + AI 按钮（仅 Dashboard 显示）
    header_left, header_right = st.columns([0.72, 0.28])
    with header_left:
        st.markdown('<div class="page-title">宏观金融环境模块因子量化</div>', unsafe_allow_html=True)
    with header_right:
        st.markdown('<div class="page-subtle" style="text-align:right;">&nbsp;</div>', unsafe_allow_html=True)
        if nav_choice == "DASHBOARD":
            st.markdown('<div class="jump-ai-btn-wrap"><a class="jump-ai-btn" href="#ai-macro">AI 宏观分析</a></div>', unsafe_allow_html=True)

    latest_date = df_all.index[-1]
    date_display = f"{datetime.now().strftime('%Y-%m-%d')} (实时)" if latest_date > datetime.now() else latest_date.strftime('%Y-%m-%d')
    st.markdown("---")

    # 侧边栏卡片导航
    with st.sidebar:
        st.markdown("### 导航")
        st.caption(f"数据截至: {date_display}")
        for label in nav_labels:
            if st.session_state.nav_choice == label:
                st.markdown(
                    f'<div class="nav-card active"><div class="nav-card-title">{label}</div></div>',
                    unsafe_allow_html=True
                )
            else:
                if st.button(label, key=f"nav_{label}", use_container_width=True):
                    st.session_state.nav_choice = label
                    st.rerun()

    # 页面渲染（同页切换）
    if nav_choice == "DASHBOARD":
        render_dashboard_standalone(df_all)
    elif nav_choice == "A. 系统流动性":
        render_module_a(df_all)
    elif nav_choice == "B. 资金价格与摩擦":
        render_module_b(df_all)
    elif nav_choice == "C. 国债期限结构":
        render_module_c(df_all)
    elif nav_choice == "D. 实际利率与通胀":
        render_module_d(df_all)
    elif nav_choice == "E. 外部冲击与汇率":
        render_module_e(df_all)
else:
    st.error("数据加载失败，请检查网络或 API Key。")

