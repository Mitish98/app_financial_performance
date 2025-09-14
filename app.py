from datetime import datetime
import streamlit as st
from utils.db import load_corr_data, load_rs_data, load_price_data, get_last_update, engine_rs
from utils.helpers import update_all_data
from pages import rankings, relative_strength, correlation, ai_agent
# -------------------------
# Configuração da página - Hide Side Bar
# -------------------------
st.set_page_config(page_title="📊 Painel de Análises Financeiras", layout="wide")
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
# Esconde a barra lateral de páginas
hide_streamlit_style = """
    <style>
        /* Esconde a barra lateral de navegação (multipage) */
        .css-1d391kg {display: none;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("📊 Painel de Análises Financeiras")

# -------------------------
# Botão de atualização
# -------------------------
if st.button("🔁 Atualizar Todos os Dados"):
    update_all_data()

# -------------------------
# Carregando dados
# -------------------------
with st.spinner("📊 Carregando dados..."):
    df_corr = load_corr_data()
    df_rs = load_rs_data()
    df_prices = load_price_data()
    last_update_perf = get_last_update(engine_rs, "asset_prices")
    last_update_dt = datetime.fromisoformat(str(last_update_perf).split('.')[0])

st.header(f"Última atualização: {last_update_dt.strftime('%d/%m/%Y')}")

# -------------------------
# Período de análise
# -------------------------
period_options = {
    "Últimos 3 dias": 3,
    "Últimos 7 dias": 7,
    "Últimos 21 dias": 21,
    "Últimos 30 dias": 30,
    "Últimos 60 dias": 60,
    "Últimos 90 dias": 90,
    "Últimos 180 dias": 180,
    "Últimos 360 dias": 360
}
selected_period_days = period_options[st.selectbox("🕒 Intervalo de análise:", list(period_options.keys()))]

# -------------------------
# Seleção de abas
# -------------------------
tab_options = ["📊 OHLC","💪 Força Relativa","📈 Correlação","🤖 Agente IA & Machine Learning"]
selected_tab = st.radio("Escolha uma aba:", tab_options, horizontal=True)

if selected_tab == "📊 OHLC":
    rankings.render_rankings(df_prices, selected_period_days)
elif selected_tab == "💪 Força Relativa":
    relative_strength.render_relative_strength(df_rs, df_prices)
elif selected_tab == "📈 Correlação":
    correlation.render_correlation(df_corr)
elif selected_tab == "🔮 Agente IA":
    ai_agent.render_ai_agent(df_prices, df_rs, df_corr)


    
