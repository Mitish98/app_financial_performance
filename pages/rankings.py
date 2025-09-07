import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def render_rankings(df_prices, selected_period_days):
    st.header("📊 Top Ganhadores e Perdedores")
    last_date_rs = df_prices["Date"].max()
    start_date_rs = last_date_rs - pd.Timedelta(days=selected_period_days)
    df_period = df_prices[(df_prices["Date"] >= start_date_rs) & (df_prices["Date"] <= last_date_rs)]

    if df_period.empty or df_period["Date"].nunique() < 2:
        st.warning("📆 Intervalo insuficiente para análise.")
        return

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

    max_n = max(3, min(20, len(performance_df)))
    default_n = min(5, max_n)
    top_n = st.slider("Número de ativos:", min_value=3, max_value=max_n, value=default_n)

    top_pos = performance_df.head(top_n)
    top_neg = performance_df.tail(top_n).sort_values("Retorno")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"### 🟢 Top {top_n} Ganhadores")
        st.dataframe(top_pos.style.format({
            "Retorno": "{:.2%}", "Volume Total": "{:,.0f}", "RSI": "{:.2f}",
            "MACD": "{:.5f}", "MACD_Signal": "{:.5f}", "SMA_20": "{:.5f}",
            "SMA_50": "{:.5f}", "EMA_20": "{:.5f}", "EMA_50": "{:.5f}",
            "Preço Atual": "U$ {:,.2f}"}), width='stretch')
        fig_rsi = go.Figure()
        for ticker in top_pos["Ticker"].tolist()[:5]:
            df_t = df_period[df_period["Ticker"] == ticker]
            fig_rsi.add_trace(go.Scatter(x=df_t["Date"], y=df_t["RSI"], mode="lines+markers", name=ticker))
        st.plotly_chart(fig_rsi, width='stretch')

    with col2:
        st.markdown(f"### 🔴 Top {top_n} Perdedores")
        st.dataframe(top_neg.style.format({
            "Retorno": "{:.2%}", "Volume Total": "{:,.0f}", "RSI": "{:.2f}",
            "MACD": "{:.5f}", "MACD_Signal": "{:.5f}", "SMA_20": "{:.5f}",
            "SMA_50": "{:.5f}", "EMA_20": "{:.5f}", "EMA_50": "{:.5f}",
            "Preço Atual": "U$ {:,.2f}"}), width='stretch')
