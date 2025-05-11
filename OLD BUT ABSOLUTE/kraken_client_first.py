# -------------------- kraken_client.py --------------------

import asyncio
import websockets
import threading
import json
import time
import requests
from collections import OrderedDict
import ssl
import certifi

ssl_context = ssl._create_unverified_context()

class LocalOrderBook:
    def __init__(self):
        self.bids = OrderedDict()
        self.asks = OrderedDict()

    def update(self, updates, side):
        book = self.bids if side == "b" else self.asks
        for update in updates:
            price, volume = float(update[0]), float(update[1])
            if volume == 0:
                book.pop(price, None)
            else:
                book[price] = volume

        if side == "b":
            self.bids = OrderedDict(sorted(book.items(), reverse=True))
        else:
            self.asks = OrderedDict(sorted(book.items()))

    def patch_from_snapshot(self, snapshot_bids, snapshot_asks):
        self._patch_side(snapshot_bids, self.bids, side="b")
        self._patch_side(snapshot_asks, self.asks, side="a")

    def _patch_side(self, snapshot, book, side):
        if len(book) >= 100:
            return

        for update in snapshot:
            price, volume = float(update[0]), float(update[1])
            if price not in book and len(book) < 100:
                book[price] = volume

        if side == "b":
            self.bids = OrderedDict(sorted(book.items(), reverse=True))
        else:
            self.asks = OrderedDict(sorted(book.items()))

    def top_of_book(self):
        best_bid = next(iter(self.bids.items()), (None, None))
        best_ask = next(iter(self.asks.items()), (None, None))
        return best_bid, best_ask

    def spread(self):
        bid, ask = self.top_of_book()
        if bid[0] is not None and ask[0] is not None:
            return round(ask[0] - bid[0], 2)
        return None

    def order_book_imbalance(self, depth=10):
        top_bids = list(self.bids.items())[:depth]
        top_asks = list(self.asks.items())[:depth]
        bid_vol = sum(vol for _, vol in top_bids)
        ask_vol = sum(vol for _, vol in top_asks)
        if bid_vol + ask_vol == 0:
            return None
        return round((bid_vol - ask_vol) / (bid_vol + ask_vol), 4)

    def needs_patch(self):
        return len(self.bids) < 100 or len(self.asks) < 100

class KrakenL2Client:
    def __init__(self, shared_state, pairs=["XBT/USD"], depth=100):
        self.pairs = pairs
        self.depth = depth
        self.uri = "wss://ws.kraken.com"
        self.loop = None
        self.thread = None
        self.stop_event = threading.Event()
        self.order_books = {pair: LocalOrderBook() for pair in self.pairs}
        self.last_patch_time = time.time()
        self.shared_state = shared_state

    async def connect(self):
        async with websockets.connect(self.uri, ssl=ssl_context) as websocket:
            await websocket.send(json.dumps({
                "event": "subscribe",
                "pair": self.pairs,
                "subscription": {"name": "book", "depth": self.depth}
            }))
            print(f"📡 Subscribed to: {', '.join(self.pairs)}")

            while not self.stop_event.is_set():
                try:
                    message = await websocket.recv()
                    self.handle_message(json.loads(message))
                    self.maybe_patch_books()
                except Exception as e:
                    print(f"⚠️ Error: {e}")
                    break

    def maybe_patch_books(self):
        if time.time() - self.last_patch_time < 5:
            return

        for pair in self.pairs:
            book = self.order_books[pair]
            if book.needs_patch():
                print(f"🔧 Patching {pair}...")
                bids, asks = self.fetch_snapshot(pair)
                if bids and asks:
                    book.patch_from_snapshot(bids, asks)
        self.last_patch_time = time.time()

    def fetch_snapshot(self, pair):
        symbol = pair.replace("/", "")
        url = f"https://api.kraken.com/0/public/Depth?pair={symbol}&count=100"
        try:
            resp = requests.get(url, timeout=5)
            data = resp.json()
            key = list(data["result"].keys())[0]
            return data["result"][key]["bids"], data["result"][key]["asks"]
        except Exception as e:
            print(f"❌ Snapshot error: {e}")
            return None, None

    def handle_message(self, message):
        if isinstance(message, dict):
            if message.get("event") in ["heartbeat", "systemStatus", "subscriptionStatus"]:
                return

        if isinstance(message, list) and len(message) > 1:
            data = message[1]
            pair = message[-1]
            book = self.order_books.get(pair)
            if not book:
                return

            if 'a' in data:
                book.update(data['a'], 'a')
            if 'b' in data:
                book.update(data['b'], 'b')

            bid, ask = book.top_of_book()
            spread = book.spread()
            imbalance = book.order_book_imbalance()

            self.shared_state[pair] = {
                "bid": bid[0],
                "ask": ask[0],
                "spread": spread,
                "imbalance": imbalance,
                "timestamp": time.time(),
            }

    def start(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.connect())

    def run_in_thread(self):
        self.thread = threading.Thread(target=self.start)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread:
            self.thread.join()
