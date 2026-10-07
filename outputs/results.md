# Example runs

Generated 2026-10-06 11:11 · LLM mode: `offline-fallback` · 10 workflows loaded from Excel


## Summary

| Case | Turn | Workflow | Status | Expected | OK |
|---|---|---|---|---|---|
| WF001-excel-test | 1 | WF001 | completed | completed | ✅ |
| WF001-custom-threshold | 1 | WF001 | completed | completed | ✅ |
| WF002-excel-test | 1 | WF002 | completed | completed | ✅ |
| WF002-custom-tolerance | 1 | WF002 | completed | completed | ✅ |
| WF003-excel-test | 1 | WF003 | completed | completed | ✅ |
| WF003-no-file-attached | 1 | WF003 | needs_input | needs_input | ✅ |
| WF003-csv-different-headers | 1 | WF003 | completed | completed | ✅ |
| WF003-error-unrecognised-format | 1 | WF003 | failed | failed | ✅ |
| WF004-excel-test-no-product | 1 | WF004 | needs_input | needs_input | ✅ |
| WF004-excel-test-with-product | 1 | WF004 | completed | completed | ✅ |
| WF004-text-only-followup | 1 | WF004 | needs_input | needs_input | ✅ |
| WF004-text-only-followup | 2 | WF004 | completed | completed | ✅ |
| WF004-inline-product | 1 | WF004 | completed | completed | ✅ |
| WF005-excel-test | 1 | WF005 | completed | completed | ✅ |
| WF005-not-found-then-email | 1 | WF005 | needs_input | needs_input | ✅ |
| WF005-not-found-then-email | 2 | WF005 | completed | completed | ✅ |
| WF005-processing-order | 1 | WF005 | completed | completed | ✅ |
| WF005-api-outage-retry | 1 | WF005 | completed | completed | ✅ |
| WF005-api-down | 1 | WF005 | failed | failed | ✅ |
| WF006-excel-test | 1 | WF006 | completed | completed | ✅ |
| WF007-excel-test-then-followup | 1 | WF007 | needs_input | needs_input | ✅ |
| WF007-excel-test-then-followup | 2 | WF007 | completed | completed | ✅ |
| WF007-named-products | 1 | WF007 | completed | completed | ✅ |
| WF007-invalid-dates | 1 | WF007 | needs_input | needs_input | ✅ |
| WF008-excel-test | 1 | WF008 | completed | completed | ✅ |
| WF009-excel-test | 1 | WF009 | completed | completed | ✅ |
| WF009-described-task | 1 | WF009 | completed | completed | ✅ |
| WF009-escalation | 1 | WF009 | escalated | escalated | ✅ |
| WF010-excel-test | 1 | WF010 | completed | completed | ✅ |
| WF010-custom-threshold | 1 | WF010 | completed | completed | ✅ |
| out-of-scope | 1 | - | no_match | no_match | ✅ |
| WF010-live-agent-logs | 1 | WF010 | completed | completed | ✅ |

---
## WF001-excel-test

### Request
> Which products need restocking?

**Selected workflow:** `WF001` - Inventory Restock Check  
**Routing:** offline-lexical, confidence 0.85 - Best lexical match to 'Inventory Restock Check' (score 0.48 vs next 0.11); shared terms: need, product, restock.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 9 ms  
**Extracted parameters:** `{"inventory_path": "data/inventory.csv"}`


**Steps executed:**

1. ✔ **Load inventory** (`load_table`, 0 ms) - Loaded 12 rows from inventory.csv (columns: sku, product_name, category, current_stock, minimum_stock, case_pack, supplier)
2. ✔ **Compare current stock with minimum threshold** (`compute_columns`, 0 ms) - Computed threshold, shortfall for 12 rows
    - ↳ threshold = user override if given, else product minimum_stock; shortfall = threshold - current_stock
3. ✔ **Identify low-stock products** (`filter_rows`, 0 ms) - 6 of 12 products matched: current_stock < threshold
    - ↳ Rule `current_stock < threshold` -> 6 products selected
4. ✔ **Calculate reorder quantity** (`compute_columns`, 0 ms) - Computed target_stock, suggested_reorder_qty for 6 rows
    - ↳ reorder qty = (threshold x 2) - current stock, rounded up to the supplier case pack
5. ✔ **Generate restock list** (`filter_rows`, 0 ms) - 6 of 6 restock lines matched: suggested_reorder_qty > 0
    - ↳ Rule `suggested_reorder_qty > 0` -> 6 restock lines selected

#### Result: Restock list
6 of 12 products are below their minimum stock threshold and need restocking.

**Products checked:** 12 · **Products to restock:** 6

**Products requiring restock**

| sku | product_name | current_stock | threshold | shortfall | suggested_reorder_qty | supplier |
|---|---|---|---|---|---|---|
| SKU-1001 | Merino Wool Crew Sweater | 4 | 20 | 16 | 36 | WoolWorks Ltd |
| SKU-1004 | Leather Chelsea Boots | 0 | 10 | 10 | 20 | StepRight |
| SKU-1003 | Slim Fit Chino Trousers | 18 | 25 | 7 | 36 | UrbanTailor |
| SKU-1007 | Cashmere Beanie | 7 | 12 | 5 | 20 | WoolWorks Ltd |
| SKU-1012 | Wool Blend Overcoat | 3 | 8 | 5 | 14 | NorthPeak |
| SKU-1009 | Denim Trucker Jacket | 9 | 10 | 1 | 12 | UrbanTailor |

> Rule: current_stock < minimum_stock (a product exactly AT its minimum is not flagged).  

Files written: `outputs/files/restock_list.csv`


---
## WF001-custom-threshold

### Request
> Check today's inventory and identify products below 20 units that need restocking.

**Selected workflow:** `WF001` - Inventory Restock Check  
**Routing:** offline-lexical, confidence 0.92 - Best lexical match to 'Inventory Restock Check' (score 0.60 vs next 0.08); shared terms: check, inventory, need, product, restock.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 5 ms  
**Extracted parameters:** `{"inventory_path": "data/inventory.csv", "threshold_override": 20}`


**Steps executed:**

1. ✔ **Load inventory** (`load_table`, 0 ms) - Loaded 12 rows from inventory.csv (columns: sku, product_name, category, current_stock, minimum_stock, case_pack, supplier)
2. ✔ **Compare current stock with minimum threshold** (`compute_columns`, 0 ms) - Computed threshold, shortfall for 12 rows
    - ↳ threshold = user override if given, else product minimum_stock; shortfall = threshold - current_stock
3. ✔ **Identify low-stock products** (`filter_rows`, 0 ms) - 7 of 12 products matched: current_stock < threshold
    - ↳ Rule `current_stock < threshold` -> 7 products selected
4. ✔ **Calculate reorder quantity** (`compute_columns`, 0 ms) - Computed target_stock, suggested_reorder_qty for 7 rows
    - ↳ reorder qty = (threshold x 2) - current stock, rounded up to the supplier case pack
5. ✔ **Generate restock list** (`filter_rows`, 0 ms) - 7 of 7 restock lines matched: suggested_reorder_qty > 0
    - ↳ Rule `suggested_reorder_qty > 0` -> 7 restock lines selected

#### Result: Restock list
7 of 12 products are below their minimum stock threshold and need restocking.

**Products checked:** 12 · **Products to restock:** 7

**Products requiring restock**

| sku | product_name | current_stock | threshold | shortfall | suggested_reorder_qty | supplier |
|---|---|---|---|---|---|---|
| SKU-1004 | Leather Chelsea Boots | 0 | 20 | 20 | 40 | StepRight |
| SKU-1012 | Wool Blend Overcoat | 3 | 20 | 17 | 38 | NorthPeak |
| SKU-1001 | Merino Wool Crew Sweater | 4 | 20 | 16 | 36 | WoolWorks Ltd |
| SKU-1007 | Cashmere Beanie | 7 | 20 | 13 | 40 | WoolWorks Ltd |
| SKU-1009 | Denim Trucker Jacket | 9 | 20 | 11 | 32 | UrbanTailor |
| SKU-1006 | Linen Button-Down Shirt | 15 | 20 | 5 | 30 | GreenThreads |
| SKU-1003 | Slim Fit Chino Trousers | 18 | 20 | 2 | 24 | UrbanTailor |

> Rule: current_stock < minimum_stock (a product exactly AT its minimum is not flagged).  

Files written: `outputs/files/restock_list.csv`


---
## WF002-excel-test

### Request
> Find products where vendor price differs by more than 10%.

**Selected workflow:** `WF002` - Product Price Validation  
**Routing:** offline-lexical, confidence 0.82 - Best lexical match to 'Product Price Validation' (score 0.68 vs next 0.21); shared terms: differ, price, product, vendor.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 6 ms  
**Extracted parameters:** `{"tolerance_pct": 10.0}`


**Steps executed:**

1. ✔ **Load product prices** (`load_tables`, 0 ms) - internal: 12 rows; vendor: 12 rows
2. ✔ **Match products by SKU** (`join_tables`, 0 ms) - 11 matched on sku; 1 only internal; 1 only vendor
    - ↳ Keys normalised (trim/upper-case) before matching
3. ✔ **Compare internal and vendor prices** (`compute_columns`, 0 ms) - Computed price_difference for 11 rows
    - ↳ price_difference = round(price - vendor_price, 2)
4. ✔ **Calculate percentage difference** (`compute_columns`, 0 ms) - Computed pct_difference for 11 rows
    - ↳ pct_difference = (internal - vendor) / vendor x 100
5. ✔ **Flag exceptions** (`compute_columns`, 0 ms) - Computed tolerance_used, is_exception, flag for 11 rows
    - ↳ Rule: |pct_difference| > tolerance (10% by default) -> exception

#### Result: Price validation report
11 products matched by SKU; exceptions are price differences above 10.0%.

**Products matched:** 11 · **Tolerance %:** 10.0 · **Unmatched internal SKUs:** 1 · **Vendor-only SKUs:** 1

**Exceptions (difference exceeds tolerance)**

| SKU | Product | Internal $ | Vendor $ | Diff $ | Diff % |
|---|---|---|---|---|---|
| SKU-1009 | Denim Trucker Jacket | 99.0 | 85.0 | 14.0 | 16.47 |
| SKU-1002 | Organic Cotton T-Shirt | 24.0 | 21.0 | 3.0 | 14.29 |
| SKU-1004 | Leather Chelsea Boots | 149.0 | 131.0 | 18.0 | 13.74 |
| SKU-1007 | Cashmere Beanie | 45.0 | 52.0 | -7.0 | -13.46 |

**All matched products**

