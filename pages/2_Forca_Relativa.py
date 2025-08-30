import streamlit as st
import asyncio
import pandas as pd
import requests
from ta.momentum import RSIIndicator
from dotenv import load_dotenv
import os
import yfinance as yf

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Importando credenciais Telegram
telegram_bot_token = os.getenv("telegram_bot_token")
telegram_chat_id = os.getenv("telegram_chat_id")

# Funções auxiliares
def calculate_bollinger_bands(df, num_periods=21, std_dev_factor=2):
    df['SMA'] = df['Close'].rolling(window=num_periods).mean()
    df['std_dev'] = df['Close'].rolling(window=num_periods).std()
    df['upper_band'] = df['SMA'] + (std_dev_factor * df['std_dev'])
    df['lower_band'] = df['SMA'] - (std_dev_factor * df['std_dev'])
    return df

def calculate_stochastic_oscillator(df, k_period=14, d_period=3):
    df['L14'] = df['Low'].rolling(window=k_period).min()
    df['H14'] = df['High'].rolling(window=k_period).max()
    df['%K'] = ((df['Close'] - df['L14']) / (df['H14'] - df['L14'])) * 100
    df['%D'] = df['%K'].rolling(window=d_period).mean()
    return df

async def fetch_ticker_and_candles(symbol, timeframe):
    """Pega dados históricos do Yahoo Finance e o último preço."""
    yf_symbol = symbol.replace("USDT", "-USD")  # Ex: BTCUSDT -> BTC-USD
    interval_mapping = {
        "1m": "1m", "5m": "5m", "15m": "15m",
        "1h": "60m", "4h": "4h", "1d": "1d"
    }
    interval = interval_mapping.get(timeframe, "1m")
    period = "7d" if interval in ["1m", "5m", "15m", "60m"] else "60d"

    try:
        df = yf.download(yf_symbol, interval=interval, period=period, progress=False)
        if df.empty:
            raise ValueError("Nenhum dado retornado do Yahoo Finance")
        
        current_price = df['Close'].iloc[-1]
        df = df.rename(columns={"Open": "Open", "High": "High", "Low": "Low", "Close": "Close", "Volume": "Volume"})
        return current_price, df
    except Exception as e:
        st.error(f"Erro ao obter dados de {symbol} no timeframe {timeframe}: {e}")
        return None, None

async def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
    payload = {"chat_id": telegram_chat_id, "text": message}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao enviar mensagem para o Telegram: {e}")

# Controle de notificações para evitar repetições
last_notifications = {}

async def notify_conditions(symbol, timeframes, notify_telegram, signal_choice):
    while True:
        for timeframe in timeframes:
            current_price, df = await fetch_ticker_and_candles(symbol, timeframe)
            if df is None:
                await asyncio.sleep(5)
                continue

            # Indicadores
            df = calculate_bollinger_bands(df)
            df = calculate_stochastic_oscillator(df)
            rsi_indicator = RSIIndicator(df['Close'], window=14)
            df['rsi'] = rsi_indicator.rsi()

            upper_band = df['upper_band'].iloc[-1]
            lower_band = df['lower_band'].iloc[-1]
            stochastic_k = df['%K'].iloc[-1]
            stochastic_d = df['%D'].iloc[-1]
            rsi = df['rsi'].iloc[-1]
            volume_ma = df['Volume'].rolling(window=21).mean().iloc[-1]  # Média móvel de volume
            high_volume = df['Volume'].iloc[-1] > 3 * volume_ma  # Novo critério: volume > 3x média

            current_signal = None
            if (
                current_price < lower_band and 
                stochastic_k < 20 and 
                stochastic_d < 20 and 
                high_volume and 
                rsi < 30 and
                signal_choice in ["Compra", "Ambos"]
            ):
                current_signal = "COMPRA"
            elif (
                current_price > upper_band and 
                stochastic_k > 80 and 
                stochastic_d > 80 and 
                high_volume and 
                rsi > 70 and
                signal_choice in ["Venda", "Ambos"]
            ):
                current_signal = "VENDA"

            key = f"{symbol}_{timeframe}"
            last_signal = last_notifications.get(key)

            if current_signal and current_signal != last_signal:
                message = (
                    f"Sinal de {current_signal} para {symbol} no timeframe {timeframe}:\n"
                    f"Preço atual: {current_price}\n"
                )
                st.info(message)
                if notify_telegram:
                    await send_telegram_message(message)
                last_notifications[key] = current_signal

            await asyncio.sleep(60)

# Configuração do Streamlit
st.title("Robô de Notificação para Criptomoedas (Yahoo Finance)")
st.write("O sistema utiliza uma combinação de indicadores técnicos para gerar sinais de compra e venda.")

# Entrada do usuário
all_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "DOTUSDT", "DOGEUSDT", "FTMUSDT", "ASTRUSDT", "XRPUSDT", "SOLUSDT", 
               "LTCUSDT", "PENDLEUSDT", "AAVEUSDT", "ORDIUSDT", "UNIUSDT", "LINKUSDT", 
               "ENSUSDT", "MOVRUSDT", "ARBUSDT", "TRBUSDT", "MANTAUSDT", "AVAXUSDT", "ADAUSDT", "GALAUSDT","LDOUSDT"]

select_all = st.sidebar.checkbox("Selecionar todos os pares")
symbols = st.sidebar.multiselect("Selecione os pares de moedas", all_symbols, default=all_symbols if select_all else [])
timeframes = st.sidebar.multiselect("Selecione o(s) timeframe(s)", ["1m", "5m", "15m", "1h", "4h", "1d"])
notify_telegram = st.sidebar.checkbox("Enviar notificações no Telegram", value=False)
signal_choice = st.sidebar.radio("Selecione os sinais desejados", ["Compra", "Venda", "Ambos"], index=2)

if st.sidebar.button("Iniciar Monitoramento"):
    if not symbols:
        st.error("Por favor, selecione pelo menos um par de moedas.")
    elif not timeframes:
        st.error("Por favor, selecione pelo menos um timeframe.")
    else:
        if notify_telegram:
            st.success("Monitoramento iniciado com notificações no Telegram! Acompanhe os alertas abaixo.")
        else:
            st.warning("Monitoramento iniciado sem notificações no Telegram. Apenas os alertas locais serão exibidos.")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = [notify_conditions(symbol, timeframes, notify_telegram, signal_choice) for symbol in symbols]
        loop.run_until_complete(asyncio.gather(*tasks))
