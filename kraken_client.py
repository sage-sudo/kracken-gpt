import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# --- kraken_client.py ---
import asyncio
import websockets
import json
import threading
import time
from collections import OrderedDict
from client_shared import shared_state, state_lock

import ssl
import certifi

# For dev/debug — disables SSL verification. DO NOT use in prod.
ssl_context = ssl._create_unverified_context()
# Use this for proper SSL:
# ssl_context = ssl.create_default_context(cafile=certifi.where())

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

        sorted_items = sorted(book.items(), reverse=(side == "b"))
        if side == "b":
            self.bids = OrderedDict(sorted_items)
        else:
            self.asks = OrderedDict(sorted_items)

    def top(self):
        bid = next(iter(self.bids.items()), (None, None))
        ask = next(iter(self.asks.items()), (None, None))
        return bid, ask

    def get_depth(self, depth=20):
        bids = list(self.bids.items())[:depth]
        asks = list(self.asks.items())[:depth]
        return bids, asks

class KrakenClient:
    def __init__(self, pairs=["XBT/USD"]):
        self.pairs = pairs
        self.uri = "wss://ws.kraken.com"
        self.books = {pair: LocalOrderBook() for pair in self.pairs}
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True

    async def connect(self):
        async with websockets.connect(self.uri, ssl=ssl_context) as ws:
            await ws.send(json.dumps({
                "event": "subscribe",
                "pair": self.pairs,
                "subscription": {"name": "book"}
            }))
            while True:
                message = await ws.recv()
                self.handle(json.loads(message))

    def handle(self, msg):
        if isinstance(msg, list) and len(msg) > 1:
            data = msg[1]
            pair = msg[-1]
            book = self.books[pair]

            if 'b' in data:
                book.update(data['b'], 'b')
            if 'a' in data:
                book.update(data['a'], 'a')

            bid, ask = book.top()
            bids, asks = book.get_depth()

            with state_lock:
                shared_state[pair] = {
                    "bid": bid[0],
                    "ask": ask[0],
                    "timestamp": time.time(),
                    "bids": bids,
                    "asks": asks
                }

    def run(self):
        asyncio.run(self.connect())

    def start(self):
        self.thread.start()