| sku | product_name | price | vendor_price | pct_difference | flag |
|---|---|---|---|---|---|
| SKU-1001 | Merino Wool Crew Sweater | 89.0 | 92.5 | -3.78 | ok |
| SKU-1002 | Organic Cotton T-Shirt | 24.0 | 21.0 | 14.29 | EXCEPTION |
| SKU-1003 | Slim Fit Chino Trousers | 59.0 | 58.0 | 1.72 | ok |
| SKU-1004 | Leather Chelsea Boots | 149.0 | 131.0 | 13.74 | EXCEPTION |
| SKU-1005 | Quilted Puffer Jacket | 129.0 | 129.0 | 0.0 | ok |
| SKU-1006 | Linen Button-Down Shirt | 55.0 | 50.0 | 10.0 | ok |
| SKU-1007 | Cashmere Beanie | 45.0 | 52.0 | -13.46 | EXCEPTION |
| SKU-1008 | Canvas Tote Bag | 19.0 | 19.5 | -2.56 | ok |
| SKU-1009 | Denim Trucker Jacket | 99.0 | 85.0 | 16.47 | EXCEPTION |
| SKU-1010 | Running Sneakers | 110.0 | 112.0 | -1.79 | ok |
| SKU-1011 | Silk Scarf | 65.0 | 66.0 | -1.52 | ok |

**Not matched (internal SKU missing from vendor list)**

| sku | product_name | price |
|---|---|---|
| SKU-1012 | Wool Blend Overcoat | 219.0 |

**Not matched (vendor SKU not in internal catalogue)**

| vendor_sku | vendor_price |
|---|---|
| SKU-2001 | 30.0 |


Files written: `outputs/files/price_validation.csv`


---
## WF002-custom-tolerance

### Request
> Validate our product prices against the vendor list using a 15% tolerance.

**Selected workflow:** `WF002` - Product Price Validation  
**Routing:** offline-lexical, confidence 0.77 - Best lexical match to 'Product Price Validation' (score 0.52 vs next 0.20); shared terms: list, pric, product, validate, vendor.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 5 ms  
**Extracted parameters:** `{"tolerance_pct": 15.0}`


**Steps executed:**

1. ✔ **Load product prices** (`load_tables`, 0 ms) - internal: 12 rows; vendor: 12 rows
2. ✔ **Match products by SKU** (`join_tables`, 0 ms) - 11 matched on sku; 1 only internal; 1 only vendor
    - ↳ Keys normalised (trim/upper-case) before matching
3. ✔ **Compare internal and vendor prices** (`compute_columns`, 0 ms) - Computed price_difference for 11 rows
    - ↳ price_difference = round(price - vendor_price, 2)
4. ✔ **Calculate percentage difference** (`compute_columns`, 0 ms) - Computed pct_difference for 11 rows
    - ↳ pct_difference = (internal - vendor) / vendor x 100
5. ✔ **Flag exceptions** (`compute_columns`, 0 ms) - Computed tolerance_used, is_exception, flag for 11 rows
    - ↳ Rule: |pct_difference| > tolerance (10% by default) -> exception

#### Result: Price validation report
11 products matched by SKU; exceptions are price differences above 15.0%.

**Products matched:** 11 · **Tolerance %:** 15.0 · **Unmatched internal SKUs:** 1 · **Vendor-only SKUs:** 1

**Exceptions (difference exceeds tolerance)**

| SKU | Product | Internal $ | Vendor $ | Diff $ | Diff % |
|---|---|---|---|---|---|
| SKU-1009 | Denim Trucker Jacket | 99.0 | 85.0 | 14.0 | 16.47 |

**All matched products**

| sku | product_name | price | vendor_price | pct_difference | flag |
|---|---|---|---|---|---|
| SKU-1001 | Merino Wool Crew Sweater | 89.0 | 92.5 | -3.78 | ok |
| SKU-1002 | Organic Cotton T-Shirt | 24.0 | 21.0 | 14.29 | ok |
| SKU-1003 | Slim Fit Chino Trousers | 59.0 | 58.0 | 1.72 | ok |
| SKU-1004 | Leather Chelsea Boots | 149.0 | 131.0 | 13.74 | ok |
| SKU-1005 | Quilted Puffer Jacket | 129.0 | 129.0 | 0.0 | ok |
| SKU-1006 | Linen Button-Down Shirt | 55.0 | 50.0 | 10.0 | ok |
| SKU-1007 | Cashmere Beanie | 45.0 | 52.0 | -13.46 | ok |
| SKU-1008 | Canvas Tote Bag | 19.0 | 19.5 | -2.56 | ok |
| SKU-1009 | Denim Trucker Jacket | 99.0 | 85.0 | 16.47 | EXCEPTION |
| SKU-1010 | Running Sneakers | 110.0 | 112.0 | -1.79 | ok |
| SKU-1011 | Silk Scarf | 65.0 | 66.0 | -1.52 | ok |

**Not matched (internal SKU missing from vendor list)**

| sku | product_name | price |
|---|---|---|
| SKU-1012 | Wool Blend Overcoat | 219.0 |

**Not matched (vendor SKU not in internal catalogue)**

| vendor_sku | vendor_price |
|---|---|
| SKU-2001 | 30.0 |


Files written: `outputs/files/price_validation.csv`


---
## WF003-excel-test

_Attachments: data/vendor_files/vendor_acme_products.xlsx_

### Request
> Process this vendor spreadsheet and show invalid rows.

**Selected workflow:** `WF003` - Vendor File Processing  
**Routing:** offline-lexical, confidence 0.86 - Best lexical match to 'Vendor File Processing' (score 0.47 vs next 0.09); shared terms: invalid, proces, row, spreadsheet, vendor.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 11 ms  
**Extracted parameters:** `{"file_path": "data/vendor_files/vendor_acme_products.xlsx"}`


**Steps executed:**

1. ✔ **Read file** (`load_table`, 5 ms) - Loaded 8 rows from vendor_acme_products.xlsx (columns: Item Code,  Product Title , Unit Price ($), Qty Available, Colour, Category)
2. ✔ **Detect columns** (`detect_columns`, 0 ms) - Detected: 'Item Code'→sku, 'Product Title'→product_name, 'Unit Price ($)'→price, 'Qty Available'→quantity, 'Colour'→color, 'Category'→category
3. ✔ **Normalize column names** (`normalize_columns`, 0 ms) - Normalised 8 rows to columns: sku, product_name, price, quantity, color, category
    - ↳ Whitespace trimmed; SKUs upper-cased
4. ✔ **Validate required fields** (`annotate_errors`, 0 ms) - Validated 8 rows against 2 rule(s)
    - ↳ Missing SKU: 2 row(s)
    - ↳ Missing product name: 2 row(s)
5. ✔ **Identify invalid rows** (`partition_rows`, 0 ms) - 3 invalid, 5 valid
    - ↳ Rule `len(_errors) > 0` -> 3 invalid
6. ✔ **Produce cleaned dataset** (`export_table`, 0 ms) - Exported 5 rows to outputs/files/vendor_acme_products_cleaned.csv

#### Result: Vendor file processing
8 rows read from data/vendor_files/vendor_acme_products.xlsx: 5 valid, 3 invalid (missing SKU or product name).

**Rows read:** 8 · **Valid rows:** 5 · **Invalid rows:** 3

**Column mapping detected**

- **Item Code**: sku
- ** Product Title **: product_name
- **Unit Price ($)**: price
- **Qty Available**: quantity
- **Colour**: color
- **Category**: category

**Invalid rows**

| Source row | SKU | Product name | Price | Errors |
|---|---|---|---|---|
| 4 |  | Corduroy Overshirt | 72 | Missing SKU |
| 5 | AC-504 |  | 35 | Missing product name |
| 7 |  |  | 15 | Missing SKU; Missing product name |

**Cleaned dataset**

| sku | product_name | price | quantity | color | category |
|---|---|---|---|---|---|
| AC-501 | Waxed Cotton Field Jacket | 140 | 25 | Olive | Outerwear |
| AC-502 | Ribbed Wool Socks (3-pack) | 18.5 | 200 | Grey | Accessories |
| AC-505 | Suede Desert Boots | 120 | 30 | Sand | Footwear |
| AC-507 | Heavyweight Hoodie | 59.9 | 80 | Black | Tops |
| AC-508 | Packable Rain Shell | N/A | 45 | Yellow | Outerwear |

> Per the decision logic only a missing SKU or product name makes a row invalid; other issues (e.g. non-numeric price) are kept.  

Files written: `outputs/files/vendor_acme_products_cleaned.csv`, `outputs/files/vendor_acme_products_invalid_rows.csv`


---
## WF003-no-file-attached

### Request
> Process this vendor spreadsheet and show invalid rows.

**Selected workflow:** `WF003` - Vendor File Processing  
**Routing:** offline-lexical, confidence 0.86 - Best lexical match to 'Vendor File Processing' (score 0.47 vs next 0.09); shared terms: invalid, proces, row, spreadsheet, vendor.  
**Status:** `NEEDS_INPUT` · LLM mode: `offline-fallback` · 2 ms  

**Steps executed:**

1. ⏸ **Read file** (`load_table`, 0 ms) - Please attach the vendor file (CSV or XLSX) you want me to process.
    - ↳ No file provided -> asking user

**Agent needs more information:** Please attach the vendor file (CSV or XLSX) you want me to process.



---
## WF003-csv-different-headers

_Attachments: data/vendor_files/vendor_globex_products.csv_

### Request
> Process this vendor file and give me the cleaned dataset.

**Selected workflow:** `WF003` - Vendor File Processing  
**Routing:** offline-lexical, confidence 0.91 - Best lexical match to 'Vendor File Processing' (score 0.71 vs next 0.11); shared terms: clean, file, proces, vendor.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 5 ms  
**Extracted parameters:** `{"file_path": "data/vendor_files/vendor_globex_products.csv"}`


**Steps executed:**

1. ✔ **Read file** (`load_table`, 0 ms) - Loaded 4 rows from vendor_globex_products.csv (columns: Vendor SKU, Name, Cost, Stock, Color)
2. ✔ **Detect columns** (`detect_columns`, 0 ms) - Detected: 'Vendor SKU'→sku, 'Name'→product_name, 'Cost'→price, 'Stock'→quantity, 'Color'→color
3. ✔ **Normalize column names** (`normalize_columns`, 0 ms) - Normalised 4 rows to columns: sku, product_name, price, quantity, color
    - ↳ Whitespace trimmed; SKUs upper-cased
4. ✔ **Validate required fields** (`annotate_errors`, 0 ms) - Validated 4 rows against 2 rule(s)
    - ↳ Missing SKU: 1 row(s)
    - ↳ Missing product name: 1 row(s)
5. ✔ **Identify invalid rows** (`partition_rows`, 0 ms) - 2 invalid, 2 valid
    - ↳ Rule `len(_errors) > 0` -> 2 invalid
6. ✔ **Produce cleaned dataset** (`export_table`, 0 ms) - Exported 2 rows to outputs/files/vendor_globex_products_cleaned.csv

#### Result: Vendor file processing
4 rows read from data/vendor_files/vendor_globex_products.csv: 2 valid, 2 invalid (missing SKU or product name).

