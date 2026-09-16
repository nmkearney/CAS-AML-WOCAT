"""Index and sample the WOCAT photo corpus.

Images are served from https://wocat.net/media/... and are **public** - no token
needed, unlike the database API. Every image ships four renditions:

    fill-320x240   webp   ~23 KB   contact sheets
    fill-576x360   avif
    fill-768x480   jpeg   ~80 KB   the sensible default for CV work
    fill-1920x1080 avif

The full corpus is ~4,400 images over ~1,450 technologies. Nothing here downloads
it all by default: ``download_sample`` takes a stratified slice so you can look at
what the photos actually show before committing to an image-based project.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

from wocat_api.client import RAW_DIR
from wocat_api.transform import i18n

MEDIA_BASE = "https://wocat.net"
RENDITION_KEYS = {
    "thumb": "fill-320x240|format-webp|webpquality-70",
    "medium": "fill-768x480|format-jpeg|jpegquality-85",
    "large": "fill-1920x1080|format-avif|avifquality-68",
}
IMAGE_DIR = RAW_DIR / "images"


def build_image_index(records: list[dict]) -> pd.DataFrame:
    """One row per image, with the metadata that decides whether M2 is viable."""
    rows = []
    for record in records:
        sv = record.get("selected_version") or {}
        header_id = (sv.get("header_image") or {}).get("id")
        for position, image in enumerate(sv.get("images") or []):
            renditions = image.get("renditions") or {}
            rows.append(
                {
                    "technology_id": record.get("id"),
                    "image_id": image.get("id"),
                    "position": position,
                    "is_header": image.get("id") == header_id,
                    "country": sv.get("country"),
                    "caption": i18n(image.get("caption")),
                    "caption_langs": "|".join(sorted(image.get("caption") or {})) or None,
                    "photo_location": i18n(image.get("location")),
                    "photographer": i18n(image.get("photographer")),
                    "date": image.get("date"),
                    "uploaded": image.get("uploaded"),
                    "width": image.get("width"),
                    "height": image.get("height"),
                    "url_thumb": _rendition_url(renditions, "thumb"),
                    "url_medium": _rendition_url(renditions, "medium"),
                    "url_original": MEDIA_BASE + image["file"] if image.get("file") else None,
                }
            )
    return pd.DataFrame(rows)


def _rendition_url(renditions: dict, size: str) -> str | None:
    entry = renditions.get(RENDITION_KEYS[size])
    return MEDIA_BASE + entry["url"] if entry and entry.get("url") else None


def download_sample(
    index: pd.DataFrame,
    n: int = 200,
    size: str = "medium",
    stratify_by: str | None = "landuse_group",
    out_dir: Path = IMAGE_DIR,
    workers: int = 8,
    seed: int = 0,
) -> pd.DataFrame:
    """Download ``n`` images to ``out_dir``; returns the sampled rows with local paths.

    Already-downloaded files are skipped, so this is safe to re-run.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    url_col = f"url_{size}"
    pool = index[index[url_col].notna()]

    if stratify_by and stratify_by in pool.columns:
        groups = pool.groupby(stratify_by, dropna=False)
        per_group = max(1, n // max(len(groups), 1))
        sample = (
            groups.apply(lambda g: g.sample(min(len(g), per_group), random_state=seed),
                         include_groups=False)
            .reset_index(level=0)
            .head(n)
        )
    else:
        sample = pool.sample(min(n, len(pool)), random_state=seed)

    ext = {"thumb": ".webp", "medium": ".jpg", "large": ".avif"}[size]
    session = requests.Session()

    def grab(row) -> str | None:
        path = out_dir / f"{row.image_id}{ext}"
        if path.exists():
            return str(path)
        try:
            resp = session.get(row[url_col], timeout=60)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"  ! image {row.image_id}: {exc}")
            return None
        path.write_bytes(resp.content)
        return str(path)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        paths = list(executor.map(grab, [r for _, r in sample.iterrows()]))

    sample = sample.copy()
    sample["local_path"] = paths
    return sample
