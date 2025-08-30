import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import subprocess
import sys
from datetime import datetime

# -------------------------
# Configuração inicial
# -------------------------
st.set_page_config(page_title="📊 Painel de Análises Financeiras", layout="wide")

# -------------------------
# Função para última atualização
# -------------------------
@st.cache_data
def get_last_update(_engine, table_name):
    query = f"SELECT MAX(Date) as last_update FROM {table_name}"
    df = pd.read_sql(query, con=_engine)
    return df["last_update"].iloc[0]

# -------------------------
# Conexão com bancos de dados
# -------------------------
DB_PATH_CORR = "sqlite:///correlation.db"
engine_corr = create_engine(DB_PATH_CORR)

DB_PATH_RS = "sqlite:///performance.db"
engine_rs = create_engine(DB_PATH_RS)

# Última atualização do banco de performance
last_update_perf = get_last_update(engine_rs, "asset_prices")
last_update_dt = datetime.fromisoformat(str(last_update_perf).split('.')[0])  # converte string para datetime

st.title(f"📊 Painel de Análises Financeiras")
st.header(f"Última atualização: {last_update_dt.strftime('%d/%m/%Y')}")
# Seleção de período
period_options = {"Últimos 3 dias":3,"Últimos 7 dias":7,"Últimos 21 dias":21,"Últimos 30 dias":30,
                      "Últimos 60 dias":60,"Últimos 90 dias":90,"Últimos 180 dias":180,"Últimos 360 dias":360}
selected_period_label = st.selectbox("🕒 Intervalo de análise:", list(period_options.keys()), key="period_rs")
selected_period_days = period_options[selected_period_label]

# -------------------------
# Carregamento de dados
# -------------------------
@st.cache_data(ttl=300)
def load_corr_data():
    df = pd.read_sql("SELECT * FROM rolling_correlation_long", con=engine_corr)
    df["Date"] = pd.to_datetime(df["Date"])
    return df

@st.cache_data(ttl=300)
def load_rs_data():
    df = pd.read_sql("SELECT * FROM relative_strength_long", con=engine_rs)
    df["Date"] = pd.to_datetime(df["Date"])
    return df

@st.cache_data(ttl=300)
def load_price_data():
    df = pd.read_sql("SELECT * FROM asset_prices", con=engine_rs)
    df["Date"] = pd.to_datetime(df["Date"])
    return df

with st.spinner("📊 Carregando dados..."):
    df_corr = load_corr_data()
    df_rs = load_rs_data()
    df_prices = load_price_data()