**Rows read:** 4 · **Valid rows:** 2 · **Invalid rows:** 2

**Column mapping detected**

- **Vendor SKU**: sku
- **Name**: product_name
- **Cost**: price
- **Stock**: quantity
- **Color**: color

**Invalid rows**

| Source row | SKU | Product name | Price | Errors |
|---|---|---|---|---|
| 4 |  | Fleece Neck Gaiter | 15.0 | Missing SKU |
| 5 | GX-04 |  | 22.0 | Missing product name |

**Cleaned dataset**

| sku | product_name | price | quantity | color | category |
|---|---|---|---|---|---|
| GX-01 | Merino Base Layer | 54.0 | 120 | Black |  |
| GX-02 | Thermal Leggings | 39.0 | 80 | Navy |  |

> Per the decision logic only a missing SKU or product name makes a row invalid; other issues (e.g. non-numeric price) are kept.  

Files written: `outputs/files/vendor_globex_products_cleaned.csv`, `outputs/files/vendor_globex_products_invalid_rows.csv`


---
## WF003-error-unrecognised-format

_Attachments: data/vendor_files/vendor_bad_format.csv_

### Request
> Process this vendor spreadsheet and show invalid rows.

**Selected workflow:** `WF003` - Vendor File Processing  
**Routing:** offline-lexical, confidence 0.86 - Best lexical match to 'Vendor File Processing' (score 0.47 vs next 0.09); shared terms: invalid, proces, row, spreadsheet, vendor.  
**Status:** `FAILED` · LLM mode: `offline-fallback` · 3 ms  
**Extracted parameters:** `{"file_path": "data/vendor_files/vendor_bad_format.csv"}`


**Steps executed:**

1. ✔ **Read file** (`load_table`, 0 ms) - Loaded 1 rows from vendor_bad_format.csv (columns: foo, bar)
2. ✘ **Detect columns** (`detect_columns`, 0 ms) - Failed: Could not detect required column(s) ['sku', 'product_name'] in headers ['foo', 'bar']. Add the header name to the aliases in config/workflow_bindings.yaml.

**Workflow failed:** Step 2 'Detect columns' failed: Could not detect required column(s) ['sku', 'product_name'] in headers ['foo', 'bar']. Add the header name to the aliases in config/workflow_bindings.yaml.



---
## WF004-excel-test-no-product

### Request
> Generate SEO content for this product.

**Selected workflow:** `WF004` - Product Description Generator  
**Routing:** offline-lexical, confidence 0.81 - Best lexical match to 'Product Description Generator' (score 0.47 vs next 0.13); shared terms: content, generate, product, seo.  
**Status:** `NEEDS_INPUT` · LLM mode: `offline-fallback` · 3 ms  

**Steps executed:**

1. ⏸ **Validate required attributes** (`validate_params`, 0 ms) - Missing required input: product name, category. Please share at least the product name and category (plus material, colour, attributes and target audience if available) - I won't invent missing details.
    - ↳ Required inputs missing or invalid -> asking user before continuing

**Agent needs more information:** Missing required input: product name, category. Please share at least the product name and category (plus material, colour, attributes and target audience if available) - I won't invent missing details.



---
## WF004-excel-test-with-product

_Attachments: examples/attachments/product_wool_coat.json_

### Request
> Generate SEO content for this product.

**Selected workflow:** `WF004` - Product Description Generator  
**Routing:** offline-lexical, confidence 0.81 - Best lexical match to 'Product Description Generator' (score 0.47 vs next 0.13); shared terms: content, generate, product, seo.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 5 ms  
**Extracted parameters:** `{"product_name": "Wool Blend Overcoat", "category": "Outerwear", "attributes": ["single-breasted", "notch lapel", "two flap pockets", "knee length"], "color": "camel", "target_audience": "men who commute in cold cities"}`


**Steps executed:**

1. ✔ **Validate required attributes** (`validate_params`, 0 ms) - Inputs valid; 1 optional field(s) missing
    - ↳ All required inputs present: product name, category
    - ↳ Optional inputs missing (will be marked, not invented): material
2. ✔ **Create product description** (`llm_generate`, 0 ms) - Generated description (206 chars)
    - ↳ No LLM configured -> deterministic template fallback used
    - ↳ Missing information explicitly marked in: description
3. ✔ **Generate short description** (`llm_generate`, 0 ms) - Generated short_description (92 chars)
    - ↳ No LLM configured -> deterministic template fallback used
    - ↳ Missing information explicitly marked in: short_description
4. ✔ **Generate SEO title** (`llm_generate`, 0 ms) - Generated seo_title (39 chars)
    - ↳ No LLM configured -> deterministic template fallback used
5. ✔ **Generate meta description** (`llm_generate`, 0 ms) - Generated meta_description (110 chars)
    - ↳ No LLM configured -> deterministic template fallback used
    - ↳ Missing information explicitly marked in: meta_description

#### Result: Product content
Content generated for 'Wool Blend Overcoat'.

**Missing attributes:** 1

**Product description**

The Wool Blend Overcoat is an outerwear piece in camel, made from [MISSING: material]. Key features: single-breasted, notch lapel, two flap pockets, knee length. Designed for men who commute in cold cities.

**Short description**

Camel Wool Blend Overcoat in [MISSING: material], featuring single-breasted and notch lapel.

**SEO title**

Wool Blend Overcoat - Camel | Outerwear

**Meta description**

Shop the Wool Blend Overcoat: [MISSING: material] outerwear in camel. Made for men who commute in cold cities.

**Missing information (marked, not invented)**

- material



---
## WF004-text-only-followup

#### Turn 1
### Request
> Generate SEO content for this product.

**Selected workflow:** `WF004` - Product Description Generator  
**Routing:** offline-lexical, confidence 0.81 - Best lexical match to 'Product Description Generator' (score 0.47 vs next 0.13); shared terms: content, generate, product, seo.  
**Status:** `NEEDS_INPUT` · LLM mode: `offline-fallback` · 2 ms  

**Steps executed:**

1. ⏸ **Validate required attributes** (`validate_params`, 0 ms) - Missing required input: product name, category. Please share at least the product name and category (plus material, colour, attributes and target audience if available) - I won't invent missing details.
    - ↳ Required inputs missing or invalid -> asking user before continuing

**Agent needs more information:** Missing required input: product name, category. Please share at least the product name and category (plus material, colour, attributes and target audience if available) - I won't invent missing details.


#### Turn 2
### Request
> name: Silk Scarf; category: Accessories; colour: emerald; features: hand-rolled edges, 90x90 cm

**Selected workflow:** `WF004` - Product Description Generator  
**Routing:** pending-followup, confidence 0.90 - Treated message as an answer to the pending 'Product Description Generator' question.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 4 ms  
**Extracted parameters:** `{"product_name": "Silk Scarf", "category": "Accessories", "attributes": ["hand-rolled edges", "90x90 cm"], "color": "emerald"}`


**Steps executed:**

1. ✔ **Validate required attributes** (`validate_params`, 0 ms) - Inputs valid; 2 optional field(s) missing
    - ↳ All required inputs present: product name, category
    - ↳ Optional inputs missing (will be marked, not invented): material, target audience
2. ✔ **Create product description** (`llm_generate`, 0 ms) - Generated description (165 chars)
    - ↳ No LLM configured -> deterministic template fallback used
    - ↳ Missing information explicitly marked in: description
3. ✔ **Generate short description** (`llm_generate`, 0 ms) - Generated short_description (84 chars)
    - ↳ No LLM configured -> deterministic template fallback used
    - ↳ Missing information explicitly marked in: short_description
4. ✔ **Generate SEO title** (`llm_generate`, 0 ms) - Generated seo_title (34 chars)
    - ↳ No LLM configured -> deterministic template fallback used
5. ✔ **Generate meta description** (`llm_generate`, 0 ms) - Generated meta_description (101 chars)
    - ↳ No LLM configured -> deterministic template fallback used
    - ↳ Missing information explicitly marked in: meta_description

#### Result: Product content
Content generated for 'Silk Scarf'.

**Missing attributes:** 2

**Product description**

The Silk Scarf is an accessories piece in emerald, made from [MISSING: material]. Key features: hand-rolled edges, 90x90 cm. Designed for [MISSING: target_audience].

**Short description**

Emerald Silk Scarf in [MISSING: material], featuring hand-rolled edges and 90x90 cm.

**SEO title**

Silk Scarf - Emerald | Accessories

**Meta description**

Shop the Silk Scarf: [MISSING: material] accessories in emerald. Made for [MISSING: target_audience].

**Missing information (marked, not invented)**

- material
- target_audience



---
## WF004-inline-product

_Attachments: examples/attachments/product_chelsea_boots.json_

### Request
> Write a product description, SEO title and meta description for the Leather Chelsea Boots.

**Selected workflow:** `WF004` - Product Description Generator  
**Routing:** offline-lexical, confidence 0.94 - Best lexical match to 'Product Description Generator' (score 0.83 vs next 0.08); shared terms: description, meta, product, seo, title, write.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 4 ms  
**Extracted parameters:** `{"product_name": "Leather Chelsea Boots", "category": "Footwear", "attributes": ["elastic side panels", "pull tab", "stacked heel", "Goodyear-welted sole"], "material": "full-grain leather", "color": "brown", "target_audience": "men looking for versatile smart-casual boots"}`


**Steps executed:**

1. ✔ **Validate required attributes** (`validate_params`, 0 ms) - Inputs valid; 0 optional field(s) missing
    - ↳ All required inputs present: product name, category
2. ✔ **Create product description** (`llm_generate`, 0 ms) - Generated description (225 chars)
    - ↳ No LLM configured -> deterministic template fallback used
3. ✔ **Generate short description** (`llm_generate`, 0 ms) - Generated short_description (94 chars)
    - ↳ No LLM configured -> deterministic template fallback used
4. ✔ **Generate SEO title** (`llm_generate`, 0 ms) - Generated seo_title (40 chars)
    - ↳ No LLM configured -> deterministic template fallback used
5. ✔ **Generate meta description** (`llm_generate`, 0 ms) - Generated meta_description (124 chars)
    - ↳ No LLM configured -> deterministic template fallback used

#### Result: Product content
Content generated for 'Leather Chelsea Boots'.

**Missing attributes:** 0

**Product description**

The Leather Chelsea Boots is a footwear piece in brown, made from full-grain leather. Key features: elastic side panels, pull tab, stacked heel, Goodyear-welted sole. Designed for men looking for versatile smart-casual boots.

**Short description**

Brown Leather Chelsea Boots in full-grain leather, featuring elastic side panels and pull tab.

**SEO title**

Leather Chelsea Boots - Brown | Footwear

**Meta description**

Shop the Leather Chelsea Boots: full-grain leather footwear in brown. Made for men looking for versatile smart-casual boots.



---
## WF005-excel-test

