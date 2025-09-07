import pandas as pd
from sqlalchemy import create_engine
import streamlit as st

# -------------------------
# Paths dos bancos de dados
# -------------------------
DB_PATH_CORR = "sqlite:///correlation.db"
DB_PATH_RS = "sqlite:///performance.db"

# -------------------------
# Engines de conexão
# -------------------------
engine_corr = create_engine(DB_PATH_CORR)
engine_rs = create_engine(DB_PATH_RS)

# -------------------------
# Funções de carregamento
# -------------------------
@st.cache_data(ttl=300)
def load_corr_data(_engine=engine_corr):
    df = pd.read_sql("SELECT * FROM rolling_correlation_long", con=_engine)
    df["Date"] = pd.to_datetime(df["Date"])
    return df

@st.cache_data(ttl=300)
def load_rs_data(_engine=engine_rs):
    df = pd.read_sql("SELECT * FROM relative_strength_long", con=_engine)
    df["Date"] = pd.to_datetime(df["Date"])
    return df

@st.cache_data(ttl=300)
def load_price_data(_engine=engine_rs):
    df = pd.read_sql("SELECT * FROM asset_prices", con=_engine)
    df["Date"] = pd.to_datetime(df["Date"])
    return df

# -------------------------
# Função para última atualização
# -------------------------
@st.cache_data
def get_last_update(_engine, table_name):
    query = f"SELECT MAX(Date) as last_update FROM {table_name}"
    df = pd.read_sql(query, con=_engine)
    return df["last_update"].iloc[0]
