"""Generates the simulated business data used by the 10 workflows (deterministic, seed=42).

Run:  python scripts/generate_sample_data.py
The generated files are committed to the repo, so you only need this to regenerate them.
Each dataset deliberately contains edge cases that exercise the workflow decision logic.
"""
from __future__ import annotations

import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
random.seed(42)


def write_csv(name, rows):
    path = DATA / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path.relative_to(ROOT)} ({len(rows)} rows)")


# --- WF001 inventory --------------------------------------------------------
inventory = [
    # sku, name, category, current, minimum, case_pack, supplier
    ("SKU-1001", "Merino Wool Crew Sweater", "Knitwear", 4, 20, 6, "WoolWorks Ltd"),
    ("SKU-1002", "Organic Cotton T-Shirt", "Tops", 120, 50, 12, "GreenThreads"),
    ("SKU-1003", "Slim Fit Chino Trousers", "Bottoms", 18, 25, 6, "UrbanTailor"),
    ("SKU-1004", "Leather Chelsea Boots", "Footwear", 0, 10, 2, "StepRight"),
    ("SKU-1005", "Quilted Puffer Jacket", "Outerwear", 30, 15, 4, "NorthPeak"),
    ("SKU-1006", "Linen Button-Down Shirt", "Tops", 15, 15, 6, "GreenThreads"),   # equal -> NOT restock
    ("SKU-1007", "Cashmere Beanie", "Accessories", 7, 12, 10, "WoolWorks Ltd"),
    ("SKU-1008", "Canvas Tote Bag", "Accessories", 64, 30, 10, "BagCo"),
    ("SKU-1009", "Denim Trucker Jacket", "Outerwear", 9, 10, 4, "UrbanTailor"),
    ("SKU-1010", "Running Sneakers", "Footwear", 42, 20, 2, "StepRight"),
    ("SKU-1011", "Silk Scarf", "Accessories", 25, 8, 5, "SilkRoad Co"),
    ("SKU-1012", "Wool Blend Overcoat", "Outerwear", 3, 8, 2, "NorthPeak"),
]
write_csv("inventory.csv", [dict(sku=s, product_name=n, category=c, current_stock=cs, minimum_stock=m,
                                 case_pack=cp, supplier=sp) for s, n, c, cs, m, cp, sp in inventory])

# --- WF002 / WF007 internal products + vendor prices --------------------------
products = [
    ("SKU-1001", "Merino Wool Crew Sweater", "Knitwear", 89.00, "Autumn 2026", "merino wool", "charcoal"),
    ("SKU-1002", "Organic Cotton T-Shirt", "Tops", 24.00, "Core", "organic cotton", "white"),
    ("SKU-1003", "Slim Fit Chino Trousers", "Bottoms", 59.00, "Core", "cotton twill", "khaki"),
    ("SKU-1004", "Leather Chelsea Boots", "Footwear", 149.00, "Autumn 2026", "leather", "brown"),
    ("SKU-1005", "Quilted Puffer Jacket", "Outerwear", 129.00, "Autumn 2026", "recycled nylon", "olive"),
    ("SKU-1006", "Linen Button-Down Shirt", "Tops", 55.00, "Summer 2026", "linen", "sky blue"),
    ("SKU-1007", "Cashmere Beanie", "Accessories", 45.00, "Autumn 2026", "cashmere", "oatmeal"),
    ("SKU-1008", "Canvas Tote Bag", "Accessories", 19.00, "Core", "canvas", "natural"),
    ("SKU-1009", "Denim Trucker Jacket", "Outerwear", 99.00, "Core", "denim", "indigo"),
    ("SKU-1010", "Running Sneakers", "Footwear", 110.00, "Core", "mesh", "black"),
    ("SKU-1011", "Silk Scarf", "Accessories", 65.00, "Summer 2026", "silk", "emerald"),
    ("SKU-1012", "Wool Blend Overcoat", "Outerwear", 219.00, "Autumn 2026", "wool blend", "camel"),
]
write_csv("products.csv", [dict(sku=s, product_name=n, category=c, price=f"{p:.2f}", collection=col,
                                material=m, color=clr) for s, n, c, p, col, m, clr in products])