### Request
> Where is order ORD-1001?

**Selected workflow:** `WF005` - Customer Order Status  
**Routing:** offline-lexical, confidence 1.00 - Best lexical match to 'Customer Order Status' (score 0.60 vs next 0.00); shared terms: order.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 107 ms  
**Extracted parameters:** `{"order_id": "ORD-1001"}`


**Steps executed:**

1. ✔ **Validate identifier** (`validate_identifier`, 0 ms) - Valid order ID ORD-1001
    - ↳ Identifier type: order ID
2. ✔ **Search order data** (`order_lookup`, 50 ms) - Order API returned 1 order(s) for ORD-1001
    - ↳ Matched by order_id
3. ✔ **Retrieve order status** (`extract_order_status`, 0 ms) - ORD-1001: Shipped
4. ✔ **Retrieve shipment information** (`shipment_lookup`, 51 ms) - Shipment info retrieved for 1 of 1 order(s)
5. ✔ **Summarize current status** (`summarize_order_status`, 0 ms) - Summarised 1 order(s)

#### Result: Order status
1 order(s) found.

**Summary**

- Order ORD-1001 (placed 2026-09-28) is **Shipped** - 1 x Merino Wool Crew Sweater, 2 x Cashmere Beanie. Shipped with BlueDart, tracking BD123456789IN: In transit (last seen Mumbai Hub), estimated delivery 2026-10-08.

**Order details**

| order_id | order_date | status | items | total | carrier | tracking_number | shipment_status | estimated_delivery |
|---|---|---|---|---|---|---|---|---|
| ORD-1001 | 2026-09-28 | Shipped | 1 x Merino Wool Crew Sweater, 2 x Cashmere Beanie | 179.0 | BlueDart | BD123456789IN | In transit | 2026-10-08 |



---
## WF005-not-found-then-email

#### Turn 1
### Request
> Where is order ORD-9999?

**Selected workflow:** `WF005` - Customer Order Status  
**Routing:** offline-lexical, confidence 1.00 - Best lexical match to 'Customer Order Status' (score 0.60 vs next 0.00); shared terms: order.  
**Status:** `NEEDS_INPUT` · LLM mode: `offline-fallback` · 55 ms  
**Extracted parameters:** `{"order_id": "ORD-9999"}`


**Steps executed:**

1. ✔ **Validate identifier** (`validate_identifier`, 0 ms) - Valid order ID ORD-9999
    - ↳ Identifier type: order ID
2. ⏸ **Search order data** (`order_lookup`, 50 ms) - No order found for order id 'ORD-9999'. Please provide another identifier - a different order ID or the email used at checkout.
    - ↳ No order found -> asking for another identifier

**Agent needs more information:** No order found for order id 'ORD-9999'. Please provide another identifier - a different order ID or the email used at checkout.


#### Turn 2
### Request
> Try priya.sharma@example.com instead

**Selected workflow:** `WF005` - Customer Order Status  
**Routing:** pending-followup, confidence 0.90 - Treated message as an answer to the pending 'Customer Order Status' question.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 158 ms  
**Extracted parameters:** `{"email": "priya.sharma@example.com"}`


**Steps executed:**

1. ✔ **Validate identifier** (`validate_identifier`, 0 ms) - Valid customer email priya.sharma@example.com
    - ↳ Identifier type: customer email
2. ✔ **Search order data** (`order_lookup`, 50 ms) - Order API returned 2 order(s) for priya.sharma@example.com
    - ↳ Matched by email
3. ✔ **Retrieve order status** (`extract_order_status`, 0 ms) - ORD-1001: Shipped; ORD-1003: Delivered
4. ✔ **Retrieve shipment information** (`shipment_lookup`, 101 ms) - Shipment info retrieved for 2 of 2 order(s)
5. ✔ **Summarize current status** (`summarize_order_status`, 0 ms) - Summarised 2 order(s)

#### Result: Order status
2 order(s) found.

**Summary**

- Order ORD-1001 (placed 2026-09-28) is **Shipped** - 1 x Merino Wool Crew Sweater, 2 x Cashmere Beanie. Shipped with BlueDart, tracking BD123456789IN: In transit (last seen Mumbai Hub), estimated delivery 2026-10-08.
- Order ORD-1003 (placed 2026-09-12) is **Delivered** - 3 x Organic Cotton T-Shirt. Shipped with Delhivery, tracking DL987654321IN: Delivered (last seen Pune), estimated delivery 2026-09-16.

**Order details**

| order_id | order_date | status | items | total | carrier | tracking_number | shipment_status | estimated_delivery |
|---|---|---|---|---|---|---|---|---|
| ORD-1001 | 2026-09-28 | Shipped | 1 x Merino Wool Crew Sweater, 2 x Cashmere Beanie | 179.0 | BlueDart | BD123456789IN | In transit | 2026-10-08 |
| ORD-1003 | 2026-09-12 | Delivered | 3 x Organic Cotton T-Shirt | 72.0 | Delhivery | DL987654321IN | Delivered | 2026-09-16 |



---
## WF005-processing-order

### Request
> What's the status of ORD-1002?

**Selected workflow:** `WF005` - Customer Order Status  
**Routing:** offline-lexical, confidence 1.00 - Best lexical match to 'Customer Order Status' (score 0.60 vs next 0.00); shared terms: statu.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 58 ms  
**Extracted parameters:** `{"order_id": "ORD-1002"}`


**Steps executed:**

1. ✔ **Validate identifier** (`validate_identifier`, 0 ms) - Valid order ID ORD-1002
    - ↳ Identifier type: order ID
2. ✔ **Search order data** (`order_lookup`, 50 ms) - Order API returned 1 order(s) for ORD-1002
    - ↳ Matched by order_id
3. ✔ **Retrieve order status** (`extract_order_status`, 0 ms) - ORD-1002: Processing
4. ✔ **Retrieve shipment information** (`shipment_lookup`, 0 ms) - Shipment info retrieved for 0 of 1 order(s)
    - ↳ ORD-1002: status Processing -> no shipment lookup needed
5. ✔ **Summarize current status** (`summarize_order_status`, 0 ms) - Summarised 1 order(s)

#### Result: Order status
1 order(s) found.

**Summary**

- Order ORD-1002 (placed 2026-10-03) is **Processing** - 1 x Leather Chelsea Boots. It has not shipped yet; tracking will be available once it ships.

**Order details**

| order_id | order_date | status | items | total | carrier | tracking_number | shipment_status | estimated_delivery |
|---|---|---|---|---|---|---|---|---|
| ORD-1002 | 2026-10-03 | Processing | 1 x Leather Chelsea Boots | 149.0 | - | - | Not shipped yet | - |



---
## WF005-api-outage-retry

_Environment: `{'SIMULATE_API_FAILURE': 'order_api:2'}`_

### Request
> Where is order ORD-1003?

**Selected workflow:** `WF005` - Customer Order Status  
**Routing:** offline-lexical, confidence 1.00 - Best lexical match to 'Customer Order Status' (score 0.60 vs next 0.00); shared terms: order.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 707 ms  
**Extracted parameters:** `{"order_id": "ORD-1003"}`


**Steps executed:**

1. ✔ **Validate identifier** (`validate_identifier`, 0 ms) - Valid order ID ORD-1003
    - ↳ Identifier type: order ID
2. ✔ **Search order data** (`order_lookup`, 651 ms) - Order API returned 1 order(s) for ORD-1003 _(attempts: 3)_
    - ↳ Attempt 1 failed (order_api unavailable (simulated 503 Service Unavailable)); retrying
    - ↳ Attempt 2 failed (order_api unavailable (simulated 503 Service Unavailable)); retrying
    - ↳ Matched by order_id
3. ✔ **Retrieve order status** (`extract_order_status`, 0 ms) - ORD-1003: Delivered
4. ✔ **Retrieve shipment information** (`shipment_lookup`, 50 ms) - Shipment info retrieved for 1 of 1 order(s)
5. ✔ **Summarize current status** (`summarize_order_status`, 0 ms) - Summarised 1 order(s)

#### Result: Order status
1 order(s) found.

**Summary**

- Order ORD-1003 (placed 2026-09-12) is **Delivered** - 3 x Organic Cotton T-Shirt. Shipped with Delhivery, tracking DL987654321IN: Delivered (last seen Pune), estimated delivery 2026-09-16.

**Order details**

| order_id | order_date | status | items | total | carrier | tracking_number | shipment_status | estimated_delivery |
|---|---|---|---|---|---|---|---|---|
| ORD-1003 | 2026-09-12 | Delivered | 3 x Organic Cotton T-Shirt | 72.0 | Delhivery | DL987654321IN | Delivered | 2026-09-16 |



---
## WF005-api-down

_Environment: `{'SIMULATE_API_FAILURE': 'order_api'}`_

### Request
> Where is order ORD-1001?

**Selected workflow:** `WF005` - Customer Order Status  
**Routing:** offline-lexical, confidence 1.00 - Best lexical match to 'Customer Order Status' (score 0.60 vs next 0.00); shared terms: order.  
**Status:** `FAILED` · LLM mode: `offline-fallback` · 605 ms  
**Extracted parameters:** `{"order_id": "ORD-1001"}`


**Steps executed:**

1. ✔ **Validate identifier** (`validate_identifier`, 0 ms) - Valid order ID ORD-1001
    - ↳ Identifier type: order ID
2. ✘ **Search order data** (`order_lookup`, 601 ms) - Failed: order_api unavailable (simulated 503 Service Unavailable) _(attempts: 3)_
    - ↳ Attempt 1 failed (order_api unavailable (simulated 503 Service Unavailable)); retrying
    - ↳ Attempt 2 failed (order_api unavailable (simulated 503 Service Unavailable)); retrying

**Workflow failed:** Step 2 'Search order data' failed: order_api unavailable (simulated 503 Service Unavailable)



---
## WF006-excel-test

### Request
> Find likely duplicate products in the catalog.

**Selected workflow:** `WF006` - Duplicate Product Detection  
**Routing:** offline-lexical, confidence 0.92 - Best lexical match to 'Duplicate Product Detection' (score 0.80 vs next 0.10); shared terms: catalog, duplicate, product.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 15 ms  
**Extracted parameters:** `{"catalog_path": "data/catalog.csv"}`


**Steps executed:**

1. ✔ **Load products** (`load_table`, 0 ms) - Loaded 14 rows from catalog.csv (columns: sku, product_name, brand, color, size, price)
2. ✔ **Normalize names/SKUs** (`normalize_products`, 0 ms) - Normalised 14 products (SKU upper/trim; names lower-cased, punctuation & synonyms unified)
3. ✔ **Compare identifiers** (`compare_identifiers`, 0 ms) - 2 exact-SKU pair(s) found
    - ↳ Rule: exact SKU match (after normalisation) = definite duplicate
