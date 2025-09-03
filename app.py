from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import subprocess
import sys
import numpy as np
import sqlite3
import openai


# Carrega a chave da variável de ambiente
openai.api_key = st.secrets["openai_api_key"]
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

# -------------------------
# Botão de atualização
# -------------------------
if st.button("🔁 Atualizar Todos os Dados"):
    # Atualizar Correlações
    with st.spinner("Executando script de correlação..."):
        result_corr = subprocess.run([sys.executable, "update_data/correlation.py"])
    if result_corr.returncode == 0:
        st.success("✅ Correlações atualizadas com sucesso.")
    else:
        st.error("❌ Erro ao atualizar correlações.")

    # Atualizar Preços e Indicadores
    with st.spinner("Executando script de força relativa..."):
        result_rs = subprocess.run([sys.executable, "update_data/rs.py"])
    if result_rs.returncode == 0:
        st.success("✅ Força relativa atualizada com sucesso.")
    else:
        st.error("❌ Erro ao atualizar força relativa.")

    # Mensagem geral de sucesso
    if result_corr.returncode == 0 and result_rs.returncode == 0:
        st.success("🎉 Todos os dados foram atualizados com sucesso!")

st.header(f"Última atualização: {last_update_dt.strftime('%d/%m/%Y')}")

# Seleção de período
period_options = {
    "Últimos 3 dias": 3, "Últimos 7 dias": 7, "Últimos 21 dias": 21, "Últimos 30 dias": 30,
    "Últimos 60 dias": 60, "Últimos 90 dias": 90, "Últimos 180 dias": 180, "Últimos 360 dias": 360
}
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
# Seleção de "abas" via radio (persistida no session_state)
# -------------------------
tab_options = ["📊 Rankings", "💪 Força Relativa", "📈 Correlação", "🛡️ Gerenciamento de Risco", "🤖 Agente IA"]
# garante que haja um valor inicial coerente no session_state
if "tab_choice" not in st.session_state:
    st.session_state["tab_choice"] = tab_options[0]

selected_tab = st.radio(
    "Escolha uma aba:",
    tab_options,
    index=tab_options.index(st.session_state["tab_choice"]),
    key="tab_choice",
    horizontal=True
)

