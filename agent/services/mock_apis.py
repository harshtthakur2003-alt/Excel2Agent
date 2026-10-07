"""Simulated external APIs (order database and shipment tracking).

Real systems are unavailable, so these classes mimic API behaviour: JSON
payloads, latency, "not found" responses and *injectable failures* to
demonstrate retry / error handling.

Failure injection:  SIMULATE_API_FAILURE="order_api:2"  -> first 2 calls fail
                    SIMULATE_API_FAILURE="shipment_api"  -> every call fails
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

from ..models import ToolError

_CALLS: dict[str, int] = {}


def _maybe_fail(api: str) -> None:
    spec = os.getenv("SIMULATE_API_FAILURE", "")
    for part in filter(None, (p.strip() for p in spec.split(","))):
        name, _, n = part.partition(":")
        if name != api:
            continue
        _CALLS[api] = _CALLS.get(api, 0) + 1
        if not n or _CALLS[api] <= int(n):
            raise ToolError(f"{api} unavailable (simulated 503 Service Unavailable)")


def reset_failures() -> None:
    _CALLS.clear()


class OrderAPI:
    def __init__(self, data_dir: Path, latency_s: float = 0.05):
        self.path = Path(data_dir) / "orders.json"
        self.latency_s = latency_s

    def search(self, order_id: Optional[str] = None, email: Optional[str] = None) -> list[dict]:
        _maybe_fail("order_api")
        time.sleep(self.latency_s)
        orders = json.loads(self.path.read_text(encoding="utf-8"))
        if order_id:
            return [o for o in orders if o["order_id"].upper() == order_id.strip().upper()]
        if email:
            return [o for o in orders if o["customer_email"].lower() == email.strip().lower()]
        return []


class ShipmentAPI:
    def __init__(self, data_dir: Path, latency_s: float = 0.05):
        self.path = Path(data_dir) / "shipments.json"
        self.latency_s = latency_s

    def track(self, order_id: str) -> Optional[dict]:
        _maybe_fail("shipment_api")
        time.sleep(self.latency_s)
        for s in json.loads(self.path.read_text(encoding="utf-8")):
            if s["order_id"] == order_id:
                return s
        return None
