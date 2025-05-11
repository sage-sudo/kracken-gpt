import pandas as pd
import matplotlib.pyplot as plt

class BacktestEngine:
    def __init__(self, strategy_fn, data_path, capital=20, risk_pct=100, TP=50, SL=50,
                 maker_fee=0.0016, taker_fee=0.0026, slippage=1.0):
        self.strategy_fn = strategy_fn
        self.data_path = data_path
        self.capital = capital
        self.risk_pct = risk_pct
        self.TP = TP
        self.SL = SL
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.slippage = slippage

    def load_data(self):
        cols = ["timestamp", "side", "price", "volume"]
        df = pd.read_csv(self.data_path, names=cols, header=None, parse_dates=[0])
        df.columns = cols
        return df

    def compute_mid_prices(self, df):
        bids = df[df["side"] == "bid"]
        asks = df[df["side"] == "ask"]
        best_bids = bids.groupby("timestamp")["price"].max()
        best_asks = asks.groupby("timestamp")["price"].min()

        mid_price_df = pd.DataFrame({
            "best_bid": best_bids,
            "best_ask": best_asks
        })
        mid_price_df["mid_price"] = (mid_price_df["best_bid"] + mid_price_df["best_ask"]) / 2
        mid_price_df.reset_index(inplace=True)
        return mid_price_df

    def simulate_trades(self, signal_df, mid_price_df):
        trades = []
        for _, signal in signal_df.iterrows():
            ts, direction, entry_price = signal["timestamp"], signal["signal"], signal["price"]
            risk_amount = self.capital * (self.risk_pct / 100)
            position_size = risk_amount / self.SL
            position_value = entry_price * position_size

            future = mid_price_df[mid_price_df["timestamp"] > ts].copy()
            if future.empty:
                break

            exit_price = None
            pnl, exit_time = 0, None

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

        trade_df = pd.DataFrame(trades)
        if not trade_df.empty:
            trade_df["cumulative_pnl"] = trade_df["net_pnl"].cumsum()
            trade_df["equity"] = self.capital + trade_df["cumulative_pnl"]
        return trade_df

    def run(self):
        df = self.load_data()
        mid_price_df = self.compute_mid_prices(df)
        signal_df = self.strategy_fn(df, mid_price_df)
        trade_df = self.simulate_trades(signal_df, mid_price_df)
        self.print_summary(trade_df)
        self.plot_equity_curve(trade_df)

    def print_summary(self, trade_df):
        if trade_df.empty:
            print("💤 No trades were executed. Check signal logic or data range.")
        else:
            print(trade_df[["entry_time", "direction", "net_pnl", "equity"]])
            print("🔥 Final Balance:", trade_df['equity'].iloc[-1])
            print("📉 Max Drawdown:", (trade_df["equity"].cummax() - trade_df["equity"]).max())

    def plot_equity_curve(self, trade_df):
        if trade_df.empty:
            return
        plt.figure(figsize=(10, 5))
        plt.plot(trade_df["exit_time"], trade_df["equity"], label="Equity Curve", color="blue")
        plt.title("Equity Curve (Modular Engine)")
        plt.xlabel("Time")
        plt.ylabel("Equity ($)")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.show()
