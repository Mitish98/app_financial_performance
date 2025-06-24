import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine
from itertools import combinations

# Configurações
TICKERS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "DOT-USD", "AVAX-USD", "LTC-USD", "XRP-USD", 
    "TRX-USD", "ADA-USD", "LINK-USD", "XLM-USD", "AAVE-USD", "HBAR-USD",
    "BCH-USD", "NEAR-USD", "ALGO-USD", "ATOM-USD", "ARB-USD", "TIA-USD", "OP-USD", 
    "IOTA-USD"
]
START_DATE = "2010-01-01"
END_DATE = "2030-01-01"
ROLLING_WINDOWS = [7, 15, 30, 60, 90]
DB_PATH = "sqlite:///correlation.db"

engine = create_engine(DB_PATH)

def fetch_and_store_data(tickers, start, end):
    print("Baixando dados do Yahoo Finance...")
    raw_df = yf.download(tickers, start=start, end=end, group_by='ticker', auto_adjust=True)
    
    valid_closes = []
    failed_tickers = []

    for ticker in tickers:
        try:
            close_series = raw_df[ticker]['Close'].dropna().rename(ticker)
            if not close_series.empty:
                valid_closes.append(close_series)
                print(f"[OK] {ticker} - Última data: {close_series.index[-1].date()}")
            else:
                print(f"[Vazio] {ticker} - Nenhum dado retornado.")
                failed_tickers.append(ticker)
        except Exception as e:
            print(f"[Erro] {ticker} - {e}")
            failed_tickers.append(ticker)

    if not valid_closes:
        raise ValueError("Nenhum dado válido foi baixado. Verifique os tickers ou a conexão.")

    df = pd.concat(valid_closes, axis=1)
    df = df.dropna()
    return df

def compute_all_rolling_correlations(df, windows):
    print("Calculando correlações móveis para todos os pares e janelas...")
    results = []
    for window in windows:
        print(f"Janela: {window} dias")
        for t1, t2 in combinations(df.columns, 2):
            corr = df[t1].rolling(window).corr(df[t2])
            df_corr = pd.DataFrame({
                'Date': corr.index,
                'Pair': f"{t1}/{t2}",
                'RollingCorrelation': corr.values,
                'Window': window
            })
            results.append(df_corr)
    all_corrs = pd.concat(results, ignore_index=True)
    return all_corrs

def export_to_excel(long_df, wide_df, file_name="correlacoes_moveis.xlsx"):
    print(f"Exportando para Excel: {file_name}")
    with pd.ExcelWriter(file_name, engine="openpyxl") as writer:
        long_df.to_excel(writer, sheet_name="Long_Format", index=False)
        wide_df.to_excel(writer, sheet_name="Wide_Format", index=False)
    print("Exportação concluída.")

if __name__ == "__main__":
    price_df = fetch_and_store_data(TICKERS, START_DATE, END_DATE)

    all_corr_df = compute_all_rolling_correlations(price_df, ROLLING_WINDOWS)

    all_corr_df.to_sql("rolling_correlation_long", con=engine, if_exists="replace", index=False)

    all_corr_wide = all_corr_df.pivot_table(index='Date', columns=['Pair', 'Window'], values='RollingCorrelation')
    all_corr_wide.reset_index(inplace=True)
    all_corr_wide.to_sql("rolling_correlation_wide", con=engine, if_exists="replace", index=False)

    print("Dados salvos com sucesso no banco SQLite.")