vendor_prices = [
    ("SKU-1001", 92.50), ("sku-1002", 21.00),        # 14.3% diff -> exception (key needs normalising)
    ("SKU-1003", 58.00), (" SKU-1004", 131.00),      # 13.7% -> exception
    ("SKU-1005", 129.00), ("SKU-1006", 50.00),       # exactly 10.0% -> NOT an exception ("exceeds")
    ("SKU-1007", 52.00),                              # -13.5% -> exception
    ("SKU-1008", 19.50), ("SKU-1009", 85.00),        # 16.5% -> exception
    ("SKU-1010", 112.00), ("SKU-1011", 66.00),
    # SKU-1012 missing at vendor -> unmatched internal
    ("SKU-2001", 30.00),                              # vendor-only SKU
]
write_csv("vendor_prices.csv", [dict(vendor_sku=s, vendor_name="Northwind Supply", vendor_price=f"{p:.2f}",
                                     currency="USD") for s, p in vendor_prices])

# --- WF003 vendor files (messy headers + invalid rows) -----------------------
vf = DATA / "vendor_files"
vf.mkdir(exist_ok=True)
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Products"
ws.append(["Item Code", " Product Title ", "Unit Price ($)", "Qty Available", "Colour", "Category"])
for row in [
    ["AC-501", "Waxed Cotton Field Jacket", 140, 25, "Olive", "Outerwear"],
    ["AC-502", "Ribbed Wool Socks (3-pack)", 18.5, 200, "Grey", "Accessories"],
    [None, "Corduroy Overshirt", 72, 40, "Tan", "Tops"],                 # missing SKU
    ["AC-504", "", 35, 60, "Navy", "Accessories"],                     # missing name
    ["AC-505", "Suede Desert Boots", 120, 30, "Sand", "Footwear"],
    ["  ", "   ", 15, 10, "Red", "Accessories"],                       # both blank
    ["ac-507 ", "  Heavyweight Hoodie ", "59.90", 80, "Black", "Tops"],  # needs trimming
    ["AC-508", "Packable Rain Shell", "N/A", 45, "Yellow", "Outerwear"],  # bad price -> warning only
]:
    ws.append(row)
wb.save(vf / "vendor_acme_products.xlsx")
print("wrote data/vendor_files/vendor_acme_products.xlsx")
write_csv("vendor_files/vendor_globex_products.csv", [
    {"Vendor SKU": "GX-01", "Name": "Merino Base Layer", "Cost": "54.00", "Stock": "120", "Color": "Black"},
    {"Vendor SKU": "GX-02", "Name": "Thermal Leggings", "Cost": "39.00", "Stock": "80", "Color": "Navy"},
    {"Vendor SKU": "", "Name": "Fleece Neck Gaiter", "Cost": "15.00", "Stock": "300", "Color": "Grey"},
    {"Vendor SKU": "GX-04", "Name": "", "Cost": "22.00", "Stock": "50", "Color": "Red"},
])
# A file without any recognisable SKU column, to demo a hard failure
write_csv("vendor_files/vendor_bad_format.csv", [{"foo": "1", "bar": "2"}])

