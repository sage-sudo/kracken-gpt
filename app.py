# --- app.py ---
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from client_shared import shared_state, state_lock
from kraken_client import KrakenClient
import time

from data_logger import start_logger

app = dash.Dash(__name__)
app.title = "Kraken Order Book"

pairs = ["XBT/USD"]

# Store rolling mid-price + signal history
price_history = []

app.layout = html.Div([
    html.H1("📊 Real-Time Kraken Order Book"),
    dcc.Graph(id='depth-chart'),
    dcc.Graph(id='signal-chart'),
    dcc.Interval(id='interval', interval=1000, n_intervals=0)
])

def make_depth_chart(data):
    bids = data.get("bids", [])
    asks = data.get("asks", [])

    bid_prices = [price for price, _ in bids]
    bid_volumes = [volume for _, volume in bids]
    bid_cum = [sum(bid_volumes[:i+1]) for i in range(len(bid_volumes))]

    ask_prices = [price for price, _ in asks]
    ask_volumes = [volume for _, volume in asks]
    ask_cum = [sum(ask_volumes[:i+1]) for i in range(len(ask_volumes))]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=bid_prices, y=bid_cum, fill='tozeroy', mode='lines', name='Bids', line=dict(color='green')))
    fig.add_trace(go.Scatter(x=ask_prices, y=ask_cum, fill='tozeroy', mode='lines', name='Asks', line=dict(color='red')))
    fig.update_layout(title=f"{pairs[0]} Depth Chart", xaxis_title="Price", yaxis_title="Cumulative Volume")
    return fig

def make_signal_chart():
    if not price_history:
        return go.Figure()

    timestamps = [p["time"] for p in price_history]
    mid_prices = [p["mid"] for p in price_history]
    buy_signals = [p["mid"] if p["signal"] == "BUY" else None for p in price_history]
    sell_signals = [p["mid"] if p["signal"] == "SELL" else None for p in price_history]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=timestamps, y=mid_prices, mode='lines', name='Mid-Price'))
    fig.add_trace(go.Scatter(x=timestamps, y=buy_signals, mode='markers', name='Buy Signal', marker=dict(color='green', symbol='triangle-up', size=10)))
    fig.add_trace(go.Scatter(x=timestamps, y=sell_signals, mode='markers', name='Sell Signal', marker=dict(color='red', symbol='triangle-down', size=10)))
    fig.update_layout(title="Mid-Price with Trade Signals", xaxis_title="Time", yaxis_title="Mid Price")
    return fig

@app.callback(
    [Output('depth-chart', 'figure'), Output('signal-chart', 'figure')],
    [Input('interval', 'n_intervals')]
)
def update_charts(n):
    with state_lock:
        data = shared_state.get(pairs[0], {})

    depth_fig = make_depth_chart(data)

    # --- Signal logic ---
    bid_price = data.get("bid_price")
    bid_size = data.get("bid_size")
    ask_price = data.get("ask_price")
    ask_size = data.get("ask_size")

    if bid_price and ask_price and bid_size and ask_size:
        mid = (bid_price + ask_price) / 2
        imbalance = (bid_size - ask_size) / (bid_size + ask_size + 1e-9)  # Avoid division by zero

        signal = None
        if imbalance > 0.6:
            signal = "BUY"
        elif imbalance < -0.6:
            signal = "SELL"

        price_history.append({
            "time": time.strftime('%H:%M:%S'),
            "mid": mid,
            "signal": signal
        })

        # Keep last 100 points
        if len(price_history) > 100:
            price_history.pop(0)

    signal_fig = make_signal_chart()
    return depth_fig, signal_fig

if __name__ == '__main__':
    kraken_client = KrakenClient(pairs=pairs)
    kraken_client.start()
    
    start_logger(interval=1.0)  # <-- Start snapshot logging

    app.run(debug=True, use_reloader=False)
