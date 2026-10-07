"""WF005 Customer Order Status - order database/API + shipment lookup tools."""
from __future__ import annotations

import re
from typing import Optional

from ..models import Halt, StepOutcome, ToolError
from ..services.mock_apis import OrderAPI, ShipmentAPI
from . import ToolContext, register_tool

ORDER_RE = re.compile(r"^ORD-?(\d{3,})$", re.I)
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")


@register_tool("validate_identifier", "input validation", "Validate an order ID or customer email")
def validate_identifier(ctx: ToolContext, order_id: Optional[str] = None, email: Optional[str] = None,
                        ask: str = "") -> StepOutcome:
    m = ORDER_RE.match(order_id.strip()) if order_id else None
    if m:
        oid = f"ORD-{m.group(1)}"
        return StepOutcome({"type": "order_id", "value": oid}, f"Valid order ID {oid}",
                           decisions=["Identifier type: order ID"])
    if email and EMAIL_RE.match(email.strip()):
        return StepOutcome({"type": "email", "value": email.strip().lower()},
                           f"Valid customer email {email.strip().lower()}", decisions=["Identifier type: customer email"])
    bad = order_id or email
    msg = (f"'{bad}' is not a valid order ID (format ORD-1234) or email. " if bad else
           "I need an order ID (e.g. ORD-1001) or the customer's email address to look up an order. ") + ask
    return StepOutcome(None, msg.strip(), halt=Halt("needs_input", msg.strip(), ["order_id or email"]),
                       decisions=["No valid identifier -> ask user"])


@register_tool("order_lookup", "Order database/API", "Search orders via the (simulated) order API")
def order_lookup(ctx: ToolContext, identifier: dict) -> StepOutcome:
    api = OrderAPI(ctx.path("data"))
    kind, value = identifier["type"], identifier["value"]
    orders = api.search(order_id=value) if kind == "order_id" else api.search(email=value)
    if not orders:
        msg = (f"No order found for {kind.replace('_', ' ')} '{value}'. "
               "Please provide another identifier - a different order ID or the email used at checkout.")
        return StepOutcome([], msg, halt=Halt("needs_input", msg, ["order_id or email"]),
                           decisions=["No order found -> asking for another identifier"])
    return StepOutcome(orders, f"Order API returned {len(orders)} order(s) for {value}",
                       decisions=[f"Matched by {kind}"])


@register_tool("extract_order_status", "Order database/API", "Pull status and items from order records")
def extract_order_status(ctx: ToolContext, orders: list) -> StepOutcome:
    out = [{"order_id": o["order_id"], "order_date": o["order_date"], "status": o["status"],
            "items": ", ".join(f"{i['qty']} x {i['name']}" for i in o["items"]), "total": o["total"],
            "customer_email": o["customer_email"]} for o in orders]
    return StepOutcome(out, "; ".join(f"{o['order_id']}: {o['status']}" for o in out))


@register_tool("shipment_lookup", "Shipment lookup", "Fetch tracking information for each order")
def shipment_lookup(ctx: ToolContext, orders: list) -> StepOutcome:
    api = ShipmentAPI(ctx.path("data"))
    decisions, out = [], []
    for o in orders:
        row = dict(o)
        if o["status"] in ("Cancelled", "Processing"):
            row.update(carrier="-", tracking_number="-", shipment_status="Not shipped yet" if o["status"] == "Processing" else "N/A (cancelled)",
                       last_location="-", estimated_delivery="-")
            decisions.append(f"{o['order_id']}: status {o['status']} -> no shipment lookup needed")
        else:
            try:
                s = api.track(o["order_id"])
            except ToolError as exc:
                s = None
                decisions.append(f"{o['order_id']}: shipment API error ({exc}) -> tracking shown as unavailable")
            if s:
                row.update({k: s[k] for k in ("carrier", "tracking_number", "shipment_status", "last_location", "estimated_delivery")})
            else:
                row.update(carrier="-", tracking_number="unavailable", shipment_status="Tracking unavailable",
                           last_location="-", estimated_delivery="-")
        out.append(row)
    return StepOutcome(out, f"Shipment info retrieved for {sum(1 for r in out if r['tracking_number'] not in ('-', 'unavailable'))} of {len(out)} order(s)",
                       decisions=decisions)


@register_tool("summarize_order_status", "reporting", "Write a customer-friendly status summary")
def summarize_order_status(ctx: ToolContext, orders: list) -> StepOutcome:
    lines = []
    for o in orders:
        s = f"Order {o['order_id']} (placed {o['order_date']}) is **{o['status']}** - {o['items']}."
        if o.get("tracking_number") not in (None, "-", "unavailable"):
            s += (f" Shipped with {o['carrier']}, tracking {o['tracking_number']}: {o['shipment_status']} "
                  f"(last seen {o['last_location']}), estimated delivery {o['estimated_delivery']}.")
        elif o.get("tracking_number") == "unavailable":
            s += " Tracking information is temporarily unavailable."
        elif o["status"] == "Processing":
            s += " It has not shipped yet; tracking will be available once it ships."
        lines.append(s)
    return StepOutcome(lines, f"Summarised {len(lines)} order(s)")