# --- WF005 orders + shipments --------------------------------------------------
orders = [
    {"order_id": "ORD-1001", "customer_email": "priya.sharma@example.com", "order_date": "2026-09-28",
     "status": "Shipped", "items": [{"sku": "SKU-1001", "name": "Merino Wool Crew Sweater", "qty": 1},
                                    {"sku": "SKU-1007", "name": "Cashmere Beanie", "qty": 2}], "total": 179.00},
    {"order_id": "ORD-1002", "customer_email": "rahul.verma@example.com", "order_date": "2026-10-03",
     "status": "Processing", "items": [{"sku": "SKU-1004", "name": "Leather Chelsea Boots", "qty": 1}], "total": 149.00},
    {"order_id": "ORD-1003", "customer_email": "priya.sharma@example.com", "order_date": "2026-09-12",
     "status": "Delivered", "items": [{"sku": "SKU-1002", "name": "Organic Cotton T-Shirt", "qty": 3}], "total": 72.00},
    {"order_id": "ORD-1004", "customer_email": "anita.k@example.com", "order_date": "2026-09-30",
     "status": "Cancelled", "items": [{"sku": "SKU-1010", "name": "Running Sneakers", "qty": 1}], "total": 110.00},
]
shipments = [
    {"order_id": "ORD-1001", "carrier": "BlueDart", "tracking_number": "BD123456789IN", "shipment_status": "In transit",
     "last_location": "Mumbai Hub", "last_update": "2026-10-05T18:40:00", "estimated_delivery": "2026-10-08"},
    {"order_id": "ORD-1003", "carrier": "Delhivery", "tracking_number": "DL987654321IN", "shipment_status": "Delivered",
     "last_location": "Pune", "last_update": "2026-09-16T11:05:00", "estimated_delivery": "2026-09-16"},
]
(DATA / "orders.json").write_text(json.dumps(orders, indent=2))
(DATA / "shipments.json").write_text(json.dumps(shipments, indent=2))
print("wrote data/orders.json, data/shipments.json")

# --- WF006 catalog with duplicates -------------------------------------------
catalog = [
    ("TS-1001", "Classic Cotton T-Shirt - Black - M", "Northline", "Black", "M", 24.00),
    ("ts-1001 ", "Classic Cotton T-Shirt Black Medium", "Northline", "Black", "M", 24.00),   # exact SKU dup
    ("TS-1002", "Classic Cotton T-Shirt - Black - L", "Northline", "Black", "L", 24.00),     # variant, NOT dup
    ("TS-2001", "Classic Cotton Tshirt, Black, Medium", "Northline", "black", "Medium", 23.50),  # possible dup of TS-1001
    ("HD-3001", "Heavyweight Pullover Hoodie Grey", "Northline", "Grey", "L", 59.00),
    ("HD-3007", "Heavyweight Pull-over Hoodie (Grey)", "Northline", "Gray", "L", 59.00),     # possible dup
    ("JK-4001", "Quilted Puffer Jacket Olive", "NorthPeak", "Olive", "M", 129.00),
    ("JK-4001", "Quilted Puffer Jacket Olive", "NorthPeak", "Olive", "M", 129.00),           # exact dup
    ("JK-4002", "Quilted Puffer Jacket Black", "NorthPeak", "Black", "M", 129.00),           # colour variant
    ("BT-5001", "Leather Chelsea Boots Brown 42", "StepRight", "Brown", "42", 149.00),
    ("BT-5101", "Chelsea Boots Leather, Brown, EU 42", "StepRight", "Brown", "42", 145.00),  # possible dup
    ("SC-6001", "Silk Scarf Emerald", "SilkRoad Co", "Emerald", "OS", 65.00),
    ("BG-7001", "Canvas Tote Bag Natural", "BagCo", "Natural", "OS", 19.00),
    ("BG-7002", "Canvas Weekender Bag Natural", "BagCo", "Natural", "OS", 79.00),           # similar words, not dup
]
write_csv("catalog.csv", [dict(sku=s, product_name=n, brand=b, color=c, size=sz, price=f"{p:.2f}")
                          for s, n, b, c, sz, p in catalog])

