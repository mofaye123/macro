# config.py
import streamlit as st

# ==========================================
# 0. 核心配置API
# ==========================================
API_KEY = st.secrets["FRED_API_KEY"]


# FRED Series IDs
SERIES_IDS = {
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

# CSS 样式
CSS_STYLE = """
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

    /* Tabs 美化 (加大字体版)  */
    button[data-baseweb="tab"] { 
        font-size: 26px !important; 
        font-weight: 700 !important;
        padding: 15px 40px !important;
        color: #888 !important; 
    }
    button[data-baseweb="tab"][aria-selected="true"] { 
        color: #000 !important; 
        font-weight: 900 !important;
        border-bottom: none !important; 
    }
    [data-testid="stMetricValue"] { font-size: 24px; color: #333 !important; }
</style>
"""
