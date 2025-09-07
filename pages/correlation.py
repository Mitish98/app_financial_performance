import streamlit as st

def render_correlation(df_corr):
    st.header("📈 Análise de Correlação entre Ativos")

    def get_unique_assets(df):
        assets = set()
        for pair in df["Pair"].unique():
            assets.update(pair.split("/"))
        return sorted(list(assets))

    assets = get_unique_assets(df_corr)
    default_assets = [a for a in ["BTC-USD", "ETH-USD"] if a in assets]
    selected_assets = st.multiselect("🔍 Selecionar ativos:", assets, default=default_assets)
    df_filtered_corr = df_corr[df_corr["Pair"].apply(lambda x: any(a in x for a in selected_assets))] if selected_assets else df_corr.copy()
    last_date_corr = df_filtered_corr["Date"].max()
    df_latest_corr = df_filtered_corr[df_filtered_corr["Date"] == last_date_corr].dropna(subset=["RollingCorrelation"])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🔝 Top Correlações Positivas")
        st.dataframe(df_latest_corr.sort_values("RollingCorrelation", ascending=False).head(10)[["Pair","RollingCorrelation"]])
    with col2:
        st.markdown("#### 🔻 Top Correlações Negativas")
        st.dataframe(df_latest_corr.sort_values("RollingCorrelation", ascending=True).head(10)[["Pair","RollingCorrelation"]])