# -------------------------
# Layout com Tabs
# -------------------------
tab1, tab2, tab3 = st.tabs(["📊 Rankings","💪 Força Relativa", "📈 Correlação"])
# -------------------------
# -------------------------
# -------------------------
# TAB 1: Rankings
# -------------------------
with tab1:
    st.header("📊 Top Performers e Perdedores")
    

    last_date_rs = df_prices["Date"].max()
    start_date_rs = last_date_rs - pd.Timedelta(days=selected_period_days)
    df_period = df_prices[(df_prices["Date"] >= start_date_rs) & (df_prices["Date"] <= last_date_rs)]

    if df_period.empty or df_period["Date"].nunique() < 2:
        st.warning("📆 Intervalo insuficiente para análise.")
    else:
        start_prices = df_period[df_period["Date"] == df_period["Date"].min()].set_index("Ticker")["Price"]
        end_prices = df_period[df_period["Date"] == df_period["Date"].max()].set_index("Ticker")["Price"]
        performance = ((end_prices / start_prices) - 1).sort_values(ascending=False)
        volume_total = df_period.groupby("Ticker")["Volume"].sum().rename("Volume Total")
        indicators_avg = df_period.groupby("Ticker")[["RSI","MACD","MACD_Signal","SMA_20","SMA_50","EMA_20","EMA_50"]].mean()
        current_prices = df_period[df_period["Date"] == last_date_rs].set_index("Ticker")["Price"].rename("Preço Atual")

        performance_df = (performance.to_frame("Retorno")
                          .merge(volume_total, left_index=True, right_index=True)
                          .merge(indicators_avg, left_index=True, right_index=True)
                          .merge(current_prices, left_index=True, right_index=True)
                          .reset_index())

    top_n = st.slider("Número de ativos:", 3, min(20, len(performance_df)), 5, key="top_rs")
    top_pos = performance_df.head(top_n)
    top_neg = performance_df.tail(top_n).sort_values("Retorno")

    col1, col2 = st.columns(2)

    # -------------------------
    # Ganhadores
    # -------------------------
    with col1:
        st.markdown(f"### 🟢 Top {top_n} Ganhadores")
        st.dataframe(top_pos.style.format({
            "Retorno": "{:.2%}", "Volume Total": "{:,.0f}", "RSI": "{:.2f}",
            "MACD": "{:.5f}", "MACD_Signal": "{:.5f}", "SMA_20": "{:.5f}",
            "SMA_50": "{:.5f}", "EMA_20": "{:.5f}", "EMA_50": "{:.5f}",
            "Preço Atual": "U$ {:,.2f}"}), use_container_width=True)

        with st.expander("📊 Detalhes Gráficos"):
            # Gráfico de pizza - Volume
            fig_pos_pie = px.pie(top_pos, values="Volume Total", names="Ticker",
                                 title=f"🟢 Distribuição de Volume - Top {top_n} Ganhadores")
            st.plotly_chart(fig_pos_pie, use_container_width=True)

            # Histórico do RSI inicial (com top 5 por padrão)
            max_initial = min(5, len(top_pos))
            initial_tickers = top_pos["Ticker"].tolist()[:max_initial]

            fig_rsi_hist = go.Figure()
            for ticker in initial_tickers:
                df_t = df_period[df_period["Ticker"] == ticker]
                fig_rsi_hist.add_trace(go.Scatter(
                    x=df_t["Date"], y=df_t["RSI"], mode="lines+markers", name=ticker,
                    line=dict(width=2), marker=dict(size=4)
                ))
            fig_rsi_hist.update_layout(
                title="🟢 Histórico do RSI dos ativos selecionados",
                xaxis_title="Data",
                yaxis_title="RSI",
                height=400
            )
            st.plotly_chart(fig_rsi_hist, use_container_width=True)

            # Multiselect para atualizar gráfico do RSI
            selected_rsi_tickers = st.multiselect(
                "Selecione ativos para histórico do RSI", 
                top_pos["Ticker"].tolist(), 
                default=initial_tickers
            )

            if selected_rsi_tickers:
                fig_rsi_hist = go.Figure()
                for ticker in selected_rsi_tickers:
                    df_t = df_period[df_period["Ticker"] == ticker]
                    fig_rsi_hist.add_trace(go.Scatter(
                        x=df_t["Date"], y=df_t["RSI"], mode="lines+markers", name=ticker,
                        line=dict(width=2), marker=dict(size=4)
                    ))
          

    # -------------------------
    # Perdedores
    # -------------------------
    with col2:
        st.markdown(f"### 🔴 Top {top_n} Perdedores")
        st.dataframe(top_neg.style.format({
            "Retorno": "{:.2%}", "Volume Total": "{:,.0f}", "RSI": "{:.2f}",
            "MACD": "{:.5f}", "MACD_Signal": "{:.5f}", "SMA_20": "{:.5f}",
            "SMA_50": "{:.5f}", "EMA_20": "{:.5f}", "EMA_50": "{:.5f}",
            "Preço Atual": "U$ {:,.2f}"}), use_container_width=True)

        with st.expander("📊 Detalhes Gráficos"):
            # Gráfico de pizza - Volume
            fig_neg_pie = px.pie(top_neg, values="Volume Total", names="Ticker",
                                 title=f"🔴 Distribuição de Volume - Top {top_n} Perdedores")
            st.plotly_chart(fig_neg_pie, use_container_width=True)

            # Histórico do RSI inicial (com top 5 por padrão)
            max_initial_neg = min(5, len(top_neg))
            initial_tickers_neg = top_neg["Ticker"].tolist()[:max_initial_neg]

            fig_rsi_hist_neg = go.Figure()
            for ticker in initial_tickers_neg:
                df_t = df_period[df_period["Ticker"] == ticker]
                fig_rsi_hist_neg.add_trace(go.Scatter(
                    x=df_t["Date"], y=df_t["RSI"], mode="lines+markers", name=ticker,
                    line=dict(width=2), marker=dict(size=4)
                ))
            fig_rsi_hist_neg.update_layout(
                title="🔴 Histórico do RSI dos ativos selecionados",
                xaxis_title="Data",
                yaxis_title="RSI",
                height=400
            )
            st.plotly_chart(fig_rsi_hist_neg, use_container_width=True)

            # Multiselect para atualizar gráfico do RSI
            selected_rsi_tickers_neg = st.multiselect(
                "Selecione ativos para histórico do RSI", 
                top_neg["Ticker"].tolist(), 
                default=initial_tickers_neg
            )

            if selected_rsi_tickers_neg:
                fig_rsi_hist_neg = go.Figure()
                for ticker in selected_rsi_tickers_neg:
                    df_t = df_period[df_period["Ticker"] == ticker]
                    fig_rsi_hist_neg.add_trace(go.Scatter(
                        x=df_t["Date"], y=df_t["RSI"], mode="lines+markers", name=ticker,
                        line=dict(width=2), marker=dict(size=4)
                    ))
            

