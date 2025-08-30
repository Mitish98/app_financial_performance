import asyncio
import pandas as pd
import yfinance as yf
import streamlit as st
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

st.set_page_config(page_title="Força Relativa", layout="wide")

# ---------------------------
# Funções de indicadores
# ---------------------------
def calculate_bollinger_bands(df, window=20, n_std=2):
    if df.empty or len(df) < window:
        df['upper_band'] = pd.Series(dtype=float)
        df['lower_band'] = pd.Series(dtype=float)
        return df
    indicator_bb = BollingerBands(close=df['Close'], window=window, window_dev=n_std)
    df['upper_band'] = indicator_bb.bollinger_hband()
    df['lower_band'] = indicator_bb.bollinger_lband()
    return df

def calculate_stochastic_oscillator(df, k_period=14, d_period=3):
    if df.empty or len(df) < k_period:
        df['%K'] = pd.Series(dtype=float)
        df['%D'] = pd.Series(dtype=float)
        return df

    df['L14'] = df['Low'].rolling(window=k_period).min()
    df['H14'] = df['High'].rolling(window=k_period).max()
    df['%K'] = ((df['Close'] - df['L14']) / (df['H14'] - df['L14'])).astype(float)
    df['%D'] = df['%K'].rolling(window=d_period).mean()
    return df

# ---------------------------
# Função para buscar dados
# ---------------------------
async def fetch_ticker_and_candles(symbol, timeframe, period="7d"):
    yf_symbol = symbol.replace("USDT", "-USD")
    try:
        df = yf.download(yf_symbol, interval=timeframe, period=period, progress=False)
        if df.empty:
            st.warning(f"No data for {yf_symbol}. Skipping...")
            return None, None
        current_price = df['Close'].iloc[-1]
        return current_price, df
    except Exception as e:
        st.warning(f"Error fetching {yf_symbol}: {e}")
        return None, None

# ---------------------------
# Função principal de sinais
# ---------------------------
async def notify_conditions(symbol, timeframe):
    current_price, df = await fetch_ticker_and_candles(symbol, timeframe)
    if df is None or df.empty:
        return

    # Calcular indicadores
    df = calculate_bollinger_bands(df)
    df = calculate_stochastic_oscillator(df)
    rsi_indicator = RSIIndicator(df['Close'], window=14)
    df['rsi'] = rsi_indicator.rsi()

    # Últimos valores
    upper_band = df['upper_band'].iloc[-1]
    lower_band = df['lower_band'].iloc[-1]
    stochastic_k = df['%K'].iloc[-1] if not df['%K'].empty else None
    stochastic_d = df['%D'].iloc[-1] if not df['%D'].empty else None
    rsi = df['rsi'].iloc[-1] if not df['rsi'].empty else None

    # Determinar sinal (exemplo simples)
    signal = None
    if stochastic_k is not None and stochastic_d is not None:
        if stochastic_k > stochastic_d and current_price < lower_band:
            signal = "Compra"
        elif stochastic_k < stochastic_d and current_price > upper_band:
            signal = "Venda"

    # Atualizar Streamlit
    chart_placeholder = st.empty()
    with chart_placeholder.container():
        st.write(f"**{symbol} ({timeframe})** - Preço: {current_price:.2f}")
        st.write(f"RSI: {rsi:.2f if rsi else 'N/A'}, %K: {stochastic_k:.2f if stochastic_k else 'N/A'}, %D: {stochastic_d:.2f if stochastic_d else 'N/A'}")
        st.write(f"Bollinger Bands -> Superior: {upper_band:.2f}, Inferior: {lower_band:.2f}")
        st.write(f"Sinal: {signal if signal else 'Sem sinal'}")

# ---------------------------
# Loop principal
# ---------------------------
symbols = ["BTCUSDT", "ETHUSDT", "UNIUSDT", "FTMUSDT"]  # Exemplo
timeframes = ["1h", "4h"]

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
tasks = []

for symbol in symbols:
    for timeframe in timeframes:
        tasks.append(notify_conditions(symbol, timeframe))

loop.run_until_complete(asyncio.gather(*tasks))
