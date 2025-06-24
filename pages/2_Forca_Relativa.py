import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import subprocess
import sys

# Deve ser a primeira chamada de Streamlit
st.set_page_config(page_title="Relative Strength - Cripto", layout="wide")

# Atualização do banco de dados
try:
    st.info("🔄 Atualizando dados do banco via...")
    subprocess.run([sys.executable, "update_data/rs.py"], check=True)

    st.success("✅ Dados atualizados com sucesso!")
except subprocess.CalledProcessError as e:
    st.error(f"❌ Erro ao atualizar os dados: {e}")
    st.stop()

# Configuração do banco
DB_PATH = "sqlite:///performance.db"
engine = create_engine(DB_PATH)

st.title("💪 Análise de Performance entre Criptomoedas")

# -------------------------
# Carregamento de dados
# -------------------------
@st.cache_data(ttl=60)
def load_rs_data():
    query = "SELECT * FROM relative_strength_long"
    df = pd.read_sql(query, con=engine)
    df["Date"] = pd.to_datetime(df["Date"])
    return df

@st.cache_data(ttl=60)
def load_price_data():
    query = "SELECT * FROM asset_prices"
    df = pd.read_sql(query, con=engine)
    df["Date"] = pd.to_datetime(df["Date"])
    return df

with st.spinner("📊 Carregando dados..."):
    df_rs = load_rs_data()
    df_prices = load_price_data()

# -------------------------
# 📈 Ranking de Performance Absoluta
# -------------------------
st.subheader("📈 Ranking de Performance Absoluta com Dados do Banco")

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

selected_period_label = st.selectbox("🕒 Selecione o período de análise:", list(period_options.keys()))
selected_period_days = period_options[selected_period_label]

last_date = df_prices["Date"].max()
start_date = last_date - pd.Timedelta(days=selected_period_days)
df_period = df_prices[(df_prices["Date"] >= start_date) & (df_prices["Date"] <= last_date)]

if df_period.empty or df_period["Date"].nunique() < 2:
    st.warning("📆 Intervalo insuficiente para análise.")
    st.stop()

# Cálculo dos dados
start_prices = df_period[df_period["Date"] == df_period["Date"].min()].set_index("Ticker")["Price"]
end_prices = df_period[df_period["Date"] == df_period["Date"].max()].set_index("Ticker")["Price"]
performance = ((end_prices / start_prices) - 1).sort_values(ascending=False)

volume_total = df_period.groupby("Ticker")["Volume"].sum()
volume_total.name = "Volume Total"

indicators_avg = df_period.groupby("Ticker")[
    ["RSI", "MACD", "MACD_Signal", "SMA_20", "SMA_50", "EMA_20", "EMA_50"]
].mean().reset_index()

current_prices = df_period[df_period["Date"] == last_date].set_index("Ticker")["Price"]
current_prices.name = "Preço Atual"

performance_df = performance.to_frame(name="Retorno").reset_index()
performance_df = performance_df.merge(volume_total.reset_index(), on="Ticker", how="left")
performance_df = performance_df.merge(indicators_avg, on="Ticker", how="left")
performance_df = performance_df.merge(current_prices.reset_index(), on="Ticker", how="left")

top_n = st.slider("Número de ativos a exibir:", 3, min(20, len(performance_df)), 5)

# Ganhadores
st.markdown(f"### 🟢 Top {top_n} Ganhadores em {selected_period_label}")
st.dataframe(
    performance_df.head(top_n).style.format({
        "Retorno": "{:.2%}",
        "Volume Total": "{:,.0f}",
        "RSI": "{:.2f}",
        "MACD": "{:.5f}",
        "MACD_Signal": "{:.5f}",
        "SMA_20": "{:.5f}",
        "SMA_50": "{:.5f}",
        "EMA_20": "{:.5f}",
        "EMA_50": "{:.5f}",
        "Preço Atual": "U$ {:,.2f}"
    }),
    use_container_width=True
)

# Perdedores
st.markdown(f"### 🔴 Top {top_n} Perdedores em {selected_period_label}")
st.dataframe(
    performance_df.tail(top_n).sort_values(by="Retorno").style.format({
        "Retorno": "{:.2%}",
        "Volume Total": "{:,.0f}",
        "RSI": "{:.2f}",
        "MACD": "{:.5f}",
        "MACD_Signal": "{:.5f}",
        "SMA_20": "{:.5f}",
        "SMA_50": "{:.5f}",
        "EMA_20": "{:.5f}",
        "EMA_50": "{:.5f}",
        "Preço Atual": "U$ {:,.2f}"
    }),
    use_container_width=True
)

# -------------------------
# Gráfico de Força Relativa
# -------------------------
st.subheader("📈 Força Relativa entre Criptomoedas")

available_pairs = sorted(df_rs["Pair"].unique())
selected_pair = st.selectbox("Selecione um par para análise:", available_pairs)

available_windows = sorted(df_rs["Window"].unique())
selected_window = st.selectbox("Janela da média móvel:", available_windows)

df_selected = df_rs[
    (df_rs["Pair"] == selected_pair) &
    (df_rs["Window"] == selected_window)
].copy()

fig = px.line()
fig.add_scatter(x=df_selected["Date"], y=df_selected["RS"], mode='lines', name='Força Relativa')
fig.add_scatter(x=df_selected["Date"], y=df_selected["RS_Smooth"], mode='lines', name=f"Média {selected_window} dias")

fig.update_layout(
    title=f"{selected_pair}",
    xaxis_title="Data",
    yaxis_title="Base / Quote",
    height=500,
    yaxis_range=[df_selected["RS"].min() * 0.9, df_selected["RS"].max() * 1.1],
)

st.plotly_chart(fig, use_container_width=True)

csv = df_selected.to_csv(index=False).encode("utf-8")
st.download_button(
    label="📥 Baixar dados CSV",
    data=csv,
    file_name=f"rs_{selected_pair.replace('/', '_')}_{selected_window}d.csv",
    mime="text/csv",
)
