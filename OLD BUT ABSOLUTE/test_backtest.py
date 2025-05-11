from backtest_parser import load_orderbook_csv, get_snapshot_group, get_mid_prices, detect_liquidity_walls

path = r"C:\Users\trrallele\Momentum Metropolitan\REALEARN\CRYPTO STRATEGIES IN PYTHON\GPT\kracken-gpt\l2_data_logs\XBT-USD_orderbook_2025-05-10.csv"

df = load_orderbook_csv(path)
grouped = get_snapshot_group(df)

mids = get_mid_prices(grouped)
walls = detect_liquidity_walls(grouped, threshold=15.0)

# Plot
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 6))
plt.plot(mids["timestamp"], mids["mid_price"], label="Mid Price", color="black")

support_walls = walls[walls["type"] == "support"]
resistance_walls = walls[walls["type"] == "resistance"]

plt.scatter(support_walls["timestamp"], support_walls["price"], label="Support Wall", color="green", alpha=0.6)
plt.scatter(resistance_walls["timestamp"], resistance_walls["price"], label="Resistance Wall", color="red", alpha=0.6)

plt.title("Mid Price & Liquidity Walls")
plt.xlabel("Time")
plt.ylabel("Price")
plt.legend()
plt.tight_layout()
plt.show()
