# --- app.py ---
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from client_shared import shared_state, state_lock
from kraken_client import KrakenClient



app = dash.Dash(__name__)
app.title = "Kraken Order Book"

pairs = ["XBT/USD"]

app.layout = html.Div([
    html.H1("📊 Real-Time Kraken Order Book Depth Chart"),
    dcc.Graph(id='depth-chart'),
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

@app.callback(Output('depth-chart', 'figure'), Input('interval', 'n_intervals'))
def update_chart(n):
    with state_lock:
        data = shared_state.get(pairs[0], {})
    return make_depth_chart(data)

if __name__ == '__main__':
    kraken_client = KrakenClient(pairs=pairs)
    kraken_client.start()
    app.run(debug=True, use_reloader=False)