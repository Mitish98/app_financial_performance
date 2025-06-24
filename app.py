import streamlit as st
import subprocess
import sys

st.set_page_config(page_title="Painel Financeiro", layout="wide")

st.title("📊 Painel de Análises Financeiras")

st.markdown("""
Este app contém duas análises principais:
1. **Correlação Móvel entre Criptoativos**
2. **Força Relativa com Indicadores Técnicos**

Você pode navegar usando o menu lateral.

---  
🔄 **Atualizar os bancos de dados**
""")

if st.button("🔁 Atualizar Correlações"):
    with st.spinner("Executando script de correlação..."):
        result = subprocess.run([sys.executable, "update_data/correlation_main.py"])
    if result.returncode == 0:
        st.success("✅ Correlações atualizadas com sucesso.")
    else:
        st.error("❌ Erro ao atualizar correlações.")

if st.button("🔁 Atualizar Força Relativa"):
    with st.spinner("Executando script de força relativa..."):
        result = subprocess.run([sys.executable, "update_data/rs_main.py"])
    if result.returncode == 0:
        st.success("✅ Força relativa atualizada com sucesso.")
    else:
        st.error("❌ Erro ao atualizar força relativa.")
