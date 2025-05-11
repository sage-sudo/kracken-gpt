#from backtest_engine.base_engine import BacktestEngine
#from backtest_engine.strategy_liquidity import liquidity_wall_strategy
from base_engine import BacktestEngine
from strategy_liquidity import liquidity_wall_strategy

if __name__ == "__main__":
    path = r"C:\Users\trrallele\Momentum Metropolitan\REALEARN\CRYPTO STRATEGIES IN PYTHON\GPT\kracken-gpt\l2_data_logs\XBT-USD_orderbook_2025-05-10.csv"
    engine = BacktestEngine(
        strategy_fn=liquidity_wall_strategy,
        data_path=path,
        capital=20,
        risk_pct=100,
        TP=50,
        SL=50
    )
    engine.run()
