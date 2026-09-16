"""Build the M1 modelling matrix: WOCAT questionnaire fields -> X, y.

Design decisions worth knowing before you use this:

* **Target** is a composite: the row-mean of whichever of the 8 on-site biodiversity
  indicators a compiler scored (`BIODIVERSITY_INDICATORS`). Modelling the three
  indicators the project plan names separately is possible but sample-starved
  (plant 475 / animal 249 / habitat 338, only 145 with all three), whereas the
  composite reaches 895. The per-indicator columns are kept so you can switch.
* **Multi-select fields become multi-hot**, not one-hot: a technology can sit on
  cropland *and* forest, and WOCAT records that faithfully.
* **Ordered fields additionally get an ordinal code.** For multi-select ordered
  fields (rainfall, altitude, slope) the code is the mean rank of the selected
  classes, which keeps "500-750mm" and "751-1000mm" adjacent for tree models.
* **Co-occurring impact scores (soil / water / climate) are excluded by default.**
  They are outcomes rated by the same person on the same form as the target, so
  they leak rater optimism rather than ecology. `include_cooccurring_impacts=True`
  adds them back for the "which ecosystem improvements travel together?" question.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np
import pandas as pd

from wocat_api.transform import BIODIVERSITY_INDICATORS, i18n

# --- ordered vocabularies (index = rank) -------------------------------------
ORDINAL_SCALES: dict[str, list[str]] = {
    "rainfall": ["LESS_250", "251_500", "501_750", "751_1000", "1001_1500",
                 "1501_2000", "2001_3000", "3001_4000", "4001_PLUS"],
    "altitudinalzone": ["0_100", "100_500", "500_1000", "1000_1500", "1500_2000",
                        "2000_2500", "2500_3000", "3000_4000", "4000_PLUS"],
    "slopes": ["FLAT", "GENTLE", "MODERATE", "ROLLING", "HILLY", "STEEP", "VERYSTEEP"],
    "soil_depth": ["VERYSHALLOW", "SHALLOW", "MODERATELYDEEP", "DEEP", "VERYDEEP"],
    "soil_texture_topsoil": ["COARSE", "MEDIUM", "FINE"],
    "topsoil_organic": ["LOW", "MEDIUM", "HIGH"],
    "groundwater": ["ONSURFACE", "LESS_5M", "5_50M", "50M_PLUS"],
    "surfacewater": ["POOR", "MEDIUM", "GOOD", "EXCESS"],
    "waterquality": ["UNUSABLE", "POOR", "AGRICULTURALUSE", "GOOD"],
    "land_size": ["LESS_05", "05_1", "1_2", "2_5", "5_15", "15_50", "50_100",
                  "100_500", "500_1000", "1000_10000", "10000_PLUS"],
    "wealth": ["VERYPOOR", "POOR", "AVERAGE", "RICH", "VERYRICH"],
    "offfarm_income": ["0_10", "10_50", "50_PLUS"],
    "implementation_decades": ["LESS_10", "10_50", "50_PLUS"],
    "habitatdiversity": ["LOW", "MEDIUM", "HIGH"],
    "speciesdiversity": ["LOW", "MEDIUM", "HIGH"],
}

Getter = Callable[[dict], Any]


def _plain(field: str) -> Getter:
    return lambda sv: sv.get(field)


def _nested(field: str, key: str) -> Getter:
    return lambda sv: (sv.get(field) or {}).get(key)


# (column prefix, block, getter, multi-select?)
FEATURE_SPEC: list[tuple[str, str, Getter, bool]] = [
    # --- environmental context ------------------------------------------------
    ("agroclimatic_zone", "environment", _plain("agroclimatic_zone"), True),
    ("rainfall", "environment", _plain("rainfall"), True),
    ("altitudinalzone", "environment", _plain("altitudinalzone"), True),
    ("slopes", "environment", _plain("slopes"), True),
    ("landforms", "environment", _plain("landforms"), True),
    ("soil_depth", "environment", _plain("soil_depth"), False),
    ("soil_texture_topsoil", "environment", _plain("soil_texture_topsoil"), False),
    ("topsoil_organic", "environment", _plain("topsoil_organic"), False),
    ("groundwater", "environment", _plain("groundwater"), False),
    ("surfacewater", "environment", _plain("surfacewater"), False),
    ("waterquality", "environment", _plain("waterquality"), False),
    ("watersupply", "environment", _plain("watersupply"), True),
    # --- land use -------------------------------------------------------------
    ("landuse", "landuse", _nested("landuse", "value"), True),
    # --- the technology itself ------------------------------------------------
    ("slm_group", "technology", _plain("slm_group"), True),
    ("measure", "technology", _nested("slm_measures", "value"), True),
    ("agronomic", "technology", _nested("slm_measures", "agronomic"), True),
    ("vegetative", "technology", _nested("slm_measures", "vegetative"), True),
    ("structural", "technology", _nested("slm_measures", "structural"), True),
    ("management", "technology", _nested("slm_measures", "management"), True),
    # --- degradation addressed ------------------------------------------------
    ("degradation", "degradation", _nested("degradation", "value"), True),
    ("deg_biological", "degradation", _nested("degradation", "biological"), True),
    ("deg_chemical", "degradation", _nested("degradation", "chemical"), True),
    ("deg_physical", "degradation", _nested("degradation", "physical"), True),
    ("deg_erosion_water", "degradation", _nested("degradation", "erosion_water"), True),
    ("deg_erosion_wind", "degradation", _nested("degradation", "erosion_wind"), True),
    ("deg_water", "degradation", _nested("degradation", "water_sub"), True),
    # --- stated intent (NB: intent, not outcome - drop this block to test
    #     whether the model works without knowing what the compiler was aiming at)
    ("purpose", "purpose", _plain("main_purpose"), True),
    ("prevention", "purpose", _plain("prevention"), True),
    # --- socio-economic -------------------------------------------------------
    ("market_orientation", "socioeconomic", _plain("market_orientation"), False),
    ("mechanisation", "socioeconomic", _plain("mechanisation"), True),
    ("land_size", "socioeconomic", _plain("land_size"), False),
    ("wealth", "socioeconomic", _plain("wealth"), True),
    ("offfarm_income", "socioeconomic", _plain("offfarm_income"), False),
    ("implementation_decades", "socioeconomic", _plain("implementation_decades"), False),
    ("spread", "socioeconomic", _plain("spread_of_technology"), False),
    # --- pre-existing site biodiversity (context, not outcome) ----------------
    ("habitatdiversity", "site_context", _plain("habitatdiversity"), False),
    ("speciesdiversity", "site_context", _plain("speciesdiversity"), False),
]

COOCCURRING_IMPACTS = {
    "impacts_ecological_soil": "soil",
    "impacts_ecological_water": "water",
    "impacts_ecological_climate": "climate",
}


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v is not None]
    return [value]


def _ordinal_code(field: str, values: list) -> float | None:
    """Mean rank of the selected classes; None when nothing maps."""
    scale = ORDINAL_SCALES.get(field)
    if not scale:
        return None
    ranks = [scale.index(v) for v in values if v in scale]
    return float(np.mean(ranks)) if ranks else None


def build_m1_matrix(
    records: list[dict],
    country_names: dict[str, str] | None = None,
    include_cooccurring_impacts: bool = False,
    min_category_count: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (matrix, data_dictionary).

    Rows are technologies that carry at least one biodiversity score. Categories
    appearing fewer than ``min_category_count`` times are dropped, since a
    one-in-a-thousand dummy is noise for any tree model.
    """
    rows: list[dict[str, Any]] = []
    blocks: dict[str, str] = {}
    kinds: dict[str, str] = {}

    for record in records:
        sv = record.get("selected_version") or {}
        bio = sv.get("impacts_ecological_biodiversity") or {}
        scores = {
            ind: (bio.get(ind) or {}).get("value") if isinstance(bio, dict) else None
            for ind in BIODIVERSITY_INDICATORS
        }
        rated = [v for v in scores.values() if v is not None]
        if not rated:
            continue  # no target -> not a modelling row

        geom = sv.get("location_geometry") or {}
        pts = [c for c in (geom.get("coordinates") or []) if isinstance(c, (list, tuple)) and len(c) >= 2]

        row: dict[str, Any] = {
            "technology_id": record.get("id"),
            "name": i18n(sv.get("name")),
            # --- targets --------------------------------------------------
            "y_biodiversity_mean": float(np.mean(rated)),
            "y_n_indicators": len(rated),
            # --- identifiers / grouping ----------------------------------
            "country": sv.get("country"),
            "country_name": (country_names or {}).get(sv.get("country")),
            "latitude": float(np.mean([p[1] for p in pts])) if pts else None,
            "longitude": float(np.mean([p[0] for p in pts])) if pts else None,
            "edition": sv.get("edition"),
            "n_images": len(sv.get("images") or []),
        }
        row.update({f"y_{ind}": scores[ind] for ind in BIODIVERSITY_INDICATORS})

        for prefix, block, getter, multi in FEATURE_SPEC:
            values = _as_list(getter(sv))
            if multi:
                for v in values:
                    col = f"{prefix}__{v}"
                    row[col] = 1
                    blocks[col], kinds[col] = block, "multi-hot"
            else:
                for v in values:
                    col = f"{prefix}__{v}"
                    row[col] = 1
                    blocks[col], kinds[col] = block, "one-hot"
            code = _ordinal_code(prefix, values)
            if code is not None:
                col = f"{prefix}_ord"
                row[col] = code
                blocks[col], kinds[col] = block, "ordinal"

        if include_cooccurring_impacts:
            for field, label in COOCCURRING_IMPACTS.items():
                block_data = sv.get(field) or {}
                vals = [
                    e["value"] for e in block_data.values()
                    if isinstance(e, dict) and isinstance(e.get("value"), int)
                ]
                col = f"cooccur_{label}_mean"
                row[col] = float(np.mean(vals)) if vals else None
                blocks[col], kinds[col] = "cooccurring_impact", "numeric (LEAKY)"

        rows.append(row)

    df = pd.DataFrame(rows).sort_values("technology_id").reset_index(drop=True)

    # Absent multi-hot means "not selected", not "unknown".
    dummy_cols = [c for c, k in kinds.items() if k in ("multi-hot", "one-hot")]
    df[dummy_cols] = df[dummy_cols].fillna(0).astype("int8")

    rare = [c for c in dummy_cols if df[c].sum() < min_category_count]
    df = df.drop(columns=rare)

    meta_cols = ["technology_id", "name", "country", "country_name",
                 "latitude", "longitude", "edition", "n_images"]
    target_cols = [c for c in df.columns if c.startswith("y_")]
    feature_cols = [c for c in df.columns if c not in meta_cols + target_cols]
    df = df[meta_cols + target_cols + sorted(feature_cols)]

    dictionary = pd.DataFrame(
        [
            {
                "column": c,
                "block": ("target" if c in target_cols else blocks.get(c, "meta")),
                "kind": ("target" if c in target_cols else kinds.get(c, "meta")),
                "non_null": int(df[c].notna().sum()),
                "coverage": round(df[c].notna().mean(), 3),
                "positives": int(df[c].sum()) if kinds.get(c) in ("multi-hot", "one-hot") else None,
            }
            for c in df.columns
        ]
    )
    return df, dictionary


def target_classes(y: pd.Series, cuts: tuple[float, float] = (0.5, 2.0)) -> pd.Series:
    """Ordinal 3-class version of the composite target.

    The corpus is heavily positive (~88% of individual scores are >= +1), so a naive
    negative/neutral/positive split leaves almost nothing outside "positive". These
    cuts instead separate *degrees* of reported benefit, which is the variation a
    model can actually learn.
    """
    low, high = cuts
    return pd.cut(
        y,
        bins=[-np.inf, low, high, np.inf],
        labels=["none/negative", "moderate gain", "strong gain"],
        right=False,
    )
