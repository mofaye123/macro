# main.py
import streamlit as st
from datetime import datetime
import pandas as pd
import pytz

# 1. 导入配置和数据引擎
from config import API_KEY, SERIES_IDS, CSS_STYLE
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

st.title("宏观金融环境 | 模块因子量化")

# ==========================================
# 数据加载
# ==========================================
with st.spinner('正在同步美联储全量数据...'):
    df_all = get_mixed_data(API_KEY, SERIES_IDS, start_date='2010-01-01')

# ==========================================
# 主逻辑
# ==========================================
if not df_all.empty:
    latest_date = df_all.index[-1]
    est_tz = pytz.timezone('US/Eastern')
    now_est = datetime.now(est_tz)
    if latest_date > datetime.now(): 
        date_display = f"{now_est.strftime('%Y-%m-%d %H:%M')} (美东实时)"
    else:
        date_display = latest_date.strftime('%Y-%m-%d') 

    st.markdown(f"#### 📅 数据截至: **{date_display}**")
    st.markdown("---")

    # 定义 Tabs
    tab_dash, tab1, tab2, tab3, tab4, tab5 = st.tabs([
        " DASHBOARD", 
        "A. 系统流动性", 
        "B. 资金价格与摩擦",
        "C. 国债期限结构",
        "D. 实际利率与通胀",
        "E. 外部冲击与汇率"
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
    with tab5:
        render_module_e(df_all)
else:
    st.error("数据加载失败，请检查网络或 API Key。")
