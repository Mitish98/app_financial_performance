import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import subprocess
import sys

# -------------------------
# Configuração inicial
# -------------------------
st.set_page_config(page_title="📊 Finance & Crypto Dashboard", layout="wide")

st.title("📊 Dashboard Integrado - Correlação & Força Relativa")

# =========================
# 1. Seção de Correlação
# =========================
st.header("📈 Análise de Correlação entre Ativos")

try:
    st.info("🔄 Atualizando dados de correlação...")
    subprocess.run([sys.executable, "update_data/correlation.py"], check=True)
    st.success("✅ Dados de correlação atualizados!")
except subprocess.CalledProcessError as e:
    st.error(f"❌ Erro ao atualizar correlação: {e}")
    st.stop()

DB_PATH_CORR = "sqlite:///correlation.db"
engine_corr = create_engine(DB_PATH_CORR)

@st.cache_data(ttl=60)
def load_corr_data():
    query = "SELECT * FROM rolling_correlation_long"
    df = pd.read_sql(query, con=engine_corr)
    df["Date"] = pd.to_datetime(df["Date"])
    return df

with st.spinner("Carregando dados de correlação..."):
    df_corr = load_corr_data()

# --- filtros correlação
available_windows_corr = sorted(df_corr["Window"].unique())
selected_window_corr = st.selectbox("🕓 Selecione o período da correlação móvel:", available_windows_corr, key="window_corr")

df_corr_window = df_corr[df_corr["Window"] == selected_window_corr]

def get_unique_assets(df):
    assets = set()
    for pair in df["Pair"].unique():
        assets.update(pair.split("/"))
    return sorted(list(assets))

assets = ["Todos os ativos"] + get_unique_assets(df_corr_window)
selected_asset_corr = st.selectbox("🔍 Filtrar por ativo:", assets, key="asset_corr")

if selected_asset_corr == "Todos os ativos":
    df_filtered_corr = df_corr_window.copy()
else:
    df_filtered_corr = df_corr_window[df_corr_window["Pair"].str.contains(selected_asset_corr)]

# média de correlação
mean_corr = df_filtered_corr.groupby('Pair')['RollingCorrelation'].mean().reset_index()
mean_corr = mean_corr.sort_values('RollingCorrelation', ascending=False).reset_index(drop=True)
mean_corr['Index'] = mean_corr.index

fig_corr_scatter = px.scatter(
    mean_corr, x='Index', y='RollingCorrelation',
    color='RollingCorrelation', color_continuous_scale='RdBu_r',
    hover_name='Pair', title='Correlação Média dos Pares Selecionados', height=600
)
fig_corr_scatter.update_layout(
    xaxis=dict(
        tickmode='array',
        tickvals=mean_corr['Index'],
        ticktext=mean_corr['Pair'],
        tickangle=45,
        tickfont=dict(size=8)
    ),
    yaxis_range=[-1, 1]
)
st.plotly_chart(fig_corr_scatter, use_container_width=True)

# top correlações último dia
last_date_corr = df_filtered_corr["Date"].max()
df_latest_corr = df_filtered_corr[df_filtered_corr["Date"] == last_date_corr].dropna(subset=["RollingCorrelation"])

st.subheader(f"📅 Rank de correlações em {last_date_corr.date()} (Janela: {selected_window_corr} dias)")

col1, col2 = st.columns(2)
with col1:
    st.markdown("#### 🔝 Top 20 Positivas")
    st.dataframe(df_latest_corr.sort_values("RollingCorrelation", ascending=False).head(20)[["Pair", "RollingCorrelation"]])

with col2:
    st.markdown("#### 🔻 Top 20 Negativas")
    st.dataframe(df_latest_corr.sort_values("RollingCorrelation", ascending=True).head(20)[["Pair", "RollingCorrelation"]])

# gráfico individual
pairs_corr = df_filtered_corr["Pair"].unique()
selected_pair_corr = st.selectbox("Escolha um par para detalhar:", sorted(pairs_corr), key="pair_corr")
df_selected_corr = df_filtered_corr[df_filtered_corr["Pair"] == selected_pair_corr]

fig_corr_line = px.line(
    df_selected_corr, x="Date", y="RollingCorrelation",
    title=f"Correlação Móvel ({selected_window_corr} dias): {selected_pair_corr}",
    labels={"RollingCorrelation": "Correlação", "Date": "Data"}
)
fig_corr_line.update_layout(yaxis_range=[-1, 1], height=500)
st.plotly_chart(fig_corr_line, use_container_width=True)

csv_corr = df_selected_corr.to_csv(index=False).encode("utf-8")
st.download_button("📥 Baixar CSV de Correlação", csv_corr,
                   file_name=f"correlacao_{selected_pair_corr.replace('/', '_')}_{selected_window_corr}d.csv",
                   mime="text/csv")

# =========================
# 2. Seção de Força Relativa
# =========================
st.header("💪 Análise de Força Relativa entre Criptomoedas")

try:
    st.info("🔄 Atualizando dados de performance...")
    subprocess.run([sys.executable, "update_data/rs.py"], check=True)
    st.success("✅ Dados de performance atualizados!")
except subprocess.CalledProcessError as e:
    st.error(f"❌ Erro ao atualizar performance: {e}")
    st.stop()

