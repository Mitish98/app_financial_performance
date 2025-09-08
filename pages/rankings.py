import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

def render_rankings(df_prices, selected_period_days):
    st.header("📊 Top Ganhadores e Perdedores")

    # -----------------------------
    # Garantir que Date é datetime
    # -----------------------------
    df_prices["Date"] = pd.to_datetime(df_prices["Date"])

    # -----------------------------
    # Última data válida (preço e MarketCap)
    # -----------------------------
    last_date_rs = df_prices.dropna(subset=["Price", "MarketCap"])["Date"].max()
    start_date_rs = last_date_rs - pd.Timedelta(days=selected_period_days)

    # Filtrar período selecionado
    df_period = df_prices[(df_prices["Date"] >= start_date_rs) & (df_prices["Date"] <= last_date_rs)]
    if df_period.empty or df_period["Date"].nunique() < 2:
        st.warning("📆 Intervalo insuficiente para análise.")
        return

    # -----------------------------
    # Performance
    # -----------------------------
    start_prices = df_period[df_period["Date"] == df_period["Date"].min()].set_index("Ticker")["Price"]
    end_prices = df_period[df_period["Date"] == df_period["Date"].max()].set_index("Ticker")["Price"]
    performance = ((end_prices / start_prices) - 1).sort_values(ascending=False)

    # -----------------------------
    # Outros indicadores
    # -----------------------------
    volume_total = df_period.groupby("Ticker")["Volume"].sum().rename("Volume Total")
    indicators_avg = df_period.groupby("Ticker")[["RSI","MACD","MACD_Signal","SMA_20","SMA_50","EMA_20","EMA_50"]].mean()
    current_prices = df_period[df_period["Date"] == last_date_rs].set_index("Ticker")["Price"].rename("Preço Atual")
    current_marketcap = df_period[df_period["Date"] == last_date_rs].set_index("Ticker")["MarketCap"].rename("MarketCap")

    # -----------------------------
    # Montar DataFrame final
    # -----------------------------
    performance_df = (
        performance.to_frame("Retorno")
        .merge(volume_total, left_index=True, right_index=True)
        .merge(indicators_avg, left_index=True, right_index=True)
        .merge(current_prices, left_index=True, right_index=True)
        .merge(current_marketcap, left_index=True, right_index=True)
        .reset_index()
    )

    # -----------------------------
    # Slider de Top N
    # -----------------------------
    max_n = max(3, min(20, len(performance_df)))
    default_n = min(5, max_n)
    top_n = st.slider("Número de ativos:", min_value=3, max_value=max_n, value=default_n)

    top_pos = performance_df.head(top_n)
    top_neg = performance_df.tail(top_n).sort_values("Retorno")

    col1, col2 = st.columns(2)

    # =============================
    # Top Ganhadores
    # =============================
    with col1:
        st.markdown(f"### 🟢 Top {top_n} Ganhadores")
        st.dataframe(
            top_pos.style.format({
                "Retorno": "{:.2%}", "Volume Total": "{:,.0f}", "RSI": "{:.2f}",
                "MACD": "{:.5f}", "MACD_Signal": "{:.5f}", "SMA_20": "{:.5f}",
                "SMA_50": "{:.5f}", "EMA_20": "{:.5f}", "EMA_50": "{:.5f}",
                "Preço Atual": "U$ {:,.2f}", "MarketCap": "U$ {:,.0f}"
            }),
            use_container_width=True,
            key=f"df_ganhadores_{top_n}"
        )

        # Gráfico Volume Total com rótulo de Retorno %
        fig_vol_ganhadores = go.Figure()
        fig_vol_ganhadores.add_trace(
            go.Bar(
                x=top_pos["Ticker"],
                y=top_pos["Volume Total"],
                marker_color="green",
                text=[f"{r*100:.2f}%" for r in top_pos["Retorno"]],
                textposition="auto"
            )
        )
        fig_vol_ganhadores.update_layout(title="📊 Volume Total - Top Ganhadores", yaxis_title="Volume")
        st.plotly_chart(fig_vol_ganhadores, use_container_width=True, key=f"vol_ganhadores_{top_n}")

        # MarketCap em Pizza
        fig_mc_ganhadores = go.Figure(go.Pie(labels=top_pos["Ticker"], values=top_pos["MarketCap"],
                                             hoverinfo="label+percent+value", textinfo="label+percent"))
        fig_mc_ganhadores.update_layout(title="💰 MarketCap - Top Ganhadores")
        st.plotly_chart(fig_mc_ganhadores, use_container_width=True, key=f"mc_ganhadores_{top_n}")

         # Gráfico RSI
        fig_rsi_ganhadores = go.Figure()
        for ticker in top_pos["Ticker"].tolist()[:3]:
            df_t = df_period[df_period["Ticker"] == ticker]
            fig_rsi_ganhadores.add_trace(go.Scatter(x=df_t["Date"], y=df_t["RSI"], mode="lines+markers", name=ticker))
        fig_rsi_ganhadores.update_layout(title="📈 RSI - Top 3 Ganhadores", yaxis_title="RSI")
        st.plotly_chart(fig_rsi_ganhadores, use_container_width=True, key=f"rsi_ganhadores_{top_n}")


    # =============================
    # Top Perdedores
    # =============================
    with col2:
        st.markdown(f"### 🔴 Top {top_n} Perdedores")
        st.dataframe(
            top_neg.style.format({
                "Retorno": "{:.2%}", "Volume Total": "{:,.0f}", "RSI": "{:.2f}",
                "MACD": "{:.5f}", "MACD_Signal": "{:.5f}", "SMA_20": "{:.5f}",
                "SMA_50": "{:.5f}", "EMA_20": "{:.5f}", "EMA_50": "{:.5f}",
                "Preço Atual": "U$ {:,.2f}", "MarketCap": "U$ {:,.0f}"
            }),
            use_container_width=True,
            key=f"df_perdedores_{top_n}"
        )

        # Gráfico Volume Total com rótulo de Retorno %
        fig_vol_perdedores = go.Figure()
        fig_vol_perdedores.add_trace(
            go.Bar(
                x=top_neg["Ticker"],
                y=top_neg["Volume Total"],
                marker_color="red",
                text=[f"{r*100:.2f}%" for r in top_neg["Retorno"]],
                textposition="auto"
            )
        )
        fig_vol_perdedores.update_layout(title="📊 Volume Total - Top Perdedores", yaxis_title="Volume")
        st.plotly_chart(fig_vol_perdedores, use_container_width=True, key=f"vol_perdedores_{top_n}")

        # MarketCap em Pizza
        fig_mc_perdedores = go.Figure(go.Pie(labels=top_neg["Ticker"], values=top_neg["MarketCap"],
                                             hoverinfo="label+percent+value", textinfo="label+percent"))
        fig_mc_perdedores.update_layout(title="💰 MarketCap - Top Perdedores")
        st.plotly_chart(fig_mc_perdedores, use_container_width=True, key=f"mc_perdedores_{top_n}")

        # Gráfico RSI
        fig_rsi_perdedores = go.Figure()
        for ticker in top_neg["Ticker"].tolist()[:3]:
            df_t = df_period[df_period["Ticker"] == ticker]
            fig_rsi_perdedores.add_trace(go.Scatter(x=df_t["Date"], y=df_t["RSI"], mode="lines+markers", name=ticker))
        fig_rsi_perdedores.update_layout(title="📉 RSI - Top 3 Perdedores", yaxis_title="RSI")
        st.plotly_chart(fig_rsi_perdedores, use_container_width=True, key=f"rsi_perdedores_{top_n}")
