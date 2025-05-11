# --- backtest_parser.py ---
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set(style="darkgrid")

def load_orderbook_csv(file_path):
    df = pd.read_csv(file_path, names=["timestamp", "side", "price", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["price"] = df["price"].astype(float)
    df["volume"] = df["volume"].astype(float)
    return df

def get_snapshot_group(df):
    # Group by timestamp to form one snapshot per second
    grouped = df.groupby("timestamp")
    return grouped

def get_mid_prices(grouped):
    mids = []
    for ts, g in grouped:
        try:
            best_bid = g[g["side"] == "bid"]["price"].max()
            best_ask = g[g["side"] == "ask"]["price"].min()
            mid = (best_bid + best_ask) / 2
            mids.append({"timestamp": ts, "mid_price": mid})
        except:
            continue
    return pd.DataFrame(mids)

def detect_liquidity_walls(grouped, threshold=5.0):
    """Detects if there's any price level with unusually large volume."""
    walls = []
    for ts, g in grouped:
        bids = g[g["side"] == "bid"]
        asks = g[g["side"] == "ask"]

        max_bid = bids.loc[bids["volume"].idxmax()] if not bids.empty else None
        max_ask = asks.loc[asks["volume"].idxmax()] if not asks.empty else None

        if max_bid is not None and max_bid["volume"] > threshold:
            walls.append({"timestamp": ts, "type": "support", "price": max_bid["price"], "volume": max_bid["volume"]})

        if max_ask is not None and max_ask["volume"] > threshold:
            walls.append({"timestamp": ts, "type": "resistance", "price": max_ask["price"], "volume": max_ask["volume"]})

    return pd.DataFrame(walls)
