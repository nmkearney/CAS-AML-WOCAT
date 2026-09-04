# WOCAT — data exploration (Colab-ready)

A single self-contained notebook that downloads the [WOCAT](https://wocat.net) Sustainable Land
Management database, builds a tidy table from it, and examines it from enough angles to decide what
a machine learning project could realistically do with it.

It follows the layout of the *Hands-On Machine Learning* notebooks: a `Setup` section, cached
downloads, `save_fig()`, and numbered sections you can read top to bottom.

| Notebook | Open in Colab |
|---|---|
| `01_wocat_explore.ipynb` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/YOUR_GITHUB_USERNAME/YOUR_REPO/blob/main/colab/01_wocat_explore.ipynb) |

> **Before pushing:** replace `YOUR_GITHUB_USERNAME/YOUR_REPO` in that badge — and in the badge in
> the notebook's second cell — with your actual repository. Until then the link will 404.
> You can always open it anyway via *Colab → File → Open notebook → GitHub*.

## Running it

**In Colab, with the committed data (no token needed).** If `datasets/wocat/wocat_technologies.csv.gz`
is committed, the notebook loads it and runs end to end in seconds.

**In Colab, fetching fresh from the API.** Add your WOCAT token as a Colab Secret named
`WOCAT_TOKEN` (the 🔑 icon in the left sidebar) and enable access for the notebook. The download
takes two to three minutes.

**Locally.**

```bash
pip install requests pandas matplotlib scikit-learn
export WOCAT_TOKEN=...        # or put it in a .env file beside the notebook
jupyter lab 01_wocat_explore.ipynb
```

A token comes from the WOCAT secretariat (wocat.cde@unibe.ch). It is sent as
`Authorization: Token <WOCAT_TOKEN>`. Never commit it.

## What the notebook produces

```
datasets/wocat/wocat_technologies.csv.gz   1540 x 51 tidy table       (~160 KB — commit)
datasets/wocat/impact_scores.csv.gz        23,802 individual scores   (~100 KB — commit)
datasets/wocat/sample_records.json         3 raw records, for §1      (~145 KB — commit)
datasets/wocat/countries.json              country code lookup        (~14 KB  — commit)
datasets/wocat/technologies_raw.json.gz    full API response          (~11 MB  — gitignored)
images/wocat/*.png                         13 figures at 300 dpi
```

Committing the first four means the notebook opens in Colab and runs end to end with **no token**.
Both paths are tested: building from the API, and loading from the committed CSVs alone.

## Sections

1. **Get the Data** — the API, token handling, cached download, flattening ~190 nested fields
2. **Quick Look** — `info()`, `describe()`, histograms of every numeric attribute
3. **Where and When** — country counts, a world scatter, questionnaire editions
4. **How Complete Is It?** — field coverage, the constraint that decides everything else
5. **Three Modalities** — structured fields, 1.2M words of text, 4,396 photographs
6. **What Kind of Practices** — land use, measures, climate zones, a crosstab
7. **The Impact Questionnaire** — the candidate targets, and their skew
8. **Who Wrote It?** — compiler concentration and its effect on the scores
9. **So What Should We Do?** — the summary table, and a one-cell test of the obvious project idea

## The short version

- 1,540 records, 51 columns, **almost entirely categorical** — classical models territory.
- Inputs are ~95% complete; the impact labels are 50–85%. **The target limits the sample, not the features.**
- Nearly every record carries **text and photographs** as well as structured fields. That is what
  makes a neural-network module worth attempting.
- **84% of all impact scores are positive** and 7% negative. WOCAT records practices worth sharing,
  rated by the person who documented them. Split targets at the median, never at zero.
- Sites **cluster hard geographically** — group your cross-validation by country.
- Compiler averages span nearly two points on a seven-point scale. **Who filled in the form matters.**
- Section 9 runs the check that matters: for reported soil impact, environment alone scores 0.505
  macro-F1 and adding the practice gives 0.498. Knowing *what was done* adds nothing to knowing
  *where it was done* — worth confirming before designing a project around predicting impact.
