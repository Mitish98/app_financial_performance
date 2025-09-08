import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def render_correlation(df_corr):
    st.header("📈 Análise de Correlação entre Ativos")

    # ------------------- Seletor numérico da janela -------------------
    window_days = st.number_input(
        "🗓️ Digite a janela da correlação móvel (dias):",
        min_value=1, max_value=180, value=30, step=1
    )

    # Filtra a tabela apenas pela janela escolhida
    if "Window" not in df_corr.columns:
        df_corr["Window"] = window_days
    df_table = df_corr[df_corr["Window"] == window_days]

    last_date_corr = df_table["Date"].max()
    df_latest_corr = df_table[df_table["Date"] == last_date_corr].dropna(subset=["RollingCorrelation"])

    # ------------------- Tabela de Top Correlações -------------------
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🔝 Top Correlações Positivas")
        st.dataframe(
            df_latest_corr.sort_values("RollingCorrelation", ascending=False)
            .head(10)[["Pair", "RollingCorrelation"]]
        )
    with col2:
        st.markdown("#### 🔻 Top Correlações Negativas")
        st.dataframe(
            df_latest_corr.sort_values("RollingCorrelation", ascending=True)
            .head(10)[["Pair", "RollingCorrelation"]]
        )

    # ------------------- Gráfico de Correlação Móvel -------------------
    st.markdown("### 📊 Gráfico de Correlação Móvel")

    # Filtro de ativos (apenas para o gráfico)
    assets = sorted(set(a for pair in df_corr["Pair"].unique() for a in pair.split("/")))
    default_assets = [a for a in ["BTC-USD", "ETH-USD"] if a in assets]
    selected_assets = st.multiselect(
        "🔍 Selecionar ativos para o gráfico:",
        assets,
        default=default_assets
    )

    df_filtered = df_corr.copy()
    if selected_assets:
        df_filtered = df_filtered[
            df_filtered["Pair"].apply(lambda x: all(a in x for a in selected_assets))
        ]

    min_date = df_filtered["Date"].min()
    max_date = df_filtered["Date"].max()
    date_range = st.date_input("📅 Intervalo de datas:", [min_date, max_date])

    df_filtered = df_filtered[
        (df_filtered["Date"] >= pd.to_datetime(date_range[0])) &
        (df_filtered["Date"] <= pd.to_datetime(date_range[1]))
    ]

    # Seleção de um par específico para o gráfico
    available_pairs = df_filtered["Pair"].unique()
    if len(available_pairs) == 0:
        st.info("Não há pares disponíveis nesse filtro.")
        return

    selected_pair = st.selectbox("Escolha um par para o gráfico:", available_pairs)
    df_pair = df_filtered[df_filtered["Pair"] == selected_pair].dropna(subset=["RollingCorrelation"])

    if not df_pair.empty:
        # Ordenar e resetar índice para evitar problemas visuais
        df_pair = df_pair.sort_values("Date").reset_index(drop=True)

        # Criar gráfico limpo, apenas linha, sem área
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df_pair["Date"],
            y=df_pair["RollingCorrelation"],
            mode="lines",
            name=selected_pair,
            line=dict(color="blue", width=1),  # linha fina
            fill=None  # garante que não preenche como área
        ))

        fig.update_layout(
            title=f"Correlação Móvel - {selected_pair}",
            xaxis_title="Data",
            yaxis_title="Correlação",
            yaxis=dict(range=[-1, 1]),
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Não há dados suficientes para o par selecionado nesse intervalo de datas.")
