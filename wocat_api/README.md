# `wocat_api` — getting the data out of the WOCAT database

Every notebook in this repo reads CSVs that came from the
[WOCAT database API](https://wocat.net/api/database/redoc/). This folder is the code that
produces them, so the whole chain — API → raw JSON → tidy tables → notebooks — lives in one place.

```
  WOCAT API  ──►  data/raw/technologies/<id>.json  ──►  data/processed/*.csv  ──►  notebooks
                  (one file per technology,               (the tables the
                   the cache; re-runs are free)            notebooks read)
```

## Quick start

```bash
# 1. a token: ask the WOCAT secretariat at wocat.cde@unibe.ch
cp wocat_api/.env.example .env          # in the repo root, not in this folder
#    then paste your token into .env

# 2. dependencies: requests, python-dotenv, pandas  (torch/torchvision only for images)
pip install requests python-dotenv pandas

# 3. fetch
python wocat_api/fetch.py --limit 20     # smoke test first: 20 records
python wocat_api/fetch.py                # the real thing: all 1,540
python wocat_api/fetch.py --images       # plus every 320x240 thumbnail
```

`.env` is git-ignored. **Never commit the token** — it is tied to a person, not to the project.

## What you get

`python wocat_api/fetch.py` writes six CSVs to `data/processed/`:

| file | shape | what it is |
|---|---|---|
| `technologies_biodiversity.csv` | 1,540 × 40 | one row per technology: location, land use, SLM group, the 8 biodiversity scores |
| `biodiversity_impacts_long.csv` | 2,525 × 10 | one row per rated indicator, tidy format |
| `biological_degradation_long.csv` | 1,694 × 4 | the biodiversity-loss degradation codes, one row each |
| `images_index.csv` | 4,396 × 16 | one row per photograph: captions, dimensions, and the four rendition URLs |
| `m1_features.csv` | 895 × 250 | the modelling matrix — questionnaire fields multi-hot encoded, plus the target |
| `m1_feature_dictionary.csv` | 250 × 6 | what every column of the matrix means |

With `--images` it also fills `data/raw/images_thumb/` with 4,395 webp thumbnails (**79 MB**).
The raw JSON cache is **50 MB**, the CSVs **6.4 MB**.

## The cache is the point

Every detail record is written to `data/raw/technologies/<id>.json` the first time it is fetched
and read from disk every time after. Three consequences worth knowing:

* **Re-running is free and offline.** Rebuilding the six CSVs from a full cache takes seconds and
  makes **no network calls at all** — the token is only created on the first cache miss, so you can
  rebuild a corpus somebody else downloaded **without having a token yourself**.
* **`--refresh` is the only way to get fresh data.** Without it, cached ids are never re-requested.
* **The cache is the archive.** If the API changes or your token expires, the JSON on disk is still
  the corpus everything was built from.

Reuse an existing download instead of fetching your own:

```bash
WOCAT_DATA_DIR=../wocat/data python wocat_api/fetch.py
```

## Where the notebooks look

Each notebook searches `../wocat/data`, `../../wocat/data`, `wocat/data`, `data` and takes the
first that exists. So if you run the fetcher here — creating `wocat_1/data/` — the notebooks find
it, **unless a sibling `../wocat/data` already exists, which wins**. Delete it, rename it, or point
`WOCAT_DATA_DIR` at it; do not keep two copies and wonder which one you are reading.

## The modules

| file | what it does |
|---|---|
| `client.py` | the API client — token, session, the four GET endpoints, and the cached parallel record fetch |
| `transform.py` | one record → tidy rows: the biodiversity block, degradation codes, the summary table |
| `features.py` | the M1 modelling matrix: multi-select fields → multi-hot, ordered fields → ordinal codes |
| `images.py` | builds the photo index from the records, and downloads renditions |
| `fetch.py` | the command-line entry point that wires the four together |

Importable as a package from the repo root, which is what you want inside a notebook:

```python
from wocat_api import WocatClient, build_image_index, fetch_technology_details
```

Each photograph ships four renditions; `images.py` knows the three worth having:

| name | size | format | use |
|---|---|---|---|
| `thumb` | 320×240 | webp, ~23 KB | contact sheets, and what `module_images.ipynb` embeds |
| `medium` | 768×480 | jpeg, ~80 KB | the sensible default for real CV work |
| `large` | 1920×1080 | avif | rarely needed |

Images are served from `wocat.net/media/...` and are **public — no token required**, unlike the
database API itself.

## Caveats

* **The API is GET-only and token-authenticated**; the token goes in an `Authorization: Token …`
  header. Withdrawn or restricted records return an HTTP error and are skipped with a warning
  rather than killing the run.
* **`--workers 6` is deliberate.** It is polite to a public research database. There is no
  documented rate limit; do not go hunting for one.
* **Field names come from the payload, not the OpenAPI spec.** Two biodiversity keys and one
  degradation enum disagree between the two; `transform.py` documents each case and trusts the
  payload.
* **`m1_features.csv` has 895 rows, not 1,540** — it keeps only technologies with at least one
  biodiversity score, because the target is built from them.

## Provenance and what is *not* here

These modules are a copy of the extraction layer of the sibling `wocat` project
(`wocat_bio/`, by Dima), adapted to this repo's layout: `data/` resolves here, and the API client
is created lazily so a cached rebuild needs no token. The modelling and benchmarking code from that
project was deliberately left behind — this folder is about getting the data, nothing else.

Two things live elsewhere:

* **Cost and water fields** — `wocat_api` does not extract them. `water_and_costs/` does, straight
  from the same `data/raw/technologies/*.json` — it lives on the `f/water-costs` branch, not yet
  merged into `main`. (The sibling project also has a
  `wocat_bio/costs.py` that goes further, normalising costs per hectare with an attrition funnel —
  worth reading before redoing that work.)
* **Image embeddings** — `module_images.ipynb` computes its own ResNet18 features from the
  thumbnails and caches them in `cache/`, so there is no embedding step here.
