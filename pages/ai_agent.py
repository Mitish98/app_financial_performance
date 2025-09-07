import streamlit as st
import openai

def render_ai_agent(df_prices, df_rs, df_corr):
    st.header("🤖 Agente de IA - Consultor Financeiro Semântico")
    user_prompt = st.text_area("Digite sua pergunta:", placeholder="Ex: Qual ativo teve maior volatilidade nos últimos 30 dias?")
    if st.button("🔎 Consultar IA"):
        if not user_prompt.strip():
            st.warning("Por favor, digite uma pergunta.")
        else:
            with st.spinner("Processando sua consulta..."):
                last_date_prices = df_prices["Date"].max()
                last_date_corr = df_corr["Date"].max()
                last_date_rs = df_rs["Date"].max()
                context = f"""
Resumo dos dados do aplicativo:
- Última data de preços: {last_date_prices.date()}
- Últimos ativos e preços: {df_prices[['Ticker','Price']].tail(5).to_dict(orient='records')}
- Última força relativa disponível: {df_rs[['Pair','RS','RS_Smooth']].tail(5).to_dict(orient='records')}
- Última correlação: {df_corr[['Pair','RollingCorrelation']].tail(5).to_dict(orient='records')}
Forneça respostas baseadas nesses dados sempre que possível.
"""
                try:
                    completion = openai.ChatCompletion.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "Você é um assistente financeiro que pode consultar dados históricos de criptomoedas."},
                            {"role": "system", "content": context},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.2,
                        max_tokens=500
                    )
                    response = completion.choices[0].message["content"]
                except Exception as e:
                    response = f"Erro ao acessar OpenAI: {str(e)}"
                st.success("✅ Consulta realizada!")
                st.write(response)
