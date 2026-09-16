"""Flatten WOCAT technology records into biodiversity-focused tidy tables."""

from __future__ import annotations

from typing import Any

import pandas as pd

# The on-site biodiversity impact indicators, as the payload actually spells them.
# NB: two keys differ from the OnSiteBiodiversitySchema enum in the OpenAPI spec
# (`BIOMASS` -> biomass_above_ground_C, `PESTS_DISEASES` -> pest_disease_control),
# and the enum's `HARMFUL_SPECIES` never appears in the data. Trust the payload.
# Each indicator is scored by the compiler on -3 (much worse) .. +3 (much better).
BIODIVERSITY_INDICATORS = [
    "vegetation_cover",
    "biomass_above_ground_C",
    "plant_diversity",
    "animal_diversity",
    "habitat_diversity",
    "beneficial_species",
    "invasive_alien_species",
    "pest_disease_control",
]

INDICATOR_LABELS = {
    "vegetation_cover": "Vegetation cover",
    "biomass_above_ground_C": "Above-ground biomass / C",
    "plant_diversity": "Plant diversity",
    "animal_diversity": "Animal diversity",
    "habitat_diversity": "Habitat diversity",
    "beneficial_species": "Beneficial species",
    "invasive_alien_species": "Invasive alien species",
    "pest_disease_control": "Pest / disease control",
}

# Other ecological impact blocks, kept as context columns.
OTHER_IMPACT_BLOCKS = {
    "impacts_ecological_soil": "soil",
    "impacts_ecological_water": "water",
    "impacts_ecological_climate": "climate",
}

# WOCAT biological degradation codes (the "loss of biodiversity" degradation class).
BIOLOGICAL_DEGRADATION = {
    "Bc": "reduction of vegetation cover",
    "Bh": "loss of habitats",
    "Bs": "quality and species composition decline",
    "Bl": "loss of soil life",
    "Bp": "increase of pests / diseases",
    "Bq": "quantity / biomass decline",
    "Bf": "detrimental effects of fires",
}

LIKERT_LABELS = {
    -3: "much worse (-3)",
    -2: "worse (-2)",
    -1: "slightly worse (-1)",
    0: "no change (0)",
    1: "slightly better (+1)",
    2: "better (+2)",
    3: "much better (+3)",
}


def i18n(value: Any, prefer: str = "en") -> str | None:
    """WOCAT free text is a {lang_code: text} dict. Prefer English, else anything."""
    if not isinstance(value, dict) or not value:
        return None
    if prefer in value and value[prefer]:
        return value[prefer]
    for text in value.values():
        if text:
            return text
    return None


def _centroid(geometry: Any) -> tuple[float | None, float | None]:
    """Mean of the recorded points. WOCAT stores site locations as a MultiPoint."""
    if not isinstance(geometry, dict):
        return None, None
    coords = geometry.get("coordinates") or []
    points = [c for c in coords if isinstance(c, (list, tuple)) and len(c) >= 2]
    if not points:
        return None, None
    lons = [p[0] for p in points]
    lats = [p[1] for p in points]
    return sum(lats) / len(lats), sum(lons) / len(lons)


def _scored(block: Any, key: str) -> dict:
    """Pull one {value, comment, quantity_before, quantity_after} entry from a block."""
    if not isinstance(block, dict):
        return {}
    entry = block.get(key)
    return entry if isinstance(entry, dict) else {}


def country_lookup(countries: list[dict]) -> dict[str, str]:
    """alpha2 -> display name. The countries endpoint lowercases alpha2; records upper it."""
    return {c["alpha2"].upper(): c["name"] for c in countries if c.get("alpha2")}


