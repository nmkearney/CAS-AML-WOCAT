"""Extract the water-availability and cost fields from the raw WOCAT records.

Four questionnaire fields were listed as "not in the table" in Module 2:
groundwater table (5.4), availability of surface water, cost of establishment (4.4)
and cost of maintenance (4.6). They are all present in the raw API records; this
script pulls them out into three flat CSVs. See README.md for the caveats.

Usage:  python water_and_costs/build.py
"""

import csv
import json
import pathlib

# the raw records live in the sibling `wocat` project (scripts/fetch_data.py put them there)
CANDIDATES = ["../wocat/data", "../../wocat/data", "wocat/data", "data"]
DATA = next((p for p in (pathlib.Path(c).resolve() for c in CANDIDATES)
             if (p / "raw" / "technologies").is_dir()), None)
assert DATA is not None, f"could not find the wocat data folder, tried {CANDIDATES}"

OUT = pathlib.Path(__file__).parent
PHASES = ["establishment", "maintenance"]
CATEGORIES = ["labour", "equipment", "plant_material", "fertilizers_biocides",
              "construction_material", "other"]


def text(value, language="en"):
    """Multilingual fields arrive as {'en': ..., 'ru': ...}. Prefer English.

    Free text carries Windows line endings; normalise them so the CSVs are byte-stable
    across checkouts.
    """
    if isinstance(value, dict):
        if not value:
            return None
        value = value.get(language) or next(iter(value.values()))
    if isinstance(value, str):
        return value.replace("\r\n", "\n").replace("\r", "\n")
    return value


def scalar(value):
    """Some answers are wrapped in a list or in a {'value': [...]} dict."""
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, list):
        return "|".join(str(v) for v in value) or None
    return value


def number(value):
    """A handful of records store a number as a string."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_usd(amount, currency_base, exchange_rate):
    """exchange_rate is local currency units per 1 USD. Returns None when unknown."""
    if amount is None:
        return None
    if currency_base == "USD":
        return round(amount, 2)
    rate = number(exchange_rate)
    if rate and rate > 0:          # one record stores a negative rate; treat it as unknown
        return round(amount / rate, 2)
    return None


records = [json.loads(path.read_text())
           for path in sorted((DATA / "raw" / "technologies").glob("*.json"))]
print(f"read {len(records):,} raw records from {DATA / 'raw' / 'technologies'}")

water, costs, items = [], [], []

for record in records:
    v = record["selected_version"]
    technology_id = record["id"]
    country = v.get("country")
    name = text(v.get("name"))

    # ---- water availability (questionnaire 5.4) ---------------------------------
    water.append({
        "technology_id": technology_id,
        "country": country,
        "name": name,
        "groundwater": scalar(v.get("groundwater")),
        "surfacewater": scalar(v.get("surfacewater")),
        "waterquality": scalar(v.get("waterquality")),
        "waterquality_referring": scalar(v.get("waterquality_referring")),
        "watersupply": scalar(v.get("watersupply")),
        "water_use_rights": scalar(v.get("wateruserights")),
        "water_comments": text(v.get("water_comments")),
    })

    # ---- currency, needed by everything below -----------------------------------
    currency = v.get("cost_calculation_currency") or {}
    currency_base = currency.get("currency_base")
    currency_other = text(currency.get("currency_other"))
    exchange_rate = currency.get("exchange_rate")
    calculation = v.get("cost_calculation") or {}

    # ---- cost items, one row per input (questionnaire 4.4 and 4.6) --------------
    totals = {}
    for phase in PHASES:
        breakdown = v.get(f"{phase}_cost_breakdown") or {}
        for category in CATEGORIES:
            for item in breakdown.get(category) or []:
                quantity, per_unit = item.get("quantity"), item.get("cost_per_unit")
                total = quantity * per_unit if quantity is not None and per_unit is not None else None
                total_usd = to_usd(total, currency_base, exchange_rate)
                if total_usd is not None:
                    totals[(phase, category)] = totals.get((phase, category), 0) + total_usd
                items.append({
                    "technology_id": technology_id,
                    "country": country,
                    "phase": phase,
                    "category": category,
                    "input": text(item.get("specify_text")),
                    "unit": text(item.get("units")),
                    "quantity": quantity,
                    "cost_per_unit": per_unit,
                    "total_cost": round(total, 2) if total is not None else None,
                    "currency": "USD" if currency_base == "USD" else (currency_other or currency_base),
                    "total_cost_usd": total_usd,
                    "pct_borne_by_land_users": item.get("percentage_costs"),
                })

    # ---- one summary row per technology ----------------------------------------
    row = {
        "technology_id": technology_id,
        "country": country,
        "name": name,
        "currency_base": currency_base,
        "currency_other": currency_other,
        "exchange_rate_per_usd": number(exchange_rate),
        "labour_day_cost_raw": text(currency.get("labour_day_cost")),
        "calculation_base": calculation.get("calculation_base"),
        "calculation_unit": text(calculation.get("unit")) or text(calculation.get("size_and_area_unit")),
        "hectare_conversion_factor": calculation.get("hectare_conversion_factor"),
    }
    for phase in PHASES:
        for category in CATEGORIES:
            row[f"{phase}_{category}_usd"] = totals.get((phase, category))
        present = [totals[(phase, c)] for c in CATEGORIES if (phase, c) in totals]
        row[f"{phase}_total_usd"] = round(sum(present), 2) if present else None
        row[f"{phase}_n_items"] = sum(
            len((v.get(f"{phase}_cost_breakdown") or {}).get(c) or []) for c in CATEGORIES)
        row[f"{phase}_total_estimation_reported"] = v.get(f"{phase}_total_estimation")
        row[f"{phase}_other_funding"] = text(v.get(f"{phase}_remaining_costs"))
    for horizon in ["short", "long"]:
        for phase in PHASES:
            row[f"costbenefit_{phase}_{horizon}"] = v.get(f"costbenefit_{phase}_{horizon}")
    row["cost_assumptions"] = text(v.get("most_important_cost_factors"))
    costs.append(row)


def write(rows, filename):
    path = OUT / filename
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {filename:<28} {len(rows):>6,} rows   {path.stat().st_size / 1024:>6.0f} KB")


write(water, "water_availability.csv")
write(costs, "costs_summary.csv")
write(items, "cost_items.csv")
