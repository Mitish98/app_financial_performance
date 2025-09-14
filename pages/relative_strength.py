import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

def render_relative_strength(df_rs, df_prices):
    # ----------------- Ranking de Força Relativa -----------------
    st.header("🏆 Ranking de Força Relativa Atual")
    
    # Seleção da janela
    available_windows_rs = sorted(df_rs["Window"].unique())
    selected_window_rs = st.selectbox("Janela da média móvel:", available_windows_rs, index=0)
    
    # Última data disponível
    latest_date = df_rs["Date"].max()
    
    # Filtra dataframe para a última data e janela selecionada
    df_latest = df_rs[(df_rs["Date"] == latest_date) & (df_rs["Window"] == selected_window_rs)]
    
    # Ordena por RS decrescente
    df_latest_sorted = df_latest.sort_values("RS", ascending=False)
    
    # Mostra tabela com par e força relativa
    st.dataframe(df_latest_sorted[["Pair", "RS"]].reset_index(drop=True))
    
    # ----------------- Gráfico de RS do par selecionado -----------------
    st.header("💪 Força Relativa entre Criptomoedas")
    
    # Seleção de par
    available_pairs_rs = sorted(df_rs["Pair"].unique())
    default_index = available_pairs_rs.index("BTC-USD/ETH-USD") if "BTC-USD/ETH-USD" in available_pairs_rs else 0
    selected_pair_rs = st.selectbox("Par para análise:", available_pairs_rs, index=default_index)
    
    # Filtra dataframe do par selecionado
    df_selected_rs = df_rs[(df_rs["Pair"] == selected_pair_rs) & (df_rs["Window"] == selected_window_rs)]

    # Gráfico de RS
    fig_rs = px.line(
        df_selected_rs, x="Date", y="RS",
        title=f"Força Relativa - {selected_pair_rs}",
        labels={"RS": "Força Relativa"}
    )
    fig_rs.add_scatter(
        x=df_selected_rs["Date"],
        y=df_selected_rs["RS_Smooth"],
        mode='lines',
        name=f"Média {selected_window_rs} dias"
    )
    
    # ----------------- d) Bandas de força relativa (RSI-style) -----------------
    # Faixas de sobrecompra/sobrevenda relativa
    fig_rs.add_hrect(y0=0, y1=0.8, fillcolor="red", opacity=0.2, line_width=0)
    fig_rs.add_hrect(y0=1.2, y1=df_selected_rs["RS"].max(), fillcolor="green", opacity=0.2, line_width=0)
    
    fig_rs.update_layout(height=400)
    st.plotly_chart(fig_rs, use_container_width=True)

    # ----------------- c) RS vs Retorno absoluto -----------------
    st.header("📊 Força Relativa vs Retorno Absoluto")
    
    # Criar retorno percentual diário/acumulado dos pares
    # Aqui assumimos que df_prices tem colunas: Date, Ticker, Price
    latest_prices = df_prices[df_prices["Date"] == latest_date]
    
    # Mapear Pair -> base/quote
    pairs_info = df_latest_sorted["Pair"].str.split("/", expand=True)
    df_latest_sorted["Base"] = pairs_info[0]
    df_latest_sorted["Quote"] = pairs_info[1]
    
    # Calcular retorno acumulado do Base no período de análise
    retorno_acumulado = {}
    for ticker in df_latest_sorted["Base"]:
        df_t = df_prices[df_prices["Ticker"] == ticker].sort_values("Date")
        ret = (df_t["Price"].iloc[-1] / df_t["Price"].iloc[0] - 1) * 100
        retorno_acumulado[ticker] = ret
    df_latest_sorted["Return"] = df_latest_sorted["Base"].map(retorno_acumulado)
    
    fig_scatter = go.Figure()
    fig_scatter.add_trace(go.Scatter(
        x=df_latest_sorted["RS"],
        y=df_latest_sorted["Return"],
        # Remover a linha abaixo para não mostrar os nomes
        # text=df_latest_sorted["Pair"],
        mode="markers",  # somente pontos
        marker=dict(size=12, color=df_latest_sorted["RS"], colorscale="Viridis", showscale=True)
    ))
    fig_scatter.update_layout(
        title="Força Relativa vs Retorno Absoluto",
        xaxis_title="Força Relativa",
        yaxis_title="Retorno (%)"
    )
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    
