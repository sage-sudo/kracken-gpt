# backtest_engine.py
import pandas as pd
import matplotlib.pyplot as plt

class LiquidityWallBacktester:
    def __init__(self, csv_path, wall_threshold=100, proximity_ticks=5, 
                 capital=10_000, risk_pct=1, TP=50, SL=50,
                 maker_fee=0.0016, taker_fee=0.0026, slippage=1.0):
        self.csv_path = csv_path
        self.wall_threshold = wall_threshold
        self.proximity_ticks = proximity_ticks
        self.capital = capital
        self.risk_pct = risk_pct
        self.TP = TP
        self.SL = SL
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.slippage = slippage

        self.df = None
        self.mid_price_df = None
        self.signal_df = None
        self.trade_df = None

    def load_data(self):
        cols = ["timestamp", "side", "price", "volume"]
        self.df = pd.read_csv(self.csv_path, names=cols, header=None, parse_dates=[0])
        self.df.columns = cols

    def compute_mid_prices(self):
        bids = self.df[self.df["side"] == "bid"]
        asks = self.df[self.df["side"] == "ask"]
        best_bids = bids.groupby("timestamp")["price"].max()
        best_asks = asks.groupby("timestamp")["price"].min()

        self.mid_price_df = pd.DataFrame({
            "best_bid": best_bids,
            "best_ask": best_asks
        })
        self.mid_price_df["mid_price"] = (self.mid_price_df["best_bid"] + self.mid_price_df["best_ask"]) / 2
        self.mid_price_df.reset_index(inplace=True)

    def generate_signals(self):
        signals = []
        grouped = self.df.groupby("timestamp")
        for timestamp, snapshot in grouped:
            bids = snapshot[snapshot["side"] == "bid"][["price", "volume"]].values
            asks = snapshot[snapshot["side"] == "ask"][["price", "volume"]].values
            mid_row = self.mid_price_df[self.mid_price_df["timestamp"] == timestamp]
            if mid_row.empty:
                continue
            mid = mid_row["mid_price"].values[0]

            nearby_bids = [(p, v) for p, v in bids if p >= mid - self.proximity_ticks]
            nearby_asks = [(p, v) for p, v in asks if p <= mid + self.proximity_ticks]
            largest_bid = max(nearby_bids, key=lambda x: x[1], default=(None, 0))
            largest_ask = max(nearby_asks, key=lambda x: x[1], default=(None, 0))

            if largest_bid[1] > self.wall_threshold:
                signals.append((timestamp, 'LONG', mid))
            elif largest_ask[1] > self.wall_threshold:
                signals.append((timestamp, 'SHORT', mid))

        self.signal_df = pd.DataFrame(signals, columns=["timestamp", "signal", "price"])

    def simulate_trades(self):
        trades = []
        for _, signal in self.signal_df.iterrows():
            ts = signal["timestamp"]
            direction = signal["signal"]
            entry_price = signal["price"]

            risk_amount = self.capital * (self.risk_pct / 100)
            position_size = risk_amount / self.SL
            position_value = entry_price * position_size

            future = self.mid_price_df[self.mid_price_df["timestamp"] > ts].copy()
            if future.empty:
                break

            exit_price = None
            pnl = 0
            exit_time = None

            for _, frow in future.iterrows():
                price = frow["mid_price"]
                if direction == "LONG":
                    if price >= entry_price + self.TP:
                        exit_price = entry_price + self.TP - self.slippage
                        pnl = (exit_price - entry_price) * position_size
                        exit_time = frow["timestamp"]
                        break
                    elif price <= entry_price - self.SL:
                        exit_price = entry_price - self.SL - self.slippage
                        pnl = (exit_price - entry_price) * position_size
                        exit_time = frow["timestamp"]
                        break
                elif direction == "SHORT":
                    if price <= entry_price - self.TP:
                        exit_price = entry_price - self.TP + self.slippage
                        pnl = (entry_price - exit_price) * position_size
                        exit_time = frow["timestamp"]
                        break
                    elif price >= entry_price + self.SL:
                        exit_price = entry_price + self.SL + self.slippage
                        pnl = (entry_price - exit_price) * position_size
                        exit_time = frow["timestamp"]
                        break

            if exit_price:
                fees = position_value * (self.maker_fee + self.taker_fee)
                net_pnl = pnl - fees
                trades.append({
                    "entry_time": ts,
                    "exit_time": exit_time,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "direction": direction,
                    "position_size": position_size,
                    "gross_pnl": pnl,
                    "fees": fees,
                    "net_pnl": net_pnl
                })

        self.trade_df = pd.DataFrame(trades)
        if not self.trade_df.empty:
            self.trade_df["cumulative_pnl"] = self.trade_df["net_pnl"].cumsum()
            self.trade_df["equity"] = self.capital + self.trade_df["cumulative_pnl"]

    def print_summary(self):
        if self.trade_df.empty:
            print("💤 No trades were executed. Check signal logic or data range.")
        else:
            print(self.trade_df[["entry_time", "direction", "net_pnl", "equity"]])
            print("🔥 Final Balance:", self.trade_df['equity'].iloc[-1])
            print("📉 Max Drawdown:", (self.trade_df["equity"].cummax() - self.trade_df["equity"]).max())

    def plot_equity_curve(self):
        if self.trade_df.empty:
            return
        plt.figure(figsize=(10, 5))
        plt.plot(self.trade_df["exit_time"], self.trade_df["equity"], label="Equity Curve", color="blue")
        plt.title("Equity Curve (Realistic Simulation)")
        plt.xlabel("Time")
        plt.ylabel("Equity ($)")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.show()

    def run(self):
        self.load_data()
        self.compute_mid_prices()
        self.generate_signals()
        self.simulate_trades()
        self.print_summary()
        self.plot_equity_curve()
