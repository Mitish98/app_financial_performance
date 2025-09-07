import streamlit as st
import plotly.express as px

def render_relative_strength(df_rs):
    st.header("💪 Força Relativa entre Criptomoedas")
    available_pairs_rs = sorted(df_rs["Pair"].unique())
    default_index = available_pairs_rs.index("BTC-USD/ETH-USD") if "BTC-USD/ETH-USD" in available_pairs_rs else 0
    selected_pair_rs = st.selectbox("Par para análise:", available_pairs_rs, index=default_index)
    available_windows_rs = sorted(df_rs["Window"].unique())
    selected_window_rs = st.selectbox("Janela da média móvel:", available_windows_rs)
    df_selected_rs = df_rs[(df_rs["Pair"] == selected_pair_rs) & (df_rs["Window"] == selected_window_rs)]

    fig_rs = px.line(df_selected_rs, x="Date", y="RS", title=f"Força Relativa - {selected_pair_rs}", labels={"RS": "Força Relativa"})
    fig_rs.add_scatter(x=df_selected_rs["Date"], y=df_selected_rs["RS_Smooth"], mode='lines', name=f"Média {selected_window_rs} dias")
    fig_rs.update_layout(height=400)
    st.plotly_chart(fig_rs, width='stretch')
