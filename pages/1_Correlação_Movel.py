import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import subprocess
import sys

# Configuração inicial
st.set_page_config(page_title="Correlação Móvel - Finance", layout="wide")

# Executa o main.py para atualizar o banco de dados
try:
    st.info("🔄 Atualizando dados do banco via...")
    subprocess.run([sys.executable, "update_data/correlation.py"], check=True)
    st.success("✅ Dados atualizados com sucesso!")
except subprocess.CalledProcessError as e:
    st.error(f"❌ Erro ao atualizar os dados: {e}")
    st.stop()

# Configuração do banco
DB_PATH = "sqlite:///correlation.db"
engine = create_engine(DB_PATH)

st.title("📈 Análise de Dados para Correlação entre Ativos")
st.markdown("Este app permite visualizar a correlação móvel entre diferentes pares de ativos financeiros usando dados históricos do Yahoo Finance.")

# Função para carregar dados
@st.cache_data(ttl=60)
def load_data():
    query = "SELECT * FROM rolling_correlation_long"
    df = pd.read_sql(query, con=engine)
    df["Date"] = pd.to_datetime(df["Date"])
    return df

# Carregamento de dados
with st.spinner("Carregando dados do banco de dados..."):
    df_corr = load_data()

# Seletor da janela de correlação móvel
available_windows = sorted(df_corr["Window"].unique())
selected_window = st.selectbox("🕓 Selecione o período da correlação móvel (em dias):", available_windows)

# Filtro por janela
df_corr_window = df_corr[df_corr["Window"] == selected_window]

# Função para extrair moedas únicas dos pares
def get_unique_assets(df):
    assets = set()
    for pair in df["Pair"].unique():
        parts = pair.split("/")
        assets.update(parts)
    return sorted(list(assets))

# Lista de moedas com opção "Todos os ativos"
assets = ["Todos os ativos"] + get_unique_assets(df_corr_window)

# Seletor de moeda (ou todos)
selected_asset = st.selectbox("🔍 Selecione uma moeda para visualizar pares relacionados:", assets)

# Filtragem com base na moeda selecionada
if selected_asset == "Todos os ativos":
    df_filtered = df_corr_window.copy()
    st.markdown("🔎 **Exibindo correlações entre todos os pares disponíveis.**")
else:
    df_filtered = df_corr_window[df_corr_window["Pair"].str.contains(selected_asset)]
    st.markdown(f"🔎 **Exibindo correlações com a moeda `{selected_asset}`.**")

# Média da correlação para os pares filtrados
mean_corr = df_filtered.groupby('Pair')['RollingCorrelation'].mean().reset_index()
mean_corr = mean_corr.sort_values('RollingCorrelation', ascending=False).reset_index(drop=True)
mean_corr['Index'] = mean_corr.index

# Gráfico de dispersão
fig_scatter = px.scatter(
    mean_corr,
    x='Index',
    y='RollingCorrelation',
    color='RollingCorrelation',
    color_continuous_scale='RdBu_r',
    labels={'Index': 'Par de Ativos', 'RollingCorrelation': 'Correlação Média'},
    hover_name='Pair',
    title='Correlação Média dos Pares Selecionados',
    height=600
)
fig_scatter.update_layout(
    xaxis=dict(
        tickmode='array',
        tickvals=mean_corr['Index'],
        ticktext=mean_corr['Pair'],
        tickangle=45,
        tickfont=dict(size=8)
    ),
    yaxis_range=[-1, 1]
)
st.plotly_chart(fig_scatter, use_container_width=True)

# Top de correlações no último dia
last_date = df_filtered["Date"].max()
df_latest = df_filtered[df_filtered["Date"] == last_date].dropna(subset=["RollingCorrelation"])

st.markdown(f"### 📅 Rank de correlações em `{last_date.date()}` (Janela: {selected_window} dias)")

st.markdown("#### 🔝 Top 20 Ativos Correlacionados Positivamente")
top_pos = (
    df_latest.sort_values(by="RollingCorrelation", ascending=False)
    .head(20)[["Pair", "RollingCorrelation"]]
    .reset_index(drop=True)
)
st.dataframe(top_pos, use_container_width=True)

st.markdown("#### 🔻 Top 20 Ativos Correlacionados Negativamente")
top_neg = (
    df_latest.sort_values(by="RollingCorrelation", ascending=True)
    .head(20)[["Pair", "RollingCorrelation"]]
    .reset_index(drop=True)
)
st.dataframe(top_neg, use_container_width=True)

# Seletor de par de ativos
pairs = df_filtered["Pair"].unique()
selected_pair = st.selectbox("Escolha um par de ativos para visualizar a correlação móvel:", sorted(pairs))

# Gráfico linha para par escolhido
df_selected = df_filtered[df_filtered["Pair"] == selected_pair]

fig = px.line(
    df_selected,
    x="Date",
    y="RollingCorrelation",
    title=f"Correlação Móvel de {selected_window} dias: {selected_pair}",
    labels={"RollingCorrelation": "Correlação", "Date": "Data"},
    template="plotly_white",
)
fig.update_layout(yaxis_range=[-1, 1], height=500)
st.plotly_chart(fig, use_container_width=True)

# Botão para download CSV
csv = df_selected.to_csv(index=False).encode("utf-8")
st.download_button(
    label="📥 Baixar dados CSV",
    data=csv,
    file_name=f"correlacao_{selected_pair.replace('/', '_')}_{selected_window}d.csv",
    mime="text/csv",
)

# Tabela completa com filtros
show_full_table = st.checkbox("📋 Visualizar banco de dados completo")
if show_full_table:
    st.markdown("### 🧾 Banco de dados completo - Com filtros")

    unique_pairs = sorted(df_corr_window["Pair"].unique())
    all_option = "-- Todos --"
    options_with_all = [all_option] + unique_pairs

    selected_pairs = st.multiselect("Filtrar por pares de ativos:", options_with_all)
    filtered_pairs = unique_pairs if all_option in selected_pairs else selected_pairs

    min_date = df_corr_window["Date"].min()
    max_date = df_corr_window["Date"].max()
    date_range = st.date_input("Filtrar por intervalo de datas:", [min_date, max_date])

    corr_range = st.slider("Filtrar por intervalo de correlação:", -1.0, 1.0, (-1.0, 1.0), step=0.01)

    if filtered_pairs:
        filtered_df = df_corr_window[
            (df_corr_window["Pair"].isin(filtered_pairs)) &
            (df_corr_window["Date"] >= pd.to_datetime(date_range[0])) &
            (df_corr_window["Date"] <= pd.to_datetime(date_range[1])) &
            (df_corr_window["RollingCorrelation"] >= corr_range[0]) &
            (df_corr_window["RollingCorrelation"] <= corr_range[1])
        ]
        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.info("🔎 Selecione pelo menos um par de ativos para visualizar os dados filtrados.")
