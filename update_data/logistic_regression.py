import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os

# Database path
DB_PATH = "sqlite:///performance.db"
TABLE_NAME = "asset_prices"

# Model save path
MODEL_PATH = "logistic_regression_model.pkl"

def load_data():
    """Load data from SQLite database."""
    engine = create_engine(DB_PATH)
    df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", con=engine)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values(["Ticker", "Date"])
    return df

def prepare_features_target(df):
    """Prepare features and target variable."""
    # Features
    features = ["RSI", "MACD", "MACD_Signal", "SMA_20", "SMA_50", "EMA_20", "EMA_50", "Volume"]

    # Create target: 1 if next price > current price, 0 otherwise
    df["Next_Price"] = df.groupby("Ticker")["Price"].shift(-1)
    df["Target"] = (df["Next_Price"] > df["Price"]).astype(int)

    # Drop rows with NaN in features or target
    df = df.dropna(subset=features + ["Target"])

    X = df[features]
    y = df["Target"]

    return X, y, df

def train_model(X, y):
    """Train Logistic Regression model."""
    # Split data (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # Train model
    model = LogisticRegression(random_state=42, max_iter=1000)
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Model Accuracy: {accuracy:.2f}")
    print(classification_report(y_test, y_pred))

    return model

def save_model(model, path):
    """Save trained model."""
    joblib.dump(model, path)
    print(f"Model saved to {path}")

def load_model(path):
    """Load trained model."""
    if os.path.exists(path):
        return joblib.load(path)
    else:
        return None

def predict_probability(model, features):
    """Predict probability of price rise."""
    prob = model.predict_proba(features.reshape(1, -1))[0][1]  # Probability of class 1
    return prob

def get_latest_features(ticker):
    """Get latest features for a ticker."""
    df = load_data()
    df_ticker = df[df["Ticker"] == ticker].sort_values("Date")
    if df_ticker.empty:
        return None
    latest = df_ticker.iloc[-1]
    features = ["RSI", "MACD", "MACD_Signal", "SMA_20", "SMA_50", "EMA_20", "EMA_50", "Volume"]
    return latest[features].values

if __name__ == "__main__":
    print("Loading data...")
    df = load_data()

    print("Preparing features and target...")
    X, y, df_processed = prepare_features_target(df)

    print("Training model...")
    model = train_model(X, y)

    print("Saving model...")
    save_model(model, MODEL_PATH)

    print("Model trained and saved successfully!")
