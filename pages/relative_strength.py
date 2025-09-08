import streamlit as st
import plotly.express as px

def render_relative_strength(df_rs):
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
    fig_rs.update_layout(height=400)
    st.plotly_chart(fig_rs, use_container_width=True)
    
