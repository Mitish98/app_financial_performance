import subprocess
import sys
import streamlit as st

def update_all_data():
    # Atualizar Correlações
    with st.spinner("Executando script de correlação..."):
        result_corr = subprocess.run([sys.executable, "update_data/correlation.py"])
    if result_corr.returncode == 0:
        st.success("✅ Correlações atualizadas com sucesso.")
    else:
        st.error("❌ Erro ao atualizar correlações.")

    # Atualizar Preços e Força Relativa
    with st.spinner("Executando script de força relativa..."):
        result_rs = subprocess.run([sys.executable, "update_data/rs.py"])
    if result_rs.returncode == 0:
        st.success("✅ Força relativa atualizada com sucesso.")
    else:
        st.error("❌ Erro ao atualizar força relativa.")

    # Limpar cache
    from utils.db import load_corr_data, load_rs_data, load_price_data, get_last_update
    load_corr_data.clear()
    load_rs_data.clear()
    load_price_data.clear()
    get_last_update.clear()

    if result_corr.returncode == 0 and result_rs.returncode == 0:
        st.success("🎉 Todos os dados foram atualizados com sucesso!")