def build_technologies_table(
    records: list[dict], country_names: dict[str, str] | None = None
) -> pd.DataFrame:
    """One row per technology: identity, site context and biodiversity summary."""
    rows = []
    for record in records:
        sv = record.get("selected_version") or {}
        bio = sv.get("impacts_ecological_biodiversity") or {}
        degradation = sv.get("degradation") or {}
        landuse = sv.get("landuse") or {}
        measures = sv.get("slm_measures") or {}
        lat, lon = _centroid(sv.get("location_geometry"))

        scores = {
            ind: _scored(bio, ind).get("value")
            for ind in BIODIVERSITY_INDICATORS
        }
        rated = [v for v in scores.values() if v is not None]

        row: dict[str, Any] = {
            "technology_id": record.get("id"),
            "version_id": sv.get("id"),
            "name": i18n(sv.get("name")),
            "country": sv.get("country"),
            "country_name": (country_names or {}).get(sv.get("country")),
            "state_province": i18n(sv.get("state_province")),
            "latitude": lat,
            "longitude": lon,
            "edition": sv.get("edition"),
            "first_published_at": record.get("first_published_at"),
            "primary_language": sv.get("primary_language"),
            # --- biodiversity framing -------------------------------------
            "purpose_is_biodiversity": "BIODIVERSITY" in (sv.get("main_purpose") or []),
            "main_purpose": "|".join(sv.get("main_purpose") or []) or None,
            "habitat_diversity_context": sv.get("habitatdiversity"),
            "species_diversity_context": sv.get("speciesdiversity"),
            "in_protected_area": sv.get("location_protected"),
            "biodiversity_comments": i18n(sv.get("biodiversity_comments")),
            "onsite_impacts_comments": i18n(sv.get("onsite_impacts_comments")),
            # --- degradation addressed ------------------------------------
            "addresses_biological_degradation": "BIOLOGICAL" in (degradation.get("value") or []),
            "biological_degradation_codes": "|".join(degradation.get("biological") or []) or None,
            "degradation_types": "|".join(degradation.get("value") or []) or None,
            # --- SLM context ----------------------------------------------
            "landuse": "|".join(landuse.get("value") or []) or None,
            "slm_group": "|".join(sv.get("slm_group") or []) or None,
            "slm_measures": "|".join(measures.get("value") or []) or None,
            "prevention": "|".join(sv.get("prevention") or []) or None,
            "agroclimatic_zone": "|".join(sv.get("agroclimatic_zone") or []) or None,
            "rainfall": "|".join(sv.get("rainfall") or []) or None,
            # --- biodiversity impact scores --------------------------------
            "n_biodiversity_indicators_rated": len(rated),
            "biodiversity_score_mean": sum(rated) / len(rated) if rated else None,
        }
        row.update({f"bio_{ind}": scores[ind] for ind in BIODIVERSITY_INDICATORS})

        # Mean score of the other ecological impact blocks, for comparison.
        for field, label in OTHER_IMPACT_BLOCKS.items():
            block = sv.get(field) or {}
            values = [
                entry["value"]
                for key, entry in block.items()
                if isinstance(entry, dict) and isinstance(entry.get("value"), int)
            ]
            row[f"{label}_score_mean"] = sum(values) / len(values) if values else None

        rows.append(row)

    df = pd.DataFrame(rows).sort_values("technology_id").reset_index(drop=True)
    return df


def build_biodiversity_impacts_long(
    records: list[dict], country_names: dict[str, str] | None = None
) -> pd.DataFrame:
    """One row per (technology, biodiversity indicator) that was actually scored."""
    rows = []
    for record in records:
        sv = record.get("selected_version") or {}
        bio = sv.get("impacts_ecological_biodiversity") or {}
        if not isinstance(bio, dict):
            continue
        for indicator in BIODIVERSITY_INDICATORS:
            entry = _scored(bio, indicator)
            value = entry.get("value")
            if value is None:
                continue
            rows.append(
                {
                    "technology_id": record.get("id"),
                    "country": sv.get("country"),
                    "country_name": (country_names or {}).get(sv.get("country")),
                    "indicator": indicator,
                    "indicator_label": INDICATOR_LABELS.get(indicator, indicator),
                    "value": value,
                    "value_label": LIKERT_LABELS.get(value),
                    "quantity_before": i18n(entry.get("quantity_before")),
                    "quantity_after": i18n(entry.get("quantity_after")),
                    "comment": i18n(entry.get("comment")),
                }
            )
    return pd.DataFrame(rows)


def build_degradation_long(records: list[dict]) -> pd.DataFrame:
    """One row per (technology, biological degradation code) addressed."""
    rows = []
    for record in records:
        sv = record.get("selected_version") or {}
        degradation = sv.get("degradation") or {}
        for code in degradation.get("biological") or []:
            rows.append(
                {
                    "technology_id": record.get("id"),
                    "country": sv.get("country"),
                    "code": code,
                    "label": BIOLOGICAL_DEGRADATION.get(code, code),
                }
            )
    return pd.DataFrame(rows)