# -------------------------
# -------------------------
# TAB 1: Rankings (agora ativada por conditional)
# -------------------------
if selected_tab == "📊 Rankings":
    st.header("📊 Top Ganhadores e Perdedores")

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

        # slider seguro mesmo com poucos ativos
        max_n = max(3, min(20, len(performance_df)))
        default_n = min(5, max_n)
        top_n = st.slider("Número de ativos:", min_value=3, max_value=max_n, value=default_n, key="top_rs")

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
                "Preço Atual": "U$ {:,.2f}"}), width='stretch')

            with st.expander("📊 Detalhes Gráficos"):
                # Gráfico de pizza - Volume
                fig_pos_pie = px.pie(top_pos, values="Volume Total", names="Ticker",
                                     title=f"🟢 Distribuição de Volume - Top {top_n} Ganhadores")
                st.plotly_chart(fig_pos_pie, width='stretch')

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
                st.plotly_chart(fig_rsi_hist, width='stretch')

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
                    fig_rsi_hist.update_layout(
                        title="🟢 Histórico do RSI (selecionados)",
                        xaxis_title="Data",
                        yaxis_title="RSI",
                        height=400
                    )
                    st.plotly_chart(fig_rsi_hist, width='stretch')

        # -------------------------
        # Perdedores
        # -------------------------
        with col2:
            st.markdown(f"### 🔴 Top {top_n} Perdedores")
            st.dataframe(top_neg.style.format({
                "Retorno": "{:.2%}", "Volume Total": "{:,.0f}", "RSI": "{:.2f}",
                "MACD": "{:.5f}", "MACD_Signal": "{:.5f}", "SMA_20": "{:.5f}",
                "SMA_50": "{:.5f}", "EMA_20": "{:.5f}", "EMA_50": "{:.5f}",
                "Preço Atual": "U$ {:,.2f}"}), width='stretch')

            with st.expander("📊 Detalhes Gráficos"):
                # Gráfico de pizza - Volume
                fig_neg_pie = px.pie(top_neg, values="Volume Total", names="Ticker",
                                     title=f"🔴 Distribuição de Volume - Top {top_n} Perdedores")
                st.plotly_chart(fig_neg_pie, width='stretch')

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
                st.plotly_chart(fig_rsi_hist_neg, width='stretch')

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
                    fig_rsi_hist_neg.update_layout(
                        title="🔴 Histórico do RSI (selecionados)",
                        xaxis_title="Data",
                        yaxis_title="RSI",
                        height=400
                    )
                    st.plotly_chart(fig_rsi_hist_neg, width='stretch')

        # -------------------------
        # Gráfico de Volatilidade (Área)
        # -------------------------
        st.markdown("### 📈 Volatilidade dos Ativos")

        # Seleção de ativos para volatilidade (combina ganhadores e perdedores)
        all_tickers = list(set(top_pos["Ticker"]).union(set(top_neg["Ticker"])))
        if not all_tickers:
            st.info("Sem ativos suficientes para calcular volatilidade.")
        else:
            selected_vol_tickers = st.multiselect(
                "Selecione ativos para visualizar a volatilidade",
                options=all_tickers,
                default=all_tickers[:min(3, len(all_tickers))]  # até 3 por padrão
            )

            if selected_vol_tickers:
                df_vol = df_period[df_period["Ticker"].isin(selected_vol_tickers)].copy()
                df_vol["Retorno"] = df_vol.groupby("Ticker")["Price"].pct_change()
                # Volatilidade como desvio padrão móvel de 7 dias
                df_vol["Volatilidade"] = df_vol.groupby("Ticker")["Retorno"].transform(lambda x: x.rolling(7).std())

                fig_vol = go.Figure()
                for ticker in selected_vol_tickers:
                    df_t = df_vol[df_vol["Ticker"] == ticker]
                    fig_vol.add_trace(go.Scatter(
                        x=df_t["Date"], y=df_t["Volatilidade"],
                        mode="lines", name=ticker,
                        stackgroup="one",  # cria área empilhada
                        line=dict(width=1.5)
                    ))

                fig_vol.update_layout(
                    title="📊 Volatilidade Histórica (Desvio padrão de retornos diários - 7d)",
                    xaxis_title="Data",
                    yaxis_title="Volatilidade",
                    height=450
                )
                st.plotly_chart(fig_vol, use_container_width=True)

# -------------------------
# TAB 2: Força Relativa
# -------------------------
if selected_tab == "💪 Força Relativa":
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

    st.plotly_chart(fig_rs, width='stretch')

# -------------------------
# TAB 3: Correlação
# -------------------------
if selected_tab == "📈 Correlação":
    st.header("📈 Análise de Correlação entre Ativos")

    # Função para listar ativos únicos
    def get_unique_assets(df):
        assets = set()
        for pair in df["Pair"].unique():
            assets.update(pair.split("/"))
        return sorted(list(assets))

    assets = get_unique_assets(df_corr)

    # Multiselect de ativos para filtrar pares da tabela
    default_assets = [a for a in ["BTC-USD", "ETH-USD"] if a in assets]
    selected_assets = st.multiselect("🔍 Selecionar ativos para filtrar a tabela:", assets, default=default_assets)

    if selected_assets:
        df_filtered_corr = df_corr[df_corr["Pair"].apply(lambda x: any(a in x for a in selected_assets))]
    else:
        df_filtered_corr = df_corr.copy()

    # Tabela de correlações atuais
    last_date_corr = df_filtered_corr["Date"].max()
    df_latest_corr = df_filtered_corr[df_filtered_corr["Date"] == last_date_corr].dropna(subset=["RollingCorrelation"])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🔝 Top Correlações Positivas")
        st.dataframe(df_latest_corr.sort_values("RollingCorrelation", ascending=False).head(10)[["Pair","RollingCorrelation"]])
    with col2:
        st.markdown("#### 🔻 Top Correlações Negativas")
        st.dataframe(df_latest_corr.sort_values("RollingCorrelation", ascending=True).head(10)[["Pair","RollingCorrelation"]])

    # -------------------------
    # Gráfico de correlação móvel do par selecionado
    st.markdown("### 📊 Gráfico da Correlação Móvel")

    # Seleção do par para plot
    available_pairs_plot = sorted(df_filtered_corr["Pair"].unique())
    default_pair = "BTC-USD/ETH-USD" if "BTC-USD/ETH-USD" in available_pairs_plot else available_pairs_plot[0]
    selected_pair_plot = st.selectbox(
        "Escolha o par para visualizar a correlação:",
        available_pairs_plot,
        index=available_pairs_plot.index(default_pair)
    )

    # Janela da correlação móvel aplicada **ao gráfico**
    available_windows_plot = sorted(df_filtered_corr["Window"].unique())
    selected_window_corr = st.selectbox(
        "🕓 Janela da correlação móvel:",
        available_windows_plot,
        index=0  # ou você pode definir um default específico
    )

    # Filtra os dados para o gráfico
    df_pair_plot = df_filtered_corr[
        (df_filtered_corr["Pair"] == selected_pair_plot) &
        (df_filtered_corr["Window"] == selected_window_corr)
    ]

    if not df_pair_plot.empty:
        fig_corr_line = px.line(
            df_pair_plot,
            x="Date",
            y="RollingCorrelation",
            title=f"Correlação Móvel - {selected_pair_plot} ({selected_window_corr} dias)",
            labels={"RollingCorrelation": "Correlação"}
        )
        fig_corr_line.update_layout(height=400)
        st.plotly_chart(fig_corr_line, width='stretch')