DB_PATH_RS = "sqlite:///performance.db"
engine_rs = create_engine(DB_PATH_RS)

@st.cache_data(ttl=60)
def load_rs_data():
    query = "SELECT * FROM relative_strength_long"
    df = pd.read_sql(query, con=engine_rs)
    df["Date"] = pd.to_datetime(df["Date"])
    return df

@st.cache_data(ttl=60)
def load_price_data():
    query = "SELECT * FROM asset_prices"
    df = pd.read_sql(query, con=engine_rs)
    df["Date"] = pd.to_datetime(df["Date"])
    return df

with st.spinner("📊 Carregando dados de força relativa..."):
    df_rs = load_rs_data()
    df_prices = load_price_data()

# ranking de performance
st.subheader("📈 Ranking de Performance Absoluta")

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
selected_period_label = st.selectbox("🕒 Período:", list(period_options.keys()), key="period_rs")
selected_period_days = period_options[selected_period_label]

last_date_rs = df_prices["Date"].max()
start_date_rs = last_date_rs - pd.Timedelta(days=selected_period_days)
df_period = df_prices[(df_prices["Date"] >= start_date_rs) & (df_prices["Date"] <= last_date_rs)]

if df_period.empty or df_period["Date"].nunique() < 2:
    st.warning("📆 Intervalo insuficiente para análise.")
else:
    start_prices = df_period[df_period["Date"] == df_period["Date"].min()].set_index("Ticker")["Price"]
    end_prices = df_period[df_period["Date"] == df_period["Date"].max()].set_index("Ticker")["Price"]
    performance = ((end_prices / start_prices) - 1).sort_values(ascending=False)

    volume_total = df_period.groupby("Ticker")["Volume"].sum()
    volume_total.name = "Volume Total"

    indicators_avg = df_period.groupby("Ticker")[["RSI","MACD","MACD_Signal","SMA_20","SMA_50","EMA_20","EMA_50"]].mean().reset_index()

    current_prices = df_period[df_period["Date"] == last_date_rs].set_index("Ticker")["Price"]
    current_prices.name = "Preço Atual"

    performance_df = performance.to_frame(name="Retorno").reset_index()
    performance_df = performance_df.merge(volume_total.reset_index(), on="Ticker", how="left")
    performance_df = performance_df.merge(indicators_avg, on="Ticker", how="left")
    performance_df = performance_df.merge(current_prices.reset_index(), on="Ticker", how="left")

    top_n = st.slider("Número de ativos:", 3, min(20, len(performance_df)), 5, key="top_rs")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"### 🟢 Top {top_n} Ganhadores")
        st.dataframe(performance_df.head(top_n).style.format({
            "Retorno": "{:.2%}", "Volume Total": "{:,.0f}", "RSI": "{:.2f}",
            "MACD": "{:.5f}", "MACD_Signal": "{:.5f}", "SMA_20": "{:.5f}", "SMA_50": "{:.5f}",
            "EMA_20": "{:.5f}", "EMA_50": "{:.5f}", "Preço Atual": "U$ {:,.2f}"
        }), use_container_width=True)

    with col2:
        st.markdown(f"### 🔴 Top {top_n} Perdedores")
        st.dataframe(performance_df.tail(top_n).sort_values("Retorno").style.format({
            "Retorno": "{:.2%}", "Volume Total": "{:,.0f}", "RSI": "{:.2f}",
            "MACD": "{:.5f}", "MACD_Signal": "{:.5f}", "SMA_20": "{:.5f}", "SMA_50": "{:.5f}",
            "EMA_20": "{:.5f}", "EMA_50": "{:.5f}", "Preço Atual": "U$ {:,.2f}"
        }), use_container_width=True)

# gráfico força relativa
st.subheader("📈 Força Relativa entre Criptomoedas")

available_pairs_rs = sorted(df_rs["Pair"].unique())
selected_pair_rs = st.selectbox("Par para análise:", available_pairs_rs, key="pair_rs")

available_windows_rs = sorted(df_rs["Window"].unique())
selected_window_rs = st.selectbox("Janela da média móvel:", available_windows_rs, key="window_rs")

df_selected_rs = df_rs[(df_rs["Pair"] == selected_pair_rs) & (df_rs["Window"] == selected_window_rs)]

fig_rs = px.line()
fig_rs.add_scatter(x=df_selected_rs["Date"], y=df_selected_rs["RS"], mode='lines', name='Força Relativa')
fig_rs.add_scatter(x=df_selected_rs["Date"], y=df_selected_rs["RS_Smooth"], mode='lines', name=f"Média {selected_window_rs} dias")

fig_rs.update_layout(
    title=f"{selected_pair_rs}", xaxis_title="Data", yaxis_title="Base / Quote",
    height=500, yaxis_range=[df_selected_rs["RS"].min() * 0.9, df_selected_rs["RS"].max() * 1.1]
)
st.plotly_chart(fig_rs, use_container_width=True)

csv_rs = df_selected_rs.to_csv(index=False).encode("utf-8")
st.download_button("📥 Baixar CSV de Força Relativa", csv_rs,
                   file_name=f"rs_{selected_pair_rs.replace('/', '_')}_{selected_window_rs}d.csv",
                   mime="text/csv")