# --- WF008 keywords + categories --------------------------------------------
keywords = [
    ("buy merino wool sweater", 2400), ("Buy Merino Wool Sweater ", 2400), ("how to wash merino wool", 5400),
    ("best puffer jacket 2026", 8100), ("puffer jacket vs parka", 1900), ("chelsea boots sale", 3600),
    ("cheap chelsea boots men", 1300), ("how to style chelsea boots", 4400), ("northline store login", 900),
    ("northline order tracking", 1200), ("organic cotton t-shirt price", 1000), ("what is organic cotton", 2900),
    ("silk scarf ways to tie", 3300), ("silk scarf discount code", 700), ("best running sneakers for flat feet", 6600),
    ("running sneakers buy online", 2900), ("cashmere beanie review", 880), ("canvas tote bag", 4400),
    ("northline returns policy", 1600), ("linen shirt vs cotton shirt", 1500), ("order linen button down shirt", 600),
    ("how to wash merino wool", 5400), ("wool overcoat men", 3900), ("top rated wool overcoats", 1700),
]
write_csv("keywords.csv", [dict(keyword=k, monthly_searches=v) for k, v in keywords])
write_csv("categories.csv", [
    dict(category="Knitwear", terms="sweater;merino;wool sweater;cardigan;knit", page="/collections/knitwear", guide_page="/blog/knitwear-care-guide"),
    dict(category="Outerwear", terms="puffer;jacket;parka;overcoat;coat", page="/collections/outerwear", guide_page="/blog/outerwear-buying-guide"),
    dict(category="Footwear", terms="boots;chelsea;sneakers;shoes;running", page="/collections/footwear", guide_page="/blog/footwear-style-guide"),
    dict(category="Tops", terms="t-shirt;tshirt;shirt;linen;cotton;organic cotton", page="/collections/tops", guide_page="/blog/fabric-guide"),
    dict(category="Accessories", terms="scarf;silk;beanie;cashmere;tote;bag", page="/collections/accessories", guide_page="/blog/accessories-styling"),
])

# --- WF009 employees + tasks ------------------------------------------------
employees = [
    ("E-101", "Aarav Mehta", "Developer", "python;api;payments;postgresql", 30, 40, "no", "senior"),
    ("E-102", "Sneha Iyer", "Developer", "python;api;django;payments", 38, 40, "no", "mid"),
    ("E-103", "Rohan Das", "Developer", "javascript;react;css;api", 20, 40, "no", "mid"),
    ("E-104", "Meera Nair", "Developer", "python;api;payments;aws", 10, 40, "yes", "senior"),   # on leave
    ("E-105", "Kabir Singh", "Developer", "python;data pipelines;sql", 12, 40, "no", "junior"),
    ("E-106", "Isha Kapoor", "Designer", "figma;ui;branding", 15, 40, "no", "mid"),
    ("E-107", "Vikram Rao", "Data Analyst", "sql;python;tableau", 22, 40, "no", "mid"),
    ("E-108", "Neha Joshi", "Marketing", "seo;copywriting;campaigns", 25, 40, "no", "senior"),
]
write_csv("employees.csv", [dict(employee_id=i, name=n, role=r, skills=s, current_workload_hours=w,
                                 weekly_capacity_hours=c, on_leave=l, seniority=sen)
                            for i, n, r, s, w, c, l, sen in employees])
write_csv("tasks.csv", [
    dict(task_id="TASK-301", title="Fix payment gateway timeout in checkout API",
         description="Checkout API intermittently times out when calling the payment gateway; needs a Python fix with retries.",
         required_skills="python;api;payments", priority="urgent", deadline="2026-10-08", estimated_hours=8,
         status="open", assignee=""),
    dict(task_id="TASK-302", title="Refresh autumn lookbook banners", description="Update homepage banners for the Autumn 2026 collection.",
         required_skills="figma;ui", priority="normal", deadline="2026-10-20", estimated_hours=6, status="open", assignee=""),
    dict(task_id="TASK-290", title="Migrate product search to Elasticsearch", description="Search migration",
         required_skills="python;elasticsearch", priority="high", deadline="2026-10-30", estimated_hours=30,
         status="in_progress", assignee="E-101"),
])

