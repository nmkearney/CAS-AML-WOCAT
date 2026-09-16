"""Download the WOCAT technology corpus and write the CSVs the notebooks read.

    python wocat_api/fetch.py                 # use whatever is already cached
    python wocat_api/fetch.py --refresh       # re-download everything
    python wocat_api/fetch.py --limit 50      # quick smoke test
    python wocat_api/fetch.py --images        # also pull the 320x240 thumbnails

Raw JSON lands in data/raw/technologies/<id>.json, one file per technology, so
re-runs are offline and free. If every record is already cached the script needs
no token at all - it just rebuilds the tables.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wocat_api import (  # noqa: E402
    PROCESSED_DIR,
    RAW_DIR,
    WocatClient,
    build_biodiversity_impacts_long,
    build_degradation_long,
    build_image_index,
    build_m1_matrix,
    build_technologies_table,
    country_lookup,
    download_sample,
    fetch_technology_details,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refresh", action="store_true", help="ignore the cache and re-download")
    parser.add_argument("--limit", type=int, help="only fetch the first N technologies")
    parser.add_argument("--workers", type=int, default=6, help="parallel requests (default 6)")
    parser.add_argument("--images", action="store_true",
                        help="also download every 320x240 thumbnail (~4,400 files, ~100 MB)")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    print(f"data directory: {RAW_DIR.parent}")

    # The two list endpoints are one request each, and only when we lack the file.
    list_path = RAW_DIR / "technologies_list.json"
    countries_path = RAW_DIR / "countries.json"
    if args.refresh or not list_path.exists() or not countries_path.exists():
        client = WocatClient()
        if args.refresh or not list_path.exists():
            print("fetching the technology list ...")
            list_path.write_text(json.dumps(client.technologies(), ensure_ascii=False))
        if args.refresh or not countries_path.exists():
            countries_path.write_text(json.dumps(client.countries(), ensure_ascii=False))

    summaries = json.loads(list_path.read_text())
    names = country_lookup(json.loads(countries_path.read_text()))
    print(f"  {len(summaries)} technologies in the database")

    ids = [s["id"] for s in summaries][: args.limit]
    print(f"fetching {len(ids)} full records (workers={args.workers}) ...")
    records = fetch_technology_details(ids, workers=args.workers, refresh=args.refresh)

    m1_matrix, m1_dictionary = build_m1_matrix(records, names)
    tables = {
        "technologies_biodiversity.csv": build_technologies_table(records, names),
        "biodiversity_impacts_long.csv": build_biodiversity_impacts_long(records, names),
        "biological_degradation_long.csv": build_degradation_long(records),
        "images_index.csv": build_image_index(records),
        "m1_features.csv": m1_matrix,
        "m1_feature_dictionary.csv": m1_dictionary,
    }

    print(f"\nwriting CSVs to {PROCESSED_DIR}")
    for name, table in tables.items():
        table.to_csv(PROCESSED_DIR / name, index=False)
        print(f"  {name:<36} shape={table.shape}")

    if args.images:
        index = tables["images_index.csv"]
        thumbs = RAW_DIR / "images_thumb"
        print(f"\ndownloading {len(index)} thumbnails to {thumbs} ...")
        download_sample(index, n=len(index), size="thumb", stratify_by=None,
                        out_dir=thumbs, workers=12)
        print(f"  {len(list(thumbs.glob('*.webp')))} thumbnails on disk")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:          # a missing token is a setup problem, not a crash
        sys.exit(f"\n{exc}")