# -------------------------
# TAB 4: Gerenciamento de Risco
# -------------------------
if selected_tab == "🛡️ Gerenciamento de Risco":
    st.header("🛡️ Gerenciamento de Risco")

    # ---------- Funções utilitárias ----------
    def safe_float(x):
        try:
            return float(x)
        except Exception:
            return None

    def rr_ratio(entry, stop, tp):
        if tp is None or tp <= 0:
            return None
        risk = abs(entry - stop)
        reward = abs(tp - entry)
        return (reward / risk) if risk > 0 else None

    def breakeven_price(entry, qty, notional, side, fee_rate_open, fee_rate_close):
        fees = notional * (fee_rate_open + fee_rate_close)
        if qty <= 0:
            return None
        if side == "Long":
            return entry + (fees / qty)
        else:
            return entry - (fees / qty)

    def est_liq_price_usdt_linear(entry, lev, mmr, side):
        """
        Estimativa simples para perpétuos lineares USDT (Binance/Bybit-like).
        Ignora variações como funding, fees pendentes e saldo extra na carteira.
        Long:  L ≈ E * (1 - 1/lev + mmr)
        Short: L ≈ E * (1 + 1/lev - mmr)
        """
        if lev is None or lev <= 0:
            return None
        if side == "Long":
            return entry * (1 - 1/lev + mmr)
        else:
            return entry * (1 + 1/lev - mmr)

    # ---------- Inputs ----------
    with st.form("risk_form"):
        st.subheader("Configurações da Operação")

        c1, c2, c3 = st.columns(3)
        mode = c1.selectbox("Modo", ["Futures", "Spot"], index=0)
        side = c2.radio("Direção", ["Long", "Short"], horizontal=True, index=0)
        quote = c3.text_input("Moeda de cotação", "USDT")

        c4, c5, c6 = st.columns(3)
        balance = c4.number_input(f"Saldo total ({quote})", min_value=0.0, value=1000.0, step=10.0, format="%.2f")
        risk_pct = c5.number_input("Risco por trade (%)", min_value=0.0, max_value=100.0, value=1.0, step=0.25, format="%.2f")
        use_fixed_risk = c6.checkbox("Definir risco fixo (em valor)", value=False)

        c7, c8 = st.columns(2)
        fixed_risk = c7.number_input(f"Risco fixo ({quote})", min_value=0.0, value=0.0, step=10.0, format="%.2f", disabled=not use_fixed_risk)
        leverage = c8.number_input("Alavancagem (somente Futures)", min_value=1, max_value=125, value=10, step=1, disabled=(mode=="Spot"))

        st.markdown("---")
        st.subheader("Preços da Estratégia")

        c9, c10, c11 = st.columns(3)
        entry = c9.number_input("Preço de Entrada", min_value=0.0, value=100.0, step=0.1, format="%.6f")
        stop = c10.number_input("Stop Loss", min_value=0.0, value=95.0, step=0.1, format="%.6f")
        tp = c11.number_input("Take Profit (opcional)", min_value=0.0, value=0.0, step=0.1, format="%.6f")

        st.markdown("---")
        st.subheader("Taxas & Manutenção")

        c12, c13, c14 = st.columns(3)
        fee_open_pct = c12.number_input("Taxa de abertura (%)", min_value=0.0, value=0.04, step=0.01, format="%.4f")
        fee_close_pct = c13.number_input("Taxa de fechamento (%)", min_value=0.0, value=0.04, step=0.01, format="%.4f")
        mmr_pct = c14.number_input("Maintenance Margin Rate - MMR (%) (Futures)", min_value=0.0, value=0.5, step=0.1, format="%.3f")

        submitted = st.form_submit_button("Calcular")

    if submitted:
        errors = []
        if entry <= 0 or stop <= 0:
            errors.append("Entrada e Stop devem ser > 0.")
        if side == "Long" and stop >= entry:
            errors.append("Para Long, o Stop deve ser menor que a Entrada.")
        if side == "Short" and stop <= entry:
            errors.append("Para Short, o Stop deve ser maior que a Entrada.")
        if balance <= 0 and not use_fixed_risk:
            errors.append("Saldo deve ser > 0.")
        if use_fixed_risk and fixed_risk <= 0:
            errors.append("Defina um valor de risco fixo > 0 ou desmarque a opção.")

        if errors:
            for e in errors:
                st.error(e)
            st.stop()

        # ---------- Cálculos ----------
        fee_open = fee_open_pct / 100.0
        fee_close = fee_close_pct / 100.0
        mmr = mmr_pct / 100.0

        # risco em valor
        risk_value = fixed_risk if use_fixed_risk else (balance * (risk_pct / 100.0))

        # distância ao stop (em preço)
        stop_dist = abs(entry - stop)

        if stop_dist == 0:
            st.error("A distância entre Entrada e Stop não pode ser zero.")
            st.stop()

        # tamanho da posição (QTD de moedas) pela regra de risco
        qty = risk_value / stop_dist

        # em Spot não há alavancagem; em Futures sim
        notional = entry * qty
        if mode == "Futures":
            margin_required = notional / float(leverage)
        else:
            margin_required = notional  # em Spot, você precisa pagar o notional todo

        # taxas estimadas (abertura + fechamento)
        est_fees = notional * (fee_open + fee_close)

        # preço de break-even considerando taxas
        be_price = breakeven_price(entry, qty, notional, side, fee_open, fee_close)

        # estimativa de liquidação (apenas Futures)
        liq_price = None
        if mode == "Futures":
            liq_price = est_liq_price_usdt_linear(entry, float(leverage), mmr, side)

        # PnL bruto no Stop/TP
        def pnl(exit_price):
            if side == "Long":
                gross = (exit_price - entry) * qty
            else:
                gross = (entry - exit_price) * qty
            # subtrair taxas totais (considerando que haverá taxa na saída)
            return gross - est_fees

        pnl_stop = pnl(stop)
        pnl_tp = pnl(tp) if tp and tp > 0 else None

        # Risco/Retorno
        rr = rr_ratio(entry, stop, tp if tp and tp > 0 else None)

        # ---------- Saída ----------
        st.success("Cálculo concluído com sucesso.")

        cA, cB, cC = st.columns(3)
        cA.metric("Risco por Trade", f"{risk_value:,.2f} {quote}", f"{risk_pct:.2f}% do saldo" if not use_fixed_risk else "fixo")
        cB.metric("Tamanho da Posição (qty)", f"{qty:,.6f}")
        cC.metric("Notional (posição)", f"{notional:,.2f} {quote}")

        cD, cE, cF = st.columns(3)
        if mode == "Futures":
            cD.metric("Margem Requerida", f"{margin_required:,.2f} {quote}", f"alav. x{leverage}")
        else:
            cD.metric("Custo da Compra (Spot)", f"{margin_required:,.2f} {quote}")
        cE.metric("Taxas Estimadas (ida+volta)", f"{est_fees:,.2f} {quote}")
        if be_price:
            cF.metric("Break-even (c/ taxas)", f"{be_price:,.6f}")

        cG, cH, cI = st.columns(3)
        if pnl_stop is not None:
            cG.metric("PnL no Stop (≈)", f"{pnl_stop:,.2f} {quote}")
        if pnl_tp is not None:
            cH.metric("PnL no TP (≈)", f"{pnl_tp:,.2f} {quote}")
        if rr is not None:
            cI.metric("Risco:Retorno", f"{rr:,.2f} : 1")

        if mode == "Futures" and liq_price:
            box = st.container()
            box.markdown("**Estimativa de Preço de Liquidação (simplificada)**")
            box.write(
                f"- Liquidação estimada: **{liq_price:,.6f}**\n"
                f"- Fórmula aproximada (perp. USDT):\n"
                f"    - Long: `E * (1 - 1/lev + MMR)`\n"
                f"    - Short: `E * (1 + 1/lev - MMR)`\n"
                f"- Observação: isso **não** considera funding, taxa de empréstimo, saldo extra na carteira, mudanças de MMR por faixa de notional, nem slippage."
            )

        with st.expander("Detalhes e fórmulas"):
            st.markdown(
                """
    **Como calculamos:**
    - **Risco (valor)** = `saldo * (risco%/100)` ou valor fixo escolhido.
    - **Tamanho da posição (qty)** = `risco / |entrada - stop|`.
    - **Notional** = `entrada * qty`.
    - **Margem (Futures)** = `notional / alavancagem`.
    - **Taxas estimadas** = `notional * (taxa_abertura + taxa_fechamento)`.
    - **Break-even** (com taxas):
      - Long: `entrada + (taxas_totais/qty)`
      - Short: `entrada - (taxas_totais/qty)`
    - **PnL (≈)** = `((preço_saida - entrada) * qty)` para Long,
      ou `((entrada - preço_saida) * qty)` para Short, **menos** taxas.
    - **R:R** = `|tp - entrada| / |entrada - stop|`.

    > Dica: ajuste o **risco%** (ou risco fixo) até que a `qty` seja prática para seu par (lotes mínimos).
                    """
            )


