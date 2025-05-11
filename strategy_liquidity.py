import pandas as pd

def liquidity_wall_strategy(df, mid_price_df, wall_threshold=15, proximity_ticks=20):
    signals = []
    grouped = df.groupby("timestamp")
    for timestamp, snapshot in grouped:
        bids = snapshot[snapshot["side"] == "bid"][["price", "volume"]].values
        asks = snapshot[snapshot["side"] == "ask"][["price", "volume"]].values
        mid_row = mid_price_df[mid_price_df["timestamp"] == timestamp]
        if mid_row.empty:
            continue
        mid = mid_row["mid_price"].values[0]

        nearby_bids = [(p, v) for p, v in bids if p >= mid - proximity_ticks]
        nearby_asks = [(p, v) for p, v in asks if p <= mid + proximity_ticks]
        largest_bid = max(nearby_bids, key=lambda x: x[1], default=(None, 0))
        largest_ask = max(nearby_asks, key=lambda x: x[1], default=(None, 0))

        if largest_bid[1] > wall_threshold:
            signals.append((timestamp, 'LONG', mid))
        elif largest_ask[1] > wall_threshold:
            signals.append((timestamp, 'SHORT', mid))

    return pd.DataFrame(signals, columns=["timestamp", "signal", "price"])