# --- WF010 execution logs (step-level) ---------------------------------------
wf_steps = {
    "WF001": ("Inventory Restock Check", ["Load inventory", "Compare stock", "Identify low-stock", "Calculate reorder", "Generate list"]),
    "WF002": ("Product Price Validation", ["Load prices", "Match SKUs", "Compare prices", "Calculate % diff", "Flag exceptions"]),
    "WF003": ("Vendor File Processing", ["Read file", "Detect columns", "Normalize columns", "Validate fields", "Identify invalid rows", "Produce cleaned dataset"]),
    "WF004": ("Product Description Generator", ["Validate attributes", "Create description", "Generate short description", "Generate SEO title", "Generate meta description"]),
    "WF005": ("Customer Order Status", ["Validate identifier", "Search order data", "Retrieve order status", "Retrieve shipment info", "Summarize status"]),
    "WF006": ("Duplicate Product Detection", ["Load products", "Normalize names/SKUs", "Compare identifiers", "Compare attributes", "Group duplicates", "Assign confidence"]),
    "WF007": ("Marketing Campaign Brief", ["Validate inputs", "Identify objective", "Summarize products", "Create messaging", "Channel recommendations", "Campaign checklist"]),
    "WF008": ("SEO Keyword Classification", ["Read keywords", "Remove duplicates", "Classify intent", "Map to categories", "Identify priority", "Export results"]),
    "WF009": ("Employee Task Assignment", ["Understand task", "Compare skills", "Check workload", "Rank candidates", "Select employee", "Assignment summary"]),
    "WF010": ("Workflow Performance Report", ["Load logs", "Success/failure rate", "Average time", "Frequent errors", "Slow steps", "Recommendations"]),
}
fail_profile = {  # workflow -> (failure probability, failing step, error messages)
    "WF003": (0.16, "Read file", ["Unsupported file encoding", "Missing header row", "Unsupported file encoding"]),
    "WF005": (0.22, "Search order data", ["Order API timeout after 30s", "Order API timeout after 30s", "Order API 503 Service Unavailable"]),
    "WF008": (0.12, "Classify intent", ["LLM rate limit exceeded (429)", "LLM returned invalid JSON"]),
    "WF004": (0.06, "Create description", ["LLM rate limit exceeded (429)"]),
    "WF009": (0.04, "Compare skills", ["Employee DB connection reset"]),
}
slow = {("WF004", "Create description"): 4200, ("WF004", "Generate SEO title"): 1800, ("WF008", "Classify intent"): 5200,
        ("WF007", "Create messaging"): 3600, ("WF007", "Channel recommendations"): 3100, ("WF006", "Compare attributes"): 2600}
logs = []
start = datetime(2026, 9, 1, 8, 0, 0)
run_no = 0
for day in range(30):
    for wid, (name, steps) in wf_steps.items():
        for _ in range(random.choice([1, 1, 2])):
            run_no += 1
            ts = start + timedelta(days=day, minutes=random.randint(0, 600))
            prob, fstep, msgs = fail_profile.get(wid, (0.02, steps[1], ["Unexpected null value"]))
            failing = random.random() < prob
            for st in steps:
                base = slow.get((wid, st), random.randint(80, 600))
                dur = max(20, int(random.gauss(base, base * 0.15)))
                status, err = "success", ""
                if failing and st == fstep:
                    status, err = "failed", random.choice(msgs)
                    if "timeout" in err:
                        dur = 30000
                logs.append(dict(timestamp=ts.isoformat(timespec="seconds"), run_id=f"R{run_no:05d}",
                                 workflow_id=wid, workflow_name=name, step_name=st, status=status,
                                 duration_ms=dur, error_message=err))
                ts += timedelta(milliseconds=dur)
                if status == "failed":
                    break
write_csv("workflow_execution_logs.csv", logs)
