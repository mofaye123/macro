# data_engine.py
import ssl
import pandas as pd
import streamlit as st
from fredapi import Fred

# 强制忽略 SSL 证书验证
ssl._create_default_https_context = ssl._create_unverified_context

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
