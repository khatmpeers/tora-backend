from __future__ import annotations

import copy
import threading
from typing import Dict, Optional

_store_lock = threading.Lock()
_active_feed: Optional[Dict[str, object]] = None


def set_active_feed(feed_payload: Dict[str, object]) -> None:
    global _active_feed
    with _store_lock:
        _active_feed = copy.deepcopy(feed_payload)


def get_active_feed() -> Optional[Dict[str, object]]:
    with _store_lock:
        if _active_feed is None:
            return None
        return copy.deepcopy(_active_feed)


def is_feed_loaded() -> bool:
    with _store_lock:
        return _active_feed is not None


def clear_active_feed() -> None:
    global _active_feed
    with _store_lock:
        _active_feed = None
