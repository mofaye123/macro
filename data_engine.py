# data_engine.py
import ssl
import pandas as pd
import streamlit as st
from fredapi import Fred
import yfinance as yf 

# 强制忽略 SSL 证书验证
ssl._create_default_https_context = ssl._create_unverified_context

@st.cache_data(ttl=3600)
def get_mixed_data(api_key, series_ids, start_date='2010-01-01'): 
    """
    同时从 FRED 和 Yahoo Finance 获取数据并合并
    """
    # 1. 获取 FRED 数据
    df_fred = pd.DataFrame()
    if api_key:
        fred = Fred(api_key=api_key)
        data = {}
        try:
            for name, series_id in series_ids.items():
                series = fred.get_series(series_id, observation_start=start_date)
                data[name] = series
            df_fred = pd.DataFrame(data)
        except Exception as e:
            st.error(f"FRED API Error: {e}")
            df_fred = pd.DataFrame()

    # 2. 获取 Yahoo 数据 (DXY)
    # DX-Y.NYB 是美元指数在 Yahoo 的代码
    df_yahoo = pd.DataFrame()
    try:
        # progress=False 隐藏下载进度条
        yahoo_data = yf.download("DX-Y.NYB", start=start_date, progress=False)
        
        # 我们只需要 'Close' 或 'Adj Close'
        if not yahoo_data.empty:
            if 'Close' in yahoo_data.columns:
                dxy_series = yahoo_data['Close']
                
                if dxy_series.index.tz is not None:
                    dxy_series.index = dxy_series.index.tz_localize(None)
                
                df_yahoo = pd.DataFrame(dxy_series)
                df_yahoo.columns = ['DXY'] # 重命名为 DXY
            else:
                st.warning("Yahoo API 返回数据但不包含 Close 列")
    except Exception as e:
        st.warning(f"Yahoo Finance API (DXY) Error: {e}")

    # 3. 合并数据
    # 使用 outer join 确保即使某一侧数据缺失，另一侧也能保留
    if not df_fred.empty and not df_yahoo.empty:
        df_all = df_fred.join(df_yahoo, how='outer')
    elif not df_fred.empty:
        df_all = df_fred
    elif not df_yahoo.empty:
        df_all = df_yahoo
    else:
        return pd.DataFrame()

    # 4. 填充缺失值 (ffill)
    return df_all.fillna(method='ffill').sort_index()
