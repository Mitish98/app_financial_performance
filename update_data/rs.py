import yfinance as yf
import pandas as pd
import numpy as np
from itertools import combinations
from sqlalchemy import create_engine
from tqdm import tqdm

# =============================
# Configuração
# =============================
TICKERS = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "DOT-USD", "AVAX-USD", "XRP-USD", 
    "AAVE-USD", "TRX-USD", "ADA-USD", "LINK-USD"]
START_DATE = "2010-01-01"
END_DATE = "2030-01-01"
WINDOWS = [3, 7, 14, 20, 30]

DB_PATH = "sqlite:///performance.db"
TABLE_NAME = "relative_strength_long"

# =============================
# Função para baixar preços e volumes
# =============================
def fetch_prices(tickers, start, end):
    data = yf.download(tickers, start=start, end=end, auto_adjust=True)
    close = data["Close"].dropna()
    volume = data["Volume"].dropna()
    return close, volume

# =============================
# Função para calcular MarketCap atual dos ativos
# =============================
def fetch_market_caps(tickers):
    marketcaps = []
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
            mc = info.get("marketCap", None)
            marketcaps.append({"Ticker": ticker, "MarketCap": mc})
        except Exception as e:
            print(f"⚠️ Não consegui pegar MarketCap de {ticker}: {e}")
            marketcaps.append({"Ticker": ticker, "MarketCap": None})
    return pd.DataFrame(marketcaps)

# =============================
# Calcular força relativa entre pares
# =============================
def compute_relative_strength(df, windows):
    all_pairs = list(combinations(df.columns, 2))
    results = []

    for base, quote in tqdm(all_pairs, desc="Calculando RS para todos os pares"):
        rs_series = df[base] / df[quote]
        for window in windows:
            rs_smooth = rs_series.rolling(window=window).mean()

            temp_df = pd.DataFrame({
                "Date": rs_series.index,
                "Pair": f"{base}/{quote}",
                "Base": base,
                "Quote": quote,
                "Window": window,
                "RS": rs_series.values,
                "RS_Smooth": rs_smooth.values
            })

            results.append(temp_df)

    final_df = pd.concat(results, ignore_index=True)
    return final_df.dropna(subset=["RS"])

# =============================
# Calcular indicadores técnicos (RSI, MACD, SMAs, EMAs)
# =============================
def compute_technical_indicators(df_prices):
    all_dfs = []
    for ticker in df_prices.columns:
        df = pd.DataFrame({
            "Date": df_prices.index,
            "Ticker": ticker,
            "Price": pd.to_numeric(df_prices[ticker], errors="coerce")
        }).dropna()

        # RSI (14)
        delta = df["Price"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss
        df["RSI"] = 100 - (100 / (1 + rs))

        # Médias móveis simples
        df["SMA_20"] = df["Price"].rolling(window=20).mean()
        df["SMA_50"] = df["Price"].rolling(window=50).mean()


        all_dfs.append(df)

    full_df = pd.concat(all_dfs, ignore_index=True)
    return full_df

# =============================
# Salvar dados de força relativa
# =============================
def save_to_sqlite(df, db_path, table_name):
    engine = create_engine(db_path)
    df.to_sql(table_name, con=engine, if_exists="replace", index=False)
    print(f"✅ Dados salvos com sucesso em '{table_name}' no banco '{db_path}'")

# =============================
# Salvar preços, volumes, indicadores e MarketCap
# =============================
def save_prices_to_sqlite(df_prices, df_volumes, db_path, table_name="asset_prices"):
    df_prices = df_prices.copy()
    df_volumes = df_volumes.copy()

    df_prices["Date"] = df_prices.index
    df_volumes["Date"] = df_volumes.index

    df_prices_melted = df_prices.melt(id_vars="Date", var_name="Ticker", value_name="Price")
    df_volumes_melted = df_volumes.melt(id_vars="Date", var_name="Ticker", value_name="Volume")

    df_merged = pd.merge(df_prices_melted, df_volumes_melted, on=["Date", "Ticker"])

    print("📈 Calculando indicadores técnicos...")
    df_indicators = compute_technical_indicators(df_prices)

    # Merge para juntar preços, volumes e indicadores
    final_df = pd.merge(df_merged, df_indicators, on=["Date", "Ticker", "Price"], how="left")

    # Adicionar MarketCap (último valor disponível por ativo)
    print("💰 Buscando MarketCap atual dos ativos...")
    marketcap_df = fetch_market_caps(df_prices.columns)
    final_df = pd.merge(final_df, marketcap_df, on="Ticker", how="left")

    engine = create_engine(db_path)
    final_df.to_sql(table_name, con=engine, if_exists="replace", index=False)
    print(f"✅ Preços, volumes, indicadores e MarketCap salvos na tabela '{table_name}'")

# =============================
# Execução principal
# =============================
if __name__ == "__main__":
    print("🔄 Baixando dados...")
    price_data, volume_data = fetch_prices(TICKERS, START_DATE, END_DATE)

    print("📊 Calculando força relativa...")
    rs_df = compute_relative_strength(price_data, WINDOWS)

    print("💾 Salvando dados de força relativa...")
    save_to_sqlite(rs_df, DB_PATH, TABLE_NAME)

    print("💾 Salvando preços, volumes, indicadores e MarketCap no banco de dados...")
    save_prices_to_sqlite(price_data, volume_data, DB_PATH)
