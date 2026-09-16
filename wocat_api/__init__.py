"""Extraction layer for the WOCAT SLM database API.

Turns the live API into the CSVs the module notebooks read. See README.md.
"""

from wocat_api.client import (
    DATA_DIR,
    PROCESSED_DIR,
    RAW_DIR,
    WocatClient,
    fetch_technology_details,
    get_token,
)
from wocat_api.features import (
    FEATURE_SPEC,
    ORDINAL_SCALES,
    build_m1_matrix,
    target_classes,
)
from wocat_api.images import build_image_index, download_sample
from wocat_api.transform import (
    BIODIVERSITY_INDICATORS,
    BIOLOGICAL_DEGRADATION,
    INDICATOR_LABELS,
    LIKERT_LABELS,
    build_biodiversity_impacts_long,
    build_degradation_long,
    build_technologies_table,
    country_lookup,
    i18n,
)

__all__ = [
    "DATA_DIR",
    "PROCESSED_DIR",
    "RAW_DIR",
    "WocatClient",
    "fetch_technology_details",
    "get_token",
    "FEATURE_SPEC",
    "ORDINAL_SCALES",
    "build_m1_matrix",
    "target_classes",
    "build_image_index",
    "download_sample",
    "BIODIVERSITY_INDICATORS",
    "BIOLOGICAL_DEGRADATION",
    "INDICATOR_LABELS",
    "LIKERT_LABELS",
    "build_biodiversity_impacts_long",
    "build_degradation_long",
    "build_technologies_table",
    "country_lookup",
    "i18n",
]
