import pandas as pd
import matplotlib.pyplot as plt

# Load CSV
path = r"C:\Users\trrallele\Momentum Metropolitan\REALEARN\CRYPTO STRATEGIES IN PYTHON\GPT\kracken-gpt\l2_data_logs\XBT-USD_orderbook_2025-05-10.csv"
cols = ["timestamp", "side", "price", "volume"]
df = pd.read_csv(path, names=cols, header=None, parse_dates=["timestamp"])

# Group to get best bid/ask
bids = df[df["side"] == "bid"]
asks = df[df["side"] == "ask"]
best_bids = bids.groupby("timestamp")["price"].max()
best_asks = asks.groupby("timestamp")["price"].min()

mid_price_df = pd.DataFrame({
    "best_bid": best_bids,
    "best_ask": best_asks
})
mid_price_df["mid_price"] = (mid_price_df["best_bid"] + mid_price_df["best_ask"]) / 2
mid_price_df = mid_price_df.reset_index()

# Detect liquidity walls near mid
wall_threshold = 15  # Volume threshold
proximity = 20         # Price units around mid

signals = []

for timestamp, row in mid_price_df.iterrows():
    ts = row["timestamp"]
    mid = row["mid_price"]

    # Get orders within time window
    snapshot = df[df["timestamp"] == ts]

    # Get orders near mid
    nearby_bids = snapshot[(snapshot["side"] == "bid") & (snapshot["price"] >= mid - proximity)]
    nearby_asks = snapshot[(snapshot["side"] == "ask") & (snapshot["price"] <= mid + proximity)]

    # Get biggest wall
    largest_bid = nearby_bids.loc[nearby_bids["volume"].idxmax()] if not nearby_bids.empty else None
    largest_ask = nearby_asks.loc[nearby_asks["volume"].idxmax()] if not nearby_asks.empty else None

    if largest_bid is not None and largest_bid["volume"] > wall_threshold:
        signals.append((ts, "LONG", mid))
    elif largest_ask is not None and largest_ask["volume"] > wall_threshold:
        signals.append((ts, "SHORT", mid))

# Plotting
signal_df = pd.DataFrame(signals, columns=["timestamp", "signal", "price"])

plt.figure(figsize=(14,6))
plt.plot(mid_price_df["timestamp"], mid_price_df["mid_price"], label='Mid Price', color='black')

# Plot signals
longs = signal_df[signal_df["signal"] == "LONG"]
shorts = signal_df[signal_df["signal"] == "SHORT"]
plt.scatter(longs["timestamp"], longs["price"], color='green', label='Long Signal', marker='^')
plt.scatter(shorts["timestamp"], shorts["price"], color='red', label='Short Signal', marker='v')

plt.legend()
plt.title("Liquidity Wall-Based Trade Signals")
plt.xlabel("Time")
plt.ylabel("Price")
plt.grid(True)
plt.tight_layout()
plt.show()

# -------------------------------------------------------------------------------------------------------

# --- Simulate trades ---
TP = 50   # take profit in price units
SL = 50    # stop loss in price units
trades = []

in_trade = False
entry = None

for i in range(len(signal_df)):
    signal = signal_df.iloc[i]
    ts = signal["timestamp"]
    direction = signal["signal"]
    entry_price = signal["price"]

    # Find future prices (forward-looking)
    future = mid_price_df[mid_price_df["timestamp"] > ts].copy()
    if future.empty:
        break

    exit_price = None
    exit_time = None
    for j, frow in future.iterrows():
        price = frow["mid_price"]
        if direction == "LONG":
            if price >= entry_price + TP:
                exit_price = entry_price + TP
                exit_time = frow["timestamp"]
                pnl = TP
                break
            elif price <= entry_price - SL:
                exit_price = entry_price - SL
                exit_time = frow["timestamp"]
                pnl = -SL
                break
        elif direction == "SHORT":
            if price <= entry_price - TP:
                exit_price = entry_price - TP
                exit_time = frow["timestamp"]
                pnl = TP
                break
            elif price >= entry_price + SL:
                exit_price = entry_price + SL
                exit_time = frow["timestamp"]
                pnl = -SL
                break

    if exit_price:
        trades.append({
            "entry_time": ts,
            "exit_time": exit_time,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "direction": direction,
            "PnL": pnl
        })

# --- Results ---
trade_df = pd.DataFrame(trades)
print("\n📈 TRADE SUMMARY 📈")
print(trade_df)
print("\n🔥 Total PnL:", trade_df["PnL"].sum())
print("✅ Winning Trades:", (trade_df["PnL"] > 0).sum())
print("❌ Losing Trades:", (trade_df["PnL"] < 0).sum())

# --- Visualize trade outcomes ---
plt.figure(figsize=(12,5))
plt.plot(mid_price_df["timestamp"], mid_price_df["mid_price"], label="Mid Price", color='gray')

for _, trade in trade_df.iterrows():
    color = "green" if trade["PnL"] > 0 else "red"
    plt.plot([trade["entry_time"], trade["exit_time"]],
             [trade["entry_price"], trade["exit_price"]],
             marker='o', color=color, linewidth=2)

plt.title("Trade Entries and Exits")
plt.xlabel("Time")
plt.ylabel("Price")
plt.grid(True)
plt.tight_layout()
plt.legend()
plt.show()

