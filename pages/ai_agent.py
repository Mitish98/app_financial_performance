import streamlit as st
import pandas as pd
from openai import OpenAI   # ✅ nova forma, não precisa mais do `import openai`

def render_ai_agent(df_prices, df_rs, df_corr, selected_period_days):
    """
    Renderiza a interface do agente de IA para análise e previsões
    """
    
    # Verificar se a chave da API está configurada
    if "openai_api_key" not in st.secrets:
        st.error("⚠️ Chave da API OpenAI não configurada!")
        st.info("💡 Configure sua chave da API no arquivo .secrets.toml")
        st.code("""
# Adicione no arquivo .secrets.toml:
[secrets]
openai_api_key = "sua_chave_da_openai_aqui"
        """)
        return
    
    user_prompt = st.text_area(
        "Digite sua pergunta sobre os dados financeiros:", 
        placeholder="Ex: Qual ativo teve maior volatilidade nos últimos 30 dias?",
        height=100
    )
        
    # Processar consulta
    if st.button("🔎 Consultar IA", type="primary") or user_prompt:
        if not user_prompt.strip():
            st.warning("⚠️ Por favor, digite uma pergunta ou selecione uma consulta rápida.")
        else:
            with st.spinner("🤖 Processando sua consulta com IA..."):
                try:
                    # Preparar contexto dos dados
                    context = prepare_data_context(df_prices, df_rs, df_corr, selected_period_days)
                    
                    # ✅ Nova forma de usar o cliente OpenAI
                    client = OpenAI(api_key=st.secrets["openai_api_key"])
                    completion = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {
                                "role": "system", 
                                "content": """Você é um analista financeiro especializado em criptomoedas. 
                                Analise os dados fornecidos e forneça insights claros e acionáveis. 
                                Use métricas técnicas quando relevante e seja específico com números e percentuais."""
                            },
                            {"role": "system", "content": context},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.3,
                        max_tokens=800
                    )
                    response = completion.choices[0].message.content
                    
                    # Exibir resultado
                    st.success("✅ Análise concluída!")
                    st.markdown("### 📋 Resposta da IA")
                    st.markdown(response)
                    
                except Exception as e:
                    st.error(f"❌ Erro ao acessar OpenAI: {str(e)}")
                    st.info("💡 Verifique se sua chave da API está correta e se você tem créditos disponíveis.")


def prepare_data_context(df_prices, df_rs, df_corr, selected_period_days):
    """
    Prepara o contexto dos dados para a IA
    """
    # Filtrar dados pelo período selecionado
    cutoff_date = df_prices['Date'].max() - pd.Timedelta(days=selected_period_days)
    recent_prices = df_prices[df_prices['Date'] >= cutoff_date]
    recent_rs = df_rs[df_rs['Date'] >= cutoff_date]
    recent_corr = df_corr[df_corr['Date'] >= cutoff_date]
    
    # Calcular métricas básicas
    price_stats = recent_prices.groupby('Ticker')['Price'].agg(['last', 'min', 'max', 'std']).round(2)
    price_changes = recent_prices.groupby('Ticker')['Price'].apply(
        lambda x: ((x.iloc[-1] - x.iloc[0]) / x.iloc[0] * 100) if len(x) > 1 else 0
    ).round(2)
    
    # Preparar contexto
    context = f"""
DADOS FINANCEIROS DISPONÍVEIS (Período: {selected_period_days} dias):

PREÇOS E PERFORMANCE:
- Período analisado: {selected_period_days} dias
- Última data: {df_prices['Date'].max().strftime('%d/%m/%Y')}
- Total de ativos: {len(df_prices['Ticker'].unique())}

ESTATÍSTICAS DE PREÇOS (últimos {selected_period_days} dias):
{price_stats.to_string()}

VARIAÇÕES PERCENTUAIS:
{price_changes.to_string()}

FORÇA RELATIVA (últimos dados):
{df_rs[['Pair', 'RS', 'RS_Smooth']].tail(10).to_string()}

CORRELAÇÕES (últimos dados):
{df_corr[['Pair', 'RollingCorrelation']].tail(10).to_string()}

INSTRUÇÕES:
- Use estes dados para responder perguntas sobre performance, volatilidade, correlações e tendências
- Forneça números específicos e percentuais quando relevante
- Identifique padrões e oportunidades de investimento
- Seja claro e objetivo nas recomendações
"""
    
    return context