4. ✔ **Compare product attributes** (`compare_attributes`, 7 ms) - 4 possible duplicate pair(s); 5 variant pair(s) and 1 low-score pair(s) rejected
    - ↳ Weighted score = {'name': 0.45, 'brand': 0.15, 'color': 0.15, 'size': 0.15, 'price': 0.1}; possible duplicate if ≥ 0.85
    - ↳ Variant, not duplicate: TS-1001 vs TS-1002: different size
    - ↳ Variant, not duplicate: ts-1001 vs TS-1002: different size
    - ↳ Variant, not duplicate: TS-1002 vs TS-2001: different size
    - ↳ Variant, not duplicate: JK-4001 vs JK-4002: different color
    - ↳ Variant, not duplicate: JK-4001 vs JK-4002: different color
5. ✔ **Group likely duplicates** (`group_duplicates`, 0 ms) - 4 duplicate group(s) covering 9 products
6. ✔ **Assign confidence** (`assign_confidence`, 0 ms) - G1=Definite + High, G2=Definite, G3=High, G4=High
    - ↳ Definite = exact SKU; High = attribute score ≥ 0.95; Medium = below. Mixed groups show both levels (e.g. 'Definite + High').

#### Result: Duplicate product groups
4 duplicate group(s) found among 14 catalogue products.

**Duplicate groups**

| group | confidence | score | skus | products | matching_fields | reason |
|---|---|---|---|---|---|---|
| G1 | Definite + High | 1.0 | TS-1001, ts-1001, TS-2001 | Classic Cotton T-Shirt - Black - M / Classic Cotton T-Shirt Black Medium / Classic Cotton Tshirt, Black, Medium | brand, color, price, price≈, product_name~, size, sku | Exact SKU match (TS-1001); name similarity 1.00; same brand, color, size |
| G2 | Definite | 1.0 | JK-4001, JK-4001 | Quilted Puffer Jacket Olive / Quilted Puffer Jacket Olive | brand, color, price, product_name, size, sku | Exact SKU match (JK-4001) |
| G3 | High | 1.0 | HD-3001, HD-3007 | Heavyweight Pullover Hoodie Grey / Heavyweight Pull-over Hoodie (Grey) | brand, color, price≈, product_name~, size | name similarity 1.00; same brand, color, size |
| G4 | High | 1.0 | BT-5001, BT-5101 | Leather Chelsea Boots Brown 42 / Chelsea Boots Leather, Brown, EU 42 | brand, color, price≈, product_name~, size | name similarity 1.00; same brand, color, size |

> Definite = exact SKU match (after trimming/upper-casing). High/Medium = possible duplicates from attribute similarity.  
> Products with a similar name but a different size or colour are treated as variants, not duplicates.  

Files written: `outputs/files/duplicate_groups.csv`


---
## WF007-excel-test-then-followup

#### Turn 1
### Request
> Create a campaign brief for the new collection.

**Selected workflow:** `WF007` - Marketing Campaign Brief  
**Routing:** offline-lexical, confidence 1.00 - Best lexical match to 'Marketing Campaign Brief' (score 0.69 vs next 0.00); shared terms: brief, campaign, collection, create.  
**Status:** `NEEDS_INPUT` · LLM mode: `offline-fallback` · 5 ms  

**Steps executed:**

1. ⏸ **Validate inputs** (`validate_params`, 0 ms) - Missing required input: campaign goal, start date, end date. Please provide the campaign goal and the start/end dates (e.g. 'Goal: drive launch sales, 2026-11-01 to 2026-11-30') and I'll generate the brief.
    - ↳ Required inputs missing or invalid -> asking user before continuing

**Agent needs more information:** Missing required input: campaign goal, start date, end date. Please provide the campaign goal and the start/end dates (e.g. 'Goal: drive launch sales, 2026-11-01 to 2026-11-30') and I'll generate the brief.


#### Turn 2
### Request
> Goal: drive launch sales of the autumn range, running 2026-11-01 to 2026-11-30, audience young professionals, promotion 15% off first order

**Selected workflow:** `WF007` - Marketing Campaign Brief  
**Routing:** pending-followup, confidence 0.90 - Treated message as an answer to the pending 'Marketing Campaign Brief' question.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 9 ms  
**Extracted parameters:** `{"campaign_goal": "drive launch sales of the autumn range", "start_date": "2026-11-01", "end_date": "2026-11-30", "collection": "autumn", "target_audience": "young professionals", "promotion": "15% off first order"}`


**Steps executed:**

1. ✔ **Validate inputs** (`validate_params`, 2 ms) - Inputs valid; 0 optional field(s) missing
    - ↳ All required inputs present: campaign goal, start date, end date
2. ✔ **Identify campaign objective** (`llm_generate`, 0 ms) - Generated objective_type (10 chars); objective (38 chars); primary_kpi (25 chars)
    - ↳ No LLM configured -> deterministic template fallback used
3. ✔ **Summarize products** (`select_campaign_products`, 0 ms) - 5 products (Accessories, Footwear, Knitwear, Outerwear), $45-$219
    - ↳ Collection 'autumn' resolved to 'Autumn 2026'
    - ↳ Products filtered by collection = Autumn 2026
4. ✔ **Create messaging** (`llm_generate`, 0 ms) - Generated key_message (114 chars); tagline (26 chars); supporting_points
    - ↳ No LLM configured -> deterministic template fallback used
5. ✔ **Create channel recommendations** (`llm_generate`, 0 ms) - Generated channel_recommendations
    - ↳ No LLM configured -> deterministic template fallback used
6. ✔ **Create campaign checklist** (`build_campaign_plan`, 0 ms) - 7 milestones, 8 checklist items, 30-day campaign

#### Result: Campaign brief
Campaign brief for 'drive launch sales of the autumn range' running 2026-11-01 to 2026-11-30.

**Objective**

- **objective type**: conversion
- **objective**: drive launch sales of the autumn range
- **primary kpi**: Revenue & conversion rate

**Target audience**

young professionals

**Product summary**

- **collection**: Autumn 2026
- **products**: 5
- **categories**: Accessories; Footwear; Knitwear; Outerwear
- **price range**: $45-$219

**Messaging**

- **key message**: Autumn 2026 is here: Merino Wool Crew Sweater, Leather Chelsea Boots, Quilted Puffer Jacket - 15% off first order.
- **tagline**: Autumn 2026, made to last.
- **supporting points**: Materials: cashmere, leather, merino wool, recycled nylon, wool blend; Audience: young professionals; Offer: 15% off first order

**Channels**

- Email + SMS with promotion
- Paid social retargeting
- Google Shopping / Performance Max
- Homepage hero banner

**Checklist**

- Confirm campaign goal, KPI and budget with stakeholders
- Verify product stock levels for featured products (see Inventory Restock workflow)
- Validate product prices before launch (see Price Validation workflow)
- Configure promotion in checkout: 15% off first order
- Produce creative for: Email + SMS with promotion, Paid social retargeting, Google Shopping / Performance Max, Homepage hero banner
- Legal/brand review of copy and claims
- Set up UTM tracking and analytics dashboard
- Schedule posts / emails / ads per timeline

**Featured products**

| sku | product_name | category | price | material | color |
|---|---|---|---|---|---|
| SKU-1001 | Merino Wool Crew Sweater | Knitwear | 89.0 | merino wool | charcoal |
| SKU-1004 | Leather Chelsea Boots | Footwear | 149.0 | leather | brown |
| SKU-1005 | Quilted Puffer Jacket | Outerwear | 129.0 | recycled nylon | olive |
| SKU-1007 | Cashmere Beanie | Accessories | 45.0 | cashmere | oatmeal |
| SKU-1012 | Wool Blend Overcoat | Outerwear | 219.0 | wool blend | camel |

**Timeline**

| milestone | date |
|---|---|
| Brief approved & assets requested | 2026-10-18 |
| Creative & copy final | 2026-10-25 |
| Channels scheduled, tracking (UTMs) tested | 2026-10-30 |
| Campaign launch | 2026-11-01 |
| Mid-campaign performance check | 2026-11-15 |
| Campaign end | 2026-11-30 |
| Post-campaign report | 2026-12-03 |



---
## WF007-named-products

### Request
> Create a campaign brief for SKU-1002 and SKU-1008. Goal: grow repeat purchases, 2026-11-10 to 2026-11-24

**Selected workflow:** `WF007` - Marketing Campaign Brief  
**Routing:** offline-lexical, confidence 1.00 - Best lexical match to 'Marketing Campaign Brief' (score 0.69 vs next 0.00); shared terms: brief, campaign, create, goal.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 6 ms  
**Extracted parameters:** `{"campaign_goal": "grow repeat purchases", "start_date": "2026-11-10", "end_date": "2026-11-24", "product_list": ["SKU-1002", "SKU-1008"]}`


**Steps executed:**

1. ✔ **Validate inputs** (`validate_params`, 0 ms) - Inputs valid; 2 optional field(s) missing
    - ↳ All required inputs present: campaign goal, start date, end date
    - ↳ Optional inputs missing (will be marked, not invented): target audience, promotion
2. ✔ **Identify campaign objective** (`llm_generate`, 0 ms) - Generated objective_type (10 chars); objective (21 chars); primary_kpi (25 chars)
    - ↳ No LLM configured -> deterministic template fallback used
3. ✔ **Summarize products** (`select_campaign_products`, 0 ms) - 2 products (Accessories, Tops), $19-$24
    - ↳ Products taken from the request: ['SKU-1002', 'SKU-1008']
4. ✔ **Create messaging** (`llm_generate`, 0 ms) - Generated key_message (64 chars); tagline (25 chars); supporting_points
    - ↳ No LLM configured -> deterministic template fallback used
5. ✔ **Create channel recommendations** (`llm_generate`, 0 ms) - Generated channel_recommendations
    - ↳ No LLM configured -> deterministic template fallback used
6. ✔ **Create campaign checklist** (`build_campaign_plan`, 0 ms) - 7 milestones, 8 checklist items, 15-day campaign

#### Result: Campaign brief
Campaign brief for 'grow repeat purchases' running 2026-11-10 to 2026-11-24.

**Objective**

- **objective type**: conversion
- **objective**: grow repeat purchases
- **primary kpi**: Revenue & conversion rate

**Product summary**

- **collection**: None
- **products**: 2
- **categories**: Accessories; Tops
- **price range**: $19-$24

**Messaging**

- **key message**: The collection is here: Organic Cotton T-Shirt, Canvas Tote Bag.
- **tagline**: New season, made to last.
- **supporting points**: Materials: canvas, organic cotton; Audience: [MISSING: target_audience]; Offer: [MISSING: promotion]

**Channels**

- Email + SMS with promotion
- Paid social retargeting
- Google Shopping / Performance Max
- Homepage hero banner

**Checklist**