# -------------------------
# Seção: Agente de IA Semântico
if selected_tab == "🤖 Agente IA":
    st.header("🤖 Agente de IA - Consultor Financeiro Semântico")

    user_prompt = st.text_area(
        "Digite sua pergunta:",
        placeholder="Ex: Qual ativo teve maior volatilidade nos últimos 30 dias?"
    )

    if st.button("🔎 Consultar IA"):
        if not user_prompt.strip():
            st.warning("Por favor, digite uma pergunta.")
        else:
            with st.spinner("Processando sua consulta..."):

                # -------------------------
                # Prepara contexto baseado nos dados do app
                # -------------------------
                last_date_prices = df_prices["Date"].max()
                last_date_corr = df_corr["Date"].max()
                last_date_rs = df_rs["Date"].max()

                # Monta um resumo dos dados para fornecer ao modelo
                context = f"""
Resumo dos dados do aplicativo:
- Última data de preços: {last_date_prices.date()}
- Últimos ativos e preços: {df_prices[['Ticker','Price']].tail(5).to_dict(orient='records')}
- Última força relativa disponível: {df_rs[['Pair','RS','RS_Smooth']].tail(5).to_dict(orient='records')}
- Última correlação: {df_corr[['Pair','RollingCorrelation']].tail(5).to_dict(orient='records')}
Forneça respostas baseadas nesses dados sempre que possível.
"""

                try:
                   

                    completion = openai.ChatCompletion.create(
                        model="gpt-4o-mini",
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "Você é um assistente financeiro que pode consultar dados históricos "
                                    "de criptomoedas (preços, força relativa, correlação) e responder perguntas "
                                    "baseadas nestes dados. Utilize os dados fornecidos no contexto quando possível."
                                )
                            },
                            {"role": "system", "content": context},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.2,
                        max_tokens=500
                    )

                    response = completion.choices[0].message["content"]
                except Exception as e:
                    response = f"Erro ao acessar OpenAI: {str(e)}"

                st.success("✅ Consulta realizada!")
                st.write(response)
