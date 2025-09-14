import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

def render_rankings(df_prices, selected_period_days):
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
    indicators_avg = df_period.groupby("Ticker")[["RSI", "SMA_20","SMA_50"]].mean()
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

    # <<< Aqui: reordenar colunas para trazer 'Preço Atual' para mais perto do início
    cols = performance_df.columns.tolist()
    if "Preço Atual" in cols:
        cols.insert(1, cols.pop(cols.index("Preço Atual")))  # move para a posição 1
    performance_df = performance_df[cols]

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
                "Preço Atual": "U$ {:,.2f}", "Retorno": "{:.2%}", "Volume Total": "{:,.0f}", "RSI": "{:.2f}",
                "SMA_20": "{:.5f}", "SMA_50": "{:.5f}" , "MarketCap": "U$ {:,.0f}"
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
                "SMA_20": "{:.5f}", "SMA_50": "{:.5f}", "Preço Atual": "U$ {:,.2f}", "MarketCap": "U$ {:,.0f}"
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

        
        # =============================
    # Sessão de análise aprofundada
    # =============================
    st.markdown("---")  # separador visual
    st.header("🔎 Análise Comparativa Aprofundada")

    # Seleção de ativos com base nos que apareceram no período filtrado
    tickers_disponiveis = sorted(df_period["Ticker"].unique())
    ativos_selecionados = st.multiselect(
        "Selecione os ativos para comparar:",
        options=tickers_disponiveis,
        default=tickers_disponiveis[:3] if len(tickers_disponiveis) >= 3 else tickers_disponiveis
    )

    if ativos_selecionados:
        df_sel = df_period[df_period["Ticker"].isin(ativos_selecionados)]

        # -----------------------------
        # Gráfico de Retorno acumulado
        # -----------------------------
        fig_ret = go.Figure()
        for ticker in ativos_selecionados:
            df_t = df_sel[df_sel["Ticker"] == ticker].sort_values("Date")
            ret_acumulado = (df_t["Price"] / df_t["Price"].iloc[0] - 1) * 100
            fig_ret.add_trace(go.Scatter(
                x=df_t["Date"], y=ret_acumulado, mode="lines+markers", name=ticker
            ))
        fig_ret.update_layout(title="📈 Retorno Acumulado (%)", yaxis_title="Retorno (%)")
        st.plotly_chart(fig_ret, use_container_width=True, key="retorno_selecao")

        # -----------------------------
        # Gráfico de Volume
        # -----------------------------
        fig_vol = go.Figure()
        for ticker in ativos_selecionados:
            df_t = df_sel[df_sel["Ticker"] == ticker].sort_values("Date")
            fig_vol.add_trace(go.Bar(x=df_t["Date"], y=df_t["Volume"], name=ticker))
        fig_vol.update_layout(barmode="group", title="📊 Volume negociado")
        st.plotly_chart(fig_vol, use_container_width=True, key="volume_selecao")

        # -----------------------------
        # Gráfico de RSI
        # -----------------------------
        fig_rsi = go.Figure()
        for ticker in ativos_selecionados:
            df_t = df_sel[df_sel["Ticker"] == ticker].sort_values("Date")
            fig_rsi.add_trace(go.Scatter(
                x=df_t["Date"], y=df_t["RSI"], mode="lines+markers", name=ticker
            ))
        fig_rsi.update_layout(title="📉 RSI dos Ativos Selecionados", yaxis_title="RSI")
        st.plotly_chart(fig_rsi, use_container_width=True, key="rsi_selecao")


        # Garantir que retornos estão calculados
        df_ret = (
            df_sel.groupby("Ticker")[["Date", "Price"]]
            .apply(lambda x: x.set_index("Date")["Price"].pct_change())
            .unstack(level=0)
        ).dropna()

        # Se apenas 1 ativo for selecionado → garantir DataFrame
        if isinstance(df_ret, pd.Series):
            df_ret = df_ret.to_frame()

        # Tratar MultiIndex e garantir consistência de nomes
        if isinstance(df_ret.columns, pd.MultiIndex):
            df_ret.columns = df_ret.columns.droplevel(0)

        # Converter nomes das colunas para string
        df_ret.columns = [str(c) for c in df_ret.columns]

        # -----------------------------

    # Calcular retornos de forma robusta
    df_ret = (
        df_sel.pivot(index="Date", columns="Ticker", values="Price")
        .pct_change()
        .dropna()
    )

    # Garantir que as colunas sejam strings
    df_ret.columns = df_ret.columns.astype(str)

    # Filtrar apenas os ativos selecionados que realmente existem no df_ret
    colunas_validas = [a for a in ativos_selecionados if a in df_ret.columns]

    if not colunas_validas:
        st.warning("⚠️ Nenhum dos ativos selecionados possui dados suficientes para o gráfico de risco x retorno.")
    else:
        retornos = df_ret[colunas_validas].mean() * 100
        vols = df_ret[colunas_validas].std() * 100

        # -----------------------------
        # Tamanho dos círculos proporcional ao retorno absoluto
        # -----------------------------
        # Escalar para uma faixa visual agradável (entre 10 e 50)
        tamanho = (retornos.values - retornos.min()) / (retornos.max() - retornos.min()) * 40 + 10

        fig_risco = go.Figure()
        fig_risco.add_trace(go.Scatter(
            x=vols.values, y=retornos.values, mode="markers+text",
            text=retornos.index, textposition="top center",
            marker=dict(
                size=tamanho,
                color="blue",
                sizemode="area",  # tamanho proporcional à área
                sizeref=2.*max(tamanho)/(50.**2)
            )
        ))
        fig_risco.update_layout(
            title="⚖️ Risco (Volatilidade) x Retorno Médio",
            xaxis_title="Volatilidade (%)",
            yaxis_title="Retorno Médio (%)"
        )
        st.plotly_chart(fig_risco, use_container_width=True, key="risco_retorno")


        # -----------------------------
    # b) Simulação de Carteira
    # -----------------------------
    st.subheader("💼 Simulação de Carteira")

    # Calcular retornos de forma robusta
    df_ret = (
        df_sel.pivot(index="Date", columns="Ticker", values="Price")
        .pct_change()
        .dropna()
    )

    # Garantir que as colunas sejam strings
    df_ret.columns = df_ret.columns.astype(str)

    # Filtrar apenas os ativos selecionados que realmente existem no df_ret
    colunas_validas = [a for a in ativos_selecionados if a in df_ret.columns]

    if not colunas_validas:
        st.warning("⚠️ Nenhum dos ativos selecionados possui dados suficientes para a simulação.")
    else:
        # Slider de pesos
        pesos = {}
        total_ativos = len(colunas_validas)
        for ativo in colunas_validas:
            pesos[ativo] = st.slider(
                f"Peso {ativo} (%)",
                0, 100, int(100/total_ativos),
                key=f"peso_{ativo}"
            ) / 100

        # Normalizar pesos
        peso_total = sum(pesos.values())
        if peso_total > 0:
            pesos = {k: v/peso_total for k, v in pesos.items()}

            # Retorno da carteira
            ret_carteira = (df_ret[colunas_validas] * pd.Series(pesos)).sum(axis=1)
            evol_carteira = (1 + ret_carteira).cumprod()

            # Gráfico da evolução da carteira
            fig_carteira = go.Figure()
            fig_carteira.add_trace(go.Scatter(
                x=evol_carteira.index, y=evol_carteira,
                mode="lines", name="Carteira"
            ))
            fig_carteira.update_layout(
                title="",
                yaxis_title="Crescimento acumulado"
            )
            st.plotly_chart(fig_carteira, use_container_width=True, key="carteira_simulada")

            # Mostrar métricas da carteira
            st.markdown("### 📊 Métricas da Carteira")
            st.write(f"**Retorno médio diário:** {ret_carteira.mean()*100:.2f}%")
            st.write(f"**Volatilidade diária:** {ret_carteira.std()*100:.2f}%")
            st.write(f"**Retorno acumulado:** {(evol_carteira.iloc[-1]-1)*100:.2f}%")
        else:
            st.warning("⚠️ Ajuste os pesos para que somem mais que zero.")