- Confirm campaign goal, KPI and budget with stakeholders
- Verify product stock levels for featured products (see Inventory Restock workflow)
- Validate product prices before launch (see Price Validation workflow)
- Decide promotion (currently [MISSING: promotion])
- Produce creative for: Email + SMS with promotion, Paid social retargeting, Google Shopping / Performance Max, Homepage hero banner
- Legal/brand review of copy and claims
- Set up UTM tracking and analytics dashboard
- Schedule posts / emails / ads per timeline

**Missing inputs (marked TBD)**

- target_audience
- promotion

**Featured products**

| sku | product_name | category | price | material | color |
|---|---|---|---|---|---|
| SKU-1002 | Organic Cotton T-Shirt | Tops | 24.0 | organic cotton | white |
| SKU-1008 | Canvas Tote Bag | Accessories | 19.0 | canvas | natural |

**Timeline**

| milestone | date |
|---|---|
| Brief approved & assets requested | 2026-10-27 |
| Creative & copy final | 2026-11-03 |
| Channels scheduled, tracking (UTMs) tested | 2026-11-08 |
| Campaign launch | 2026-11-10 |
| Mid-campaign performance check | 2026-11-17 |
| Campaign end | 2026-11-24 |
| Post-campaign report | 2026-11-27 |



---
## WF007-invalid-dates

### Request
> Create a campaign brief. Goal: clear winter stock, from 2026-12-20 to 2026-12-01

**Selected workflow:** `WF007` - Marketing Campaign Brief  
**Routing:** offline-lexical, confidence 0.78 - Best lexical match to 'Marketing Campaign Brief' (score 0.61 vs next 0.23); shared terms: brief, campaign, create, goal.  
**Status:** `NEEDS_INPUT` · LLM mode: `offline-fallback` · 2 ms  
**Extracted parameters:** `{"campaign_goal": "clear winter stock", "start_date": "2026-12-20", "end_date": "2026-12-01"}`


**Steps executed:**

1. ⏸ **Validate inputs** (`validate_params`, 0 ms) - Start date (2026-12-20) must be before end date (2026-12-01). Please provide the campaign goal and the start/end dates (e.g. 'Goal: drive launch sales, 2026-11-01 to 2026-11-30') and I'll generate the brief.
    - ↳ Required inputs missing or invalid -> asking user before continuing

**Agent needs more information:** Start date (2026-12-20) must be before end date (2026-12-01). Please provide the campaign goal and the start/end dates (e.g. 'Goal: drive launch sales, 2026-11-01 to 2026-11-30') and I'll generate the brief.



---
## WF008-excel-test

### Request
> Classify these keywords and map them to pages.

**Selected workflow:** `WF008` - SEO Keyword Classification  
**Routing:** offline-lexical, confidence 1.00 - Best lexical match to 'SEO Keyword Classification' (score 0.59 vs next 0.00); shared terms: classify, keyword, map, pag.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 12 ms  
**Extracted parameters:** `{"keywords_path": "data/keywords.csv"}`


**Steps executed:**

1. ✔ **Read keywords** (`load_table`, 0 ms) - Loaded 24 rows from keywords.csv (columns: keyword, monthly_searches)
2. ✔ **Remove duplicates** (`dedupe_rows`, 0 ms) - 24 rows -> 22 unique (2 duplicates removed)
    - ↳ Duplicate key: norm_text(keyword)
    - ↳ Removed duplicate: Buy Merino Wool Sweater
    - ↳ Removed duplicate: how to wash merino wool
3. ✔ **Classify search intent** (`llm_classify`, 2 ms) - Labels: commercial=8, informational=4, navigational=3, transactional=7
    - ↳ No LLM configured -> rule-based classifier used
4. ✔ **Map keywords to categories** (`map_keyword_categories`, 2 ms) - Mapped 19 keywords to product categories; 3 brand/general
    - ↳ Transactional/commercial → category page; informational → guide/blog page; navigational → brand utility page
5. ✔ **Identify high-priority keywords** (`compute_columns`, 2 ms) - Computed priority for 22 rows
    - ↳ High = transactional ≥1,000 searches or commercial ≥2,500; Medium = ≥1,500 searches or buying intent; else Low
6. ✔ **Export results** (`export_table`, 0 ms) - Exported 22 rows to outputs/files/keyword_report.csv

#### Result: SEO keyword report
24 keywords read, 22 unique after de-duplication, classified and mapped to target pages.

**Keywords read:** 24 · **Unique keywords:** 22

**High-priority keywords**

| keyword | monthly_searches | intent | category | target_page |
|---|---|---|---|---|
| best puffer jacket 2026 | 8100 | commercial | Outerwear | /collections/outerwear |
| best running sneakers for flat feet | 6600 | commercial | Footwear | /collections/footwear |
| canvas tote bag | 4400 | commercial | Accessories | /collections/accessories |
| wool overcoat men | 3900 | commercial | Outerwear | /collections/outerwear |
| chelsea boots sale | 3600 | transactional | Footwear | /collections/footwear |
| running sneakers buy online | 2900 | transactional | Footwear | /collections/footwear |
| buy merino wool sweater | 2400 | transactional | Knitwear | /collections/knitwear |
| cheap chelsea boots men | 1300 | transactional | Footwear | /collections/footwear |
| organic cotton t-shirt price | 1000 | transactional | Tops | /collections/tops |

**All keywords**

| keyword | monthly_searches | intent | category | priority | target_page |
|---|---|---|---|---|---|
| best puffer jacket 2026 | 8100 | commercial | Outerwear | High | /collections/outerwear |
| best running sneakers for flat feet | 6600 | commercial | Footwear | High | /collections/footwear |
| how to wash merino wool | 5400 | informational | Knitwear | Medium | /blog/knitwear-care-guide |
| how to style chelsea boots | 4400 | informational | Footwear | Medium | /blog/footwear-style-guide |
| canvas tote bag | 4400 | commercial | Accessories | High | /collections/accessories |
| wool overcoat men | 3900 | commercial | Outerwear | High | /collections/outerwear |
| chelsea boots sale | 3600 | transactional | Footwear | High | /collections/footwear |
| silk scarf ways to tie | 3300 | informational | Accessories | Medium | /blog/accessories-styling |
| what is organic cotton | 2900 | informational | Tops | Medium | /blog/fabric-guide |
| running sneakers buy online | 2900 | transactional | Footwear | High | /collections/footwear |
| buy merino wool sweater | 2400 | transactional | Knitwear | High | /collections/knitwear |
| puffer jacket vs parka | 1900 | commercial | Outerwear | Medium | /collections/outerwear |
| top rated wool overcoats | 1700 | commercial | Outerwear | Medium | /collections/outerwear |
| northline returns policy | 1600 | navigational | General / Brand | Medium | /pages/returns-policy |
| linen shirt vs cotton shirt | 1500 | commercial | Tops | Medium | /collections/tops |
| cheap chelsea boots men | 1300 | transactional | Footwear | High | /collections/footwear |
| northline order tracking | 1200 | navigational | General / Brand | Low | /pages/order-tracking |
| organic cotton t-shirt price | 1000 | transactional | Tops | High | /collections/tops |
| northline store login | 900 | navigational | General / Brand | Low | /account/login |
| cashmere beanie review | 880 | commercial | Accessories | Medium | /collections/accessories |
| silk scarf discount code | 700 | transactional | Accessories | Medium | /collections/accessories |
| order linen button down shirt | 600 | transactional | Tops | Medium | /collections/tops |

> Full report exported to outputs/files/keyword_report.csv  


---
## WF009-excel-test

### Request
> Assign this urgent task to the best available developer.

**Selected workflow:** `WF009` - Employee Task Assignment  
**Routing:** offline-lexical, confidence 0.96 - Best lexical match to 'Employee Task Assignment' (score 0.55 vs next 0.04); shared terms: assign, available, best, developer, task.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 5 ms  
**Extracted parameters:** `{"priority": "urgent", "role": "Developer"}`


**Steps executed:**

1. ✔ **Understand task requirements** (`understand_task`, 0 ms) - TASK-301: 'Fix payment gateway timeout in checkout API' needs python, api, payments; priority urgent, deadline 2026-10-08
    - ↳ No description given -> the only open, unassigned urgent task in the task database was used: TASK-301
2. ✔ **Compare employee skills** (`compare_skills`, 0 ms) - Aarav Mehta 100%; Sneha Iyer 100%; Rohan Das 33%; Meera Nair 100%; Kabir Singh 33%
    - ↳ Role filter 'Developer': 5 of 8 employees
3. ✔ **Check current workload** (`check_workload`, 0 ms) - 3 of 5 have ≥ 8h free and are not on leave
4. ✔ **Rank candidates** (`rank_candidates`, 0 ms) - Ranking: Aarav Mehta (1.0) > Sneha Iyer (0.729) > Meera Nair (0.714) > Rohan Das (0.56)
    - ↳ Score = skills×0.6 + capacity×0.3 + seniority×0.1 (×1.5 for urgent); capacity = free hours / task hours (capped at 1)
5. ✔ **Select employee** (`select_employee`, 0 ms) - Selected Aarav Mehta (E-101)
    - ↳ Selected Aarav Mehta: skill match 100%, 10h free, senior
6. ✔ **Generate assignment summary** (`assignment_summary`, 0 ms) - Aarav Mehta (E-101, senior Developer)

#### Result: Task assignment
Recommendation: Aarav Mehta (E-101, senior Developer)

**Assignment summary**

- **recommended**: Aarav Mehta (E-101, senior Developer)
- **reasoning**: Has 3/3 required skills (api, payments, python) and 10h free this week (task needs 8h). Others not chosen: Sneha Iyer - only 2h free; Meera Nair - on leave; Rohan Das - skill match 33% < 67%.
- **priority**: urgent
- **deadline**: 2026-10-08
- **task summary**: TASK-301: Fix payment gateway timeout in checkout API
- **required skills**: python, api, payments
- **estimated hours**: 8.0

**Candidate ranking**

| rank | name | skill_match | matched_skills | available_hours | seniority | score | status |
|---|---|---|---|---|---|---|---|
| 1 | Aarav Mehta | 1.0 | api; payments; python | 10.0 | senior | 1.0 | ✔ suitable |
| 2 | Sneha Iyer | 1.0 | api; payments; python | 2.0 | mid | 0.73 | ✘ only 2h free |
| 3 | Meera Nair | 1.0 | api; payments; python | 30.0 | senior | 0.71 | ✘ on leave |
| 4 | Rohan Das | 0.33 | api | 20.0 | mid | 0.56 | ✘ skill match 33% < 67% |
| 5 | Kabir Singh | 0.33 | python | 28.0 | junior | 0.52 | ✘ skill match 33% < 67% |



---
## WF009-described-task

### Request
> Assign a React and CSS product filter UI task (12 hours) to a developer by 2026-10-15

**Selected workflow:** `WF009` - Employee Task Assignment  
**Routing:** offline-lexical, confidence 0.90 - Best lexical match to 'Employee Task Assignment' (score 0.54 vs next 0.09); shared terms: assign, developer, task.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 6 ms  
**Extracted parameters:** `{"task_description": "React and CSS product filter UI", "deadline": "2026-10-15", "role": "Developer", "estimated_hours": 12.0}`


**Steps executed:**

1. ✔ **Understand task requirements** (`understand_task`, 1 ms) - NEW: 'React and CSS product filter UI' needs css, react, ui; priority normal, deadline 2026-10-15
    - ↳ Required skills matched from skill vocabulary: ['css', 'react', 'ui']
2. ✔ **Compare employee skills** (`compare_skills`, 0 ms) - Aarav Mehta 0%; Sneha Iyer 0%; Rohan Das 67%; Meera Nair 0%; Kabir Singh 0%
    - ↳ Role filter 'Developer': 5 of 8 employees
3. ✔ **Check current workload** (`check_workload`, 0 ms) - 2 of 5 have ≥ 12h free and are not on leave
4. ✔ **Rank candidates** (`rank_candidates`, 0 ms) - Ranking: Rohan Das (0.762) > Aarav Mehta (0.35) > Kabir Singh (0.33) > Sneha Iyer (0.11)
    - ↳ Score = skills×0.6 + capacity×0.3 + seniority×0.1; capacity = free hours / task hours (capped at 1)
5. ✔ **Select employee** (`select_employee`, 0 ms) - Selected Rohan Das (E-103)
    - ↳ Selected Rohan Das: skill match 67%, 20h free, mid
6. ✔ **Generate assignment summary** (`assignment_summary`, 0 ms) - Rohan Das (E-103, mid Developer)

#### Result: Task assignment
Recommendation: Rohan Das (E-103, mid Developer)

**Assignment summary**

- **recommended**: Rohan Das (E-103, mid Developer)
- **reasoning**: Has 2/3 required skills (css, react) and 20h free this week (task needs 12h). Others not chosen: Aarav Mehta - only 10h free; skill match 0% < 67%; Kabir Singh - skill match 0% < 67%; Sneha Iyer - only 2h free; skill match 0% < 67%.
- **priority**: normal
- **deadline**: 2026-10-15
- **task summary**: NEW: React and CSS product filter UI
- **required skills**: css, react, ui
- **estimated hours**: 12.0

**Candidate ranking**

| rank | name | skill_match | matched_skills | available_hours | seniority | score | status |
|---|---|---|---|---|---|---|---|
| 1 | Rohan Das | 0.67 | css; react | 20.0 | mid | 0.76 | ✔ suitable |
| 2 | Aarav Mehta | 0.0 |  | 10.0 | senior | 0.35 | ✘ only 10h free; skill match 0% < 67% |
| 3 | Kabir Singh | 0.0 |  | 28.0 | junior | 0.33 | ✘ skill match 0% < 67% |
| 4 | Sneha Iyer | 0.0 |  | 2.0 | mid | 0.11 | ✘ only 2h free; skill match 0% < 67% |
| 5 | Meera Nair | 0.0 |  | 30.0 | senior | 0.1 | ✘ on leave; skill match 0% < 67% |



---
## WF009-escalation

### Request
> Assign a Kubernetes and Go migration task (40 hours) to a developer by 2026-10-10

**Selected workflow:** `WF009` - Employee Task Assignment  
**Routing:** offline-lexical, confidence 1.00 - Best lexical match to 'Employee Task Assignment' (score 0.56 vs next 0.00); shared terms: assign, developer, task.  
**Status:** `ESCALATED` · LLM mode: `offline-fallback` · 6 ms  
**Extracted parameters:** `{"task_description": "Kubernetes and Go migration", "deadline": "2026-10-10", "role": "Developer", "estimated_hours": 40.0}`


**Steps executed:**

1. ✔ **Understand task requirements** (`understand_task`, 0 ms) - NEW: 'Kubernetes and Go migration' needs go, kubernetes; priority normal, deadline 2026-10-10
    - ↳ Required skills matched from skill vocabulary: ['go', 'kubernetes']
2. ✔ **Compare employee skills** (`compare_skills`, 0 ms) - Aarav Mehta 0%; Sneha Iyer 0%; Rohan Das 0%; Meera Nair 0%; Kabir Singh 0%
    - ↳ Role filter 'Developer': 5 of 8 employees
3. ✔ **Check current workload** (`check_workload`, 0 ms) - 0 of 5 have ≥ 40h free and are not on leave
4. ✔ **Rank candidates** (`rank_candidates`, 0 ms) - Ranking: Kabir Singh (0.24) > Rohan Das (0.21) > Aarav Mehta (0.175) > Meera Nair (0.1)
    - ↳ Score = skills×0.6 + capacity×0.3 + seniority×0.1; capacity = free hours / task hours (capped at 1)
5. ✔ **Select employee** (`select_employee`, 0 ms) - No suitable employee - escalated
    - ↳ No employee has ≥67% of the required skills AND enough capacity -> ESCALATE to manager
6. ✔ **Generate assignment summary** (`assignment_summary`, 0 ms) - ESCALATED - no suitable employee

#### Result: Task assignment
> **ESCALATED** - no suitable employee found; manager decision required.

Recommendation: ESCALATED - no suitable employee

**Assignment summary**

- **recommended**: ESCALATED - no suitable employee
- **reasoning**: No candidate meets both the skill requirement and the capacity needed. Options: re-prioritise existing work, extend the deadline, or bring in additional help.
- **priority**: normal
- **deadline**: 2026-10-10
- **task summary**: NEW: Kubernetes and Go migration
- **required skills**: go, kubernetes
- **estimated hours**: 40.0

**Candidate ranking**

| rank | name | skill_match | matched_skills | available_hours | seniority | score | status |
|---|---|---|---|---|---|---|---|
| 1 | Kabir Singh | 0.0 |  | 28.0 | junior | 0.24 | ✘ only 28h free; skill match 0% < 67% |
| 2 | Rohan Das | 0.0 |  | 20.0 | mid | 0.21 | ✘ only 20h free; skill match 0% < 67% |
| 3 | Aarav Mehta | 0.0 |  | 10.0 | senior | 0.17 | ✘ only 10h free; skill match 0% < 67% |
| 4 | Meera Nair | 0.0 |  | 30.0 | senior | 0.1 | ✘ on leave; skill match 0% < 67% |
| 5 | Sneha Iyer | 0.0 |  | 2.0 | mid | 0.07 | ✘ only 2h free; skill match 0% < 67% |



---
## WF010-excel-test

### Request
> Which workflows are failing most often?

**Selected workflow:** `WF010` - Workflow Performance Report  
**Routing:** offline-lexical, confidence 0.93 - Best lexical match to 'Workflow Performance Report' (score 0.41 vs next 0.00); shared terms: fail, workflow.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 26 ms  
**Extracted parameters:** `{"logs_path": "data/workflow_execution_logs.csv", "failure_threshold": 10.0}`


**Steps executed:**

1. ✔ **Load execution logs** (`load_table`, 15 ms) - Loaded 2148 rows from workflow_execution_logs.csv (columns: timestamp, run_id, workflow_id, workflow_name, step_name, status, duration_ms, error_message)
2. ✔ **Calculate success/failure rate** (`workflow_success_rates`, 2 ms) - 403 runs across 10 workflows; overall failure rate 8.2%
3. ✔ **Calculate average execution time** (`average_execution_time`, 2 ms) - Slowest: WF007 8015ms, WF004 6805ms, WF008 6627ms
4. ✔ **Identify frequent errors** (`frequent_errors`, 0 ms) - 33 errors; top: Order API 503 Service Unavailable
5. ✔ **Identify slow steps** (`slow_steps`, 1 ms) - 4 step(s) average above 3000ms
    - ↳ Slow step rule: avg successful duration > 3000ms
6. ✔ **Generate recommendations** (`performance_recommendations`, 0 ms) - 4 workflow(s) flagged; 7 recommendation(s)
    - ↳ Flag rule: failure rate > 10% OR avg time > 8000ms

#### Result: Workflow performance report
4 of 10 workflows are flagged (failure rate above threshold or slow). Sorted by failure rate below.

**Recommendations**

- WF005 Customer Order Status: most common error 'Order API 503 Service Unavailable' in step 'Search order data' -> Upstream service unavailable - add retries/backoff and an alert on the dependency's health.
- WF003 Vendor File Processing: most common error 'Unsupported file encoding' in step 'Read file' -> Detect file encoding (e.g. UTF-8 vs Latin-1) before parsing vendor files.
- WF004 Product Description Generator: most common error 'LLM rate limit exceeded (429)' in step 'Create description' -> Throttle LLM calls: batch requests, add backoff on 429, or raise the rate-limit tier.
- WF007 Marketing Campaign Brief: slow step 'Create messaging' (3611ms avg) -> cache results, parallelise or use a smaller/faster model.
- WF008: step 'Classify intent' averages 5037ms - watch it (above the per-step threshold) - consider caching, batching or a faster model.
- WF004: step 'Create description' averages 4206ms - watch it (above the per-step threshold) - consider caching, batching or a faster model.
- WF007: step 'Channel recommendations' averages 3220ms - watch it (above the per-step threshold) - consider caching, batching or a faster model.

**Workflow metrics (sorted by failure rate)**

| ID | Workflow | Runs | Failed | Failure % | Success % | Avg ms | Flag |
|---|---|---|---|---|---|---|---|
| WF005 | Customer Order Status | 37 | 12 | 32.4 | 67.6 | 5377 | ⚠ failure rate 32.4% > 10% |
| WF003 | Vendor File Processing | 41 | 6 | 14.6 | 85.4 | 1775 | ⚠ failure rate 14.6% > 10% |
| WF004 | Product Description Generator | 38 | 5 | 13.2 | 86.8 | 6805 | ⚠ failure rate 13.2% > 10% |
| WF008 | SEO Keyword Classification | 38 | 3 | 7.9 | 92.1 | 6627 | OK |
| WF001 | Inventory Restock Check | 40 | 2 | 5.0 | 95.0 | 1624 | OK |
| WF006 | Duplicate Product Detection | 38 | 1 | 2.6 | 97.4 | 4261 | OK |
| WF002 | Product Price Validation | 40 | 1 | 2.5 | 97.5 | 1715 | OK |
| WF010 | Workflow Performance Report | 40 | 1 | 2.5 | 97.5 | 1838 | OK |
| WF009 | Employee Task Assignment | 44 | 1 | 2.3 | 97.7 | 2045 | OK |
| WF007 | Marketing Campaign Brief | 47 | 1 | 2.1 | 97.9 | 8015 | ⚠ avg time 8015ms > 8000ms |

**Most frequent errors**

| workflow_id | step_name | error_message | occurrences | share_of_errors |
|---|---|---|---|---|
| WF005 | Search order data | Order API 503 Service Unavailable | 7 | 21% |
| WF005 | Search order data | Order API timeout after 30s | 5 | 15% |
| WF004 | Create description | LLM rate limit exceeded (429) | 5 | 15% |
| WF003 | Read file | Unsupported file encoding | 5 | 15% |
| WF008 | Classify intent | LLM rate limit exceeded (429) | 2 | 6% |
| WF001 | Compare stock | Unexpected null value | 2 | 6% |

**Slow steps**

| workflow_id | step_name | avg_ms | executions |
|---|---|---|---|
| WF008 | Classify intent | 5037 | 35 |
| WF004 | Create description | 4206 | 33 |
| WF007 | Create messaging | 3611 | 46 |
| WF007 | Channel recommendations | 3220 | 46 |



---
## WF010-custom-threshold

### Request
> Give me a workflow performance report and flag anything failing more than 5%.

**Selected workflow:** `WF010` - Workflow Performance Report  
**Routing:** offline-lexical, confidence 0.97 - Best lexical match to 'Workflow Performance Report' (score 0.73 vs next 0.03); shared terms: fail, performance, report, workflow.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 21 ms  
**Extracted parameters:** `{"logs_path": "data/workflow_execution_logs.csv", "failure_threshold": 5.0}`


**Steps executed:**

1. ✔ **Load execution logs** (`load_table`, 12 ms) - Loaded 2148 rows from workflow_execution_logs.csv (columns: timestamp, run_id, workflow_id, workflow_name, step_name, status, duration_ms, error_message)
2. ✔ **Calculate success/failure rate** (`workflow_success_rates`, 1 ms) - 403 runs across 10 workflows; overall failure rate 8.2%
3. ✔ **Calculate average execution time** (`average_execution_time`, 1 ms) - Slowest: WF007 8015ms, WF004 6805ms, WF008 6627ms
4. ✔ **Identify frequent errors** (`frequent_errors`, 0 ms) - 33 errors; top: Order API 503 Service Unavailable
5. ✔ **Identify slow steps** (`slow_steps`, 1 ms) - 4 step(s) average above 3000ms
    - ↳ Slow step rule: avg successful duration > 3000ms
6. ✔ **Generate recommendations** (`performance_recommendations`, 0 ms) - 5 workflow(s) flagged; 8 recommendation(s)
    - ↳ Flag rule: failure rate > 5% OR avg time > 8000ms

#### Result: Workflow performance report
5 of 10 workflows are flagged (failure rate above threshold or slow). Sorted by failure rate below.

**Recommendations**

- WF005 Customer Order Status: most common error 'Order API 503 Service Unavailable' in step 'Search order data' -> Upstream service unavailable - add retries/backoff and an alert on the dependency's health.
- WF003 Vendor File Processing: most common error 'Unsupported file encoding' in step 'Read file' -> Detect file encoding (e.g. UTF-8 vs Latin-1) before parsing vendor files.
- WF004 Product Description Generator: most common error 'LLM rate limit exceeded (429)' in step 'Create description' -> Throttle LLM calls: batch requests, add backoff on 429, or raise the rate-limit tier.
- WF008 SEO Keyword Classification: most common error 'LLM rate limit exceeded (429)' in step 'Classify intent' -> Throttle LLM calls: batch requests, add backoff on 429, or raise the rate-limit tier.
- WF007 Marketing Campaign Brief: slow step 'Create messaging' (3611ms avg) -> cache results, parallelise or use a smaller/faster model.
- WF008: step 'Classify intent' averages 5037ms - watch it (above the per-step threshold) - consider caching, batching or a faster model.
- WF004: step 'Create description' averages 4206ms - watch it (above the per-step threshold) - consider caching, batching or a faster model.
- WF007: step 'Channel recommendations' averages 3220ms - watch it (above the per-step threshold) - consider caching, batching or a faster model.

**Workflow metrics (sorted by failure rate)**

| ID | Workflow | Runs | Failed | Failure % | Success % | Avg ms | Flag |
|---|---|---|---|---|---|---|---|
| WF005 | Customer Order Status | 37 | 12 | 32.4 | 67.6 | 5377 | ⚠ failure rate 32.4% > 5% |
| WF003 | Vendor File Processing | 41 | 6 | 14.6 | 85.4 | 1775 | ⚠ failure rate 14.6% > 5% |
| WF004 | Product Description Generator | 38 | 5 | 13.2 | 86.8 | 6805 | ⚠ failure rate 13.2% > 5% |
| WF008 | SEO Keyword Classification | 38 | 3 | 7.9 | 92.1 | 6627 | ⚠ failure rate 7.9% > 5% |
| WF001 | Inventory Restock Check | 40 | 2 | 5.0 | 95.0 | 1624 | OK |
| WF006 | Duplicate Product Detection | 38 | 1 | 2.6 | 97.4 | 4261 | OK |
| WF002 | Product Price Validation | 40 | 1 | 2.5 | 97.5 | 1715 | OK |
| WF010 | Workflow Performance Report | 40 | 1 | 2.5 | 97.5 | 1838 | OK |
| WF009 | Employee Task Assignment | 44 | 1 | 2.3 | 97.7 | 2045 | OK |
| WF007 | Marketing Campaign Brief | 47 | 1 | 2.1 | 97.9 | 8015 | ⚠ avg time 8015ms > 8000ms |

**Most frequent errors**

| workflow_id | step_name | error_message | occurrences | share_of_errors |
|---|---|---|---|---|
| WF005 | Search order data | Order API 503 Service Unavailable | 7 | 21% |
| WF005 | Search order data | Order API timeout after 30s | 5 | 15% |
| WF004 | Create description | LLM rate limit exceeded (429) | 5 | 15% |
| WF003 | Read file | Unsupported file encoding | 5 | 15% |
| WF008 | Classify intent | LLM rate limit exceeded (429) | 2 | 6% |
| WF001 | Compare stock | Unexpected null value | 2 | 6% |

**Slow steps**

| workflow_id | step_name | avg_ms | executions |
|---|---|---|---|
| WF008 | Classify intent | 5037 | 35 |
| WF004 | Create description | 4206 | 33 |
| WF007 | Create messaging | 3611 | 46 |
| WF007 | Channel recommendations | 3220 | 46 |



---
## out-of-scope

### Request
> What's the weather in Paris tomorrow?

**Selected workflow:** none  
**Routing:** offline-lexical, confidence 0.00 - No workflow matched the request with enough similarity.  
**Status:** `NO_MATCH` · LLM mode: `offline-fallback` · 2 ms  

**No workflow selected:** I couldn't match this request to a workflow. No workflow matched the request with enough similarity. Available workflows: Inventory Restock Check, Product Price Validation, Vendor File Processing, Product Description Generator, Customer Order Status, Duplicate Product Detection, Marketing Campaign Brief, SEO Keyword Classification, Employee Task Assignment, Workflow Performance Report.



---
## WF010-live-agent-logs

### Request
> Show a performance report of this agent's own live runs.

**Selected workflow:** `WF010` - Workflow Performance Report  
**Routing:** offline-lexical, confidence 0.90 - Best lexical match to 'Workflow Performance Report' (score 0.50 vs next 0.08); shared terms: performance, report.  
**Status:** `COMPLETED` · LLM mode: `offline-fallback` · 9 ms  
**Extracted parameters:** `{"logs_path": "logs/execution_log.csv", "failure_threshold": 10.0}`


**Steps executed:**

1. ✔ **Load execution logs** (`load_table`, 1 ms) - Loaded 132 rows from execution_log.csv (columns: timestamp, run_id, workflow_id, workflow_name, step_name, status, duration_ms, error_message)
2. ✔ **Calculate success/failure rate** (`workflow_success_rates`, 0 ms) - 30 runs across 10 workflows; overall failure rate 6.7%
3. ✔ **Calculate average execution time** (`average_execution_time`, 0 ms) - Slowest: WF005 276ms, WF010 17ms, WF006 8ms
4. ✔ **Identify frequent errors** (`frequent_errors`, 0 ms) - 2 errors; top: Could not detect required column(s) ['sku', 'product_name'] in headers ['foo', 'bar']. Add the header name to the aliases in config/workflow_bindings.yaml.
5. ✔ **Identify slow steps** (`slow_steps`, 0 ms) - 0 step(s) average above 3000ms
    - ↳ Slow step rule: avg successful duration > 3000ms
6. ✔ **Generate recommendations** (`performance_recommendations`, 0 ms) - 2 workflow(s) flagged; 2 recommendation(s)
    - ↳ Flag rule: failure rate > 10% OR avg time > 8000ms

#### Result: Workflow performance report
2 of 10 workflows are flagged (failure rate above threshold or slow). Sorted by failure rate below.

**Recommendations**

- WF003 Vendor File Processing: most common error 'Could not detect required column(s) ['sku', 'product_name'] in headers ['foo', 'bar']. Add the header name to the aliases in config/workflow_bindings.yaml.' in step 'Detect columns' -> Validate the header row up-front and return a clear message to the vendor.
- WF005 Customer Order Status: most common error 'order_api unavailable (simulated 503 Service Unavailable)' in step 'Search order data' -> Upstream service unavailable - add retries/backoff and an alert on the dependency's health.

**Workflow metrics (sorted by failure rate)**

| ID | Workflow | Runs | Failed | Failure % | Success % | Avg ms | Flag |
|---|---|---|---|---|---|---|---|
| WF003 | Vendor File Processing | 4 | 1 | 25.0 | 75.0 | 2 | ⚠ failure rate 25.0% > 10% |
| WF005 | Customer Order Status | 6 | 1 | 16.7 | 83.3 | 276 | ⚠ failure rate 16.7% > 10% |
| WF001 | Inventory Restock Check | 2 | 0 | 0.0 | 100.0 | 1 | OK |
| WF002 | Product Price Validation | 2 | 0 | 0.0 | 100.0 | 1 | OK |
| WF004 | Product Description Generator | 5 | 0 | 0.0 | 100.0 | 0 | OK |
| WF006 | Duplicate Product Detection | 1 | 0 | 0.0 | 100.0 | 8 | OK |
| WF007 | Marketing Campaign Brief | 4 | 0 | 0.0 | 100.0 | 1 | OK |
| WF008 | SEO Keyword Classification | 1 | 0 | 0.0 | 100.0 | 6 | OK |
| WF009 | Employee Task Assignment | 3 | 0 | 0.0 | 100.0 | 1 | OK |
| WF010 | Workflow Performance Report | 2 | 0 | 0.0 | 100.0 | 17 | OK |

**Most frequent errors**

| workflow_id | step_name | error_message | occurrences | share_of_errors |
|---|---|---|---|---|
| WF003 | Detect columns | Could not detect required column(s) ['sku', 'product_name'] in headers ['foo', 'bar']. Add the header name to the aliases in config/workflow_bindings.yaml. | 1 | 50% |
| WF005 | Search order data | order_api unavailable (simulated 503 Service Unavailable) | 1 | 50% |

**Slow steps**

_No slow steps._

