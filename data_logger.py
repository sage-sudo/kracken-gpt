# --- data_logger.py ---
import csv
import os
import time
from datetime import datetime
from client_shared import shared_state, state_lock
import threading

PAIR = "XBT/USD"
SAVE_DIR = "l2_data_logs"
os.makedirs(SAVE_DIR, exist_ok=True)

def get_log_path():
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"{PAIR.replace('/', '-')}_orderbook_{date_str}.csv"
    return os.path.join(SAVE_DIR, filename)

def write_snapshot():
    with state_lock:
        data = shared_state.get(PAIR, {})

    if not data:
        return

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    bids = data.get("bids", [])[:10]
    asks = data.get("asks", [])[:10]

    rows = []
    for price, volume in bids:
        rows.append([timestamp, "bid", price, volume])
    for price, volume in asks:
        rows.append([timestamp, "ask", price, volume])

    filepath = get_log_path()
    with open(filepath, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

def start_logger(interval=1.0):
    def loop():
        while True:
            write_snapshot()
            time.sleep(interval)

    thread = threading.Thread(target=loop)
    thread.daemon = True
    thread.start()
