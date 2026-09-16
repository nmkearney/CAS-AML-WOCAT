# Water availability and cost fields

Module 2 listed four research-plan fields as *"not in the table"*: **groundwater table** (5.4),
**availability of surface water**, **cost of establishment** (4.4) and **cost of maintenance** (4.6).

They are all present in the raw WOCAT API records — they were simply never extracted. This folder
extracts them for all **1,540 technologies**, so they can be joined into any of the module
notebooks on `technology_id`.

```python
import pandas as pd
water = pd.read_csv("water_and_costs/water_availability.csv")
costs = pd.read_csv("water_and_costs/costs_summary.csv")
items = pd.read_csv("water_and_costs/cost_items.csv")
```

## Files

| file | rows | what it is |
|---|---|---|
| `water_availability.csv` | 1,540 | one row per technology — the water block of questionnaire section 5.4 |
| `costs_summary.csv` | 1,540 | one row per technology — costs totalled per phase and category, converted to USD |
| `cost_items.csv` | 11,734 | one row per **cost item** (a single input line of section 4.4 / 4.6) |
| `build.py` | — | the script that regenerates all three from the raw records |

## `water_availability.csv`

| column | coverage | values |
|---|---|---|
| `groundwater` | 75% | `ONSURFACE`, `LESS_5M`, `5_50M`, `50M_PLUS` — depth of the groundwater table |
| `surfacewater` | 79% | `EXCESS`, `GOOD`, `MEDIUM`, `POOR` — availability of surface water |
| `waterquality` | 78% | `GOOD`, `AGRICULTURALUSE`, `POOR`, `UNUSABLE` |
| `waterquality_referring` | 25% | `GROUND`, `SURFACE`, `BOTH` — which source the quality rating refers to |
| `watersupply` | 86% | `RAINFED`, `MIXED`, `IRRIGATION`, `OTHER` |
| `water_use_rights` | 71% | `OPEN_ACCESS`, `COMMUNAL`, `INDIVIDUAL`, `LEASED`, `OTHER`, pipe-separated when several |
| `water_comments` | 36% | free text, English preferred |

The four ordered categories make `groundwater` and `surfacewater` usable as ordinal features
straight away. Note they are missing for a quarter of records, which is roughly the same share as
the `mechanisation` gap — the same gap-filling question applies.

## `costs_summary.csv`

One row per technology. Besides `technology_id`, `country` and `name`:

| column group | columns |
|---|---|
| currency | `currency_base` (`USD` / `other`), `currency_other`, `exchange_rate_per_usd`, `labour_day_cost_raw` |
| basis | `calculation_base` (`area` / `unit`), `calculation_unit`, `hectare_conversion_factor` |
| per phase × category | `establishment_labour_usd`, `establishment_equipment_usd`, `establishment_plant_material_usd`, `establishment_fertilizers_biocides_usd`, `establishment_construction_material_usd`, `establishment_other_usd` — and the same six for `maintenance_` |
| per phase totals | `{phase}_total_usd`, `{phase}_n_items`, `{phase}_total_estimation_reported`, `{phase}_other_funding` |
| ratings | `costbenefit_{establishment,maintenance}_{short,long}` — `VERYNEGATIVE` … `VERYPOSITIVE`, 7 levels, ~91% coverage |
| context | `cost_assumptions` — the compiler's own note on what the figures assume (87%) |

`establishment_total_usd` is present for **1,088 records (71%)**, `maintenance_total_usd` for
**952 (62%)**. Median establishment total is **434 USD** (quartiles 67 / 434 / 2,313); median
maintenance total is **106 USD** (15 / 106 / 448).

## `cost_items.csv`

The long/tidy version — one row per input line, which is where the detail is:

`technology_id`, `country`, `phase` (`establishment` / `maintenance`), `category`, `input`
(what the compiler typed, e.g. *"Bulldozer rent"*), `unit`, `quantity`, `cost_per_unit`,
`total_cost` (= `quantity × cost_per_unit`, **in local currency**), `currency`, `total_cost_usd`,
`pct_borne_by_land_users`.

## Caveats — please read before modelling

1. **Currencies are mixed.** Only 365 records report in USD; 1,011 report in a local currency
   named free-text in `currency_other` (*"Kshs"*, *"KES"*, *"KES (March 2023)"* — not a clean
   code), and 164 say nothing. `total_cost_usd` divides by `exchange_rate_per_usd`, which is local
   units per 1 USD as stated by the compiler. **10,326 of 11,734 items (88%) get a USD figure; the
   rest are local-currency only.** No inflation adjustment is applied, and the records were first
   published anywhere between 2016 and 2026, so a USD figure from one record is not directly
   comparable with one from another.
2. **The totals are not per-hectare and are not comparable as they stand.** Only 546 records say
   the figures are per `area` and 271 per `unit`; **723 say nothing at all**, and
   `hectare_conversion_factor` exists for only 9%. So a 22,000 USD establishment cost may be for
   one hectare or for a whole scheme. Filter on `calculation_base == "area"` and read
   `calculation_unit` before comparing anything.
3. **Outliers are real, not extraction bugs.** The largest item is a 21 M EUR labour line on a
   German record. It is what the compiler entered. Expect to work on logs or on medians.
4. **One negative cost survives** (technology 2965, pig slurry application, −10 EUR/unit) and
   looks deliberate — the input earns money rather than costing it. One record with a *negative
   exchange rate* is treated as having no rate, so its items carry `total_cost_usd = NaN`.
5. **`labour_day_cost_raw` is free text**, not a number: *"3.00"*, *"KES 250.00"*,
   *"4333.67 FCFA/linear meter"*. Parse it yourself if you need it.

## Rebuilding

```bash
python water_and_costs/build.py
```

It reads the raw JSON records from the sibling `wocat` project
(`../wocat/data/raw/technologies/*.json`, one file per technology, fetched by that project's
`scripts/fetch_data.py`) and rewrites the three CSVs. English is preferred wherever a field is
multilingual.