# -------------------------
# TAB 2: Força Relativa
# -------------------------
# -------------------------
# TAB 2: Força Relativa
# -------------------------
with tab2:
    st.header("💪 Força Relativa entre Criptomoedas")
    
    # Lista de pares disponíveis
    available_pairs_rs = sorted(df_rs["Pair"].unique())
    
    # Define "BTC-USD/ETH-USD" como padrão, se existir na lista
    default_index = available_pairs_rs.index("BTC-USD/ETH-USD") if "BTC-USD/ETH-USD" in available_pairs_rs else 0
    selected_pair_rs = st.selectbox("Par para análise:", available_pairs_rs, index=default_index, key="pair_rs")
    

 
    # Janela da média móvel
    available_windows_rs = sorted(df_rs["Window"].unique())
    selected_window_rs = st.selectbox("Janela da média móvel:", available_windows_rs, key="window_rs")

    # Filtra os dados do par e da janela selecionada
    df_selected_rs = df_rs[(df_rs["Pair"] == selected_pair_rs) & (df_rs["Window"] == selected_window_rs)]

    # Gráfico de Força Relativa
    fig_rs = px.line(
        df_selected_rs, 
        x="Date", 
        y="RS", 
        title=f"Força Relativa - {selected_pair_rs}", 
        labels={"RS": "Força Relativa"}
    )
    fig_rs.add_scatter(
        x=df_selected_rs["Date"], 
        y=df_selected_rs["RS_Smooth"], 
        mode='lines', 
        name=f"Média {selected_window_rs} dias"
    )
    fig_rs.update_layout(height=400)
    
    st.plotly_chart(fig_rs, use_container_width=True)

# -------------------------
# TAB 3: Correlação
# -------------------------
with tab3:
    st.header("📈 Análise de Correlação entre Ativos")
    available_windows_corr = sorted(df_corr["Window"].unique())
    selected_window_corr = st.selectbox("🕓 Janela da correlação móvel:", available_windows_corr, key="window_corr")
    df_corr_window = df_corr[df_corr["Window"] == selected_window_corr]

    def get_unique_assets(df):
        assets = set()
        for pair in df["Pair"].unique():
            assets.update(pair.split("/"))
        return sorted(list(assets))

    assets = get_unique_assets(df_corr_window)
    selected_assets = st.multiselect("🔍 Selecionar ativos:", assets, default=assets[:5])

    if selected_assets:
        df_filtered_corr = df_corr_window[df_corr_window["Pair"].apply(lambda x: any(a in x for a in selected_assets))]
    else:
        df_filtered_corr = df_corr_window.copy()

    last_date_corr = df_filtered_corr["Date"].max()
    df_latest_corr = df_filtered_corr[df_filtered_corr["Date"] == last_date_corr].dropna(subset=["RollingCorrelation"])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🔝 Top Correlações Positivas")
        st.dataframe(df_latest_corr.sort_values("RollingCorrelation", ascending=False).head(10)[["Pair","RollingCorrelation"]])
    with col2:
        st.markdown("#### 🔻 Top Correlações Negativas")
        st.dataframe(df_latest_corr.sort_values("RollingCorrelation", ascending=True).head(10)[["Pair","RollingCorrelation"]])



st.markdown("---")



# -------------------------
# Botões de atualização
# -------------------------
col_upd1, col_upd2 = st.columns(2)
with col_upd2:
    if st.button("🔁 Atualizar Correlações"):
        with st.spinner("Executando script de correlação..."):
            result = subprocess.run([sys.executable, "update_data/correlation_main.py"])
        if result.returncode == 0:
            st.success("✅ Correlações atualizadas com sucesso.")
        else:
            st.error("❌ Erro ao atualizar correlações.")

with col_upd1:
    if st.button("🔁 Atualizar Preços e Indicadores"):
        with st.spinner("Executando script de força relativa..."):
            result = subprocess.run([sys.executable, "update_data/rs_main.py"])
        if result.returncode == 0:
            st.success("✅ Força relativa atualizada com sucesso.")
        else:
            st.error("❌ Erro ao atualizar força relativa.")