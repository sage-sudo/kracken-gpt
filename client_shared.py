# --- shared_client.py ---
from collections import defaultdict
import threading

shared_state = defaultdict(dict)
state_lock = threading.Lock()