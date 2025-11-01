# Downloaders Submodule

The `downloaders` submodule provides tools for **downloading board game data** from BoardGameGeek (BGG) using either a **web crawler** or the **official API**.

```
downloaders/
├── bgg_api.py       # Downloader using BGG XML API
├── bgg_crawler.py   # Web crawler using Selenium
```

---

## Overview of Methods

### 1. BGG Crawler (`bgg_crawler.py`)

- **Mechanism:** Uses **Selenium** to navigate BGG web pages and extract review data.

- **Capabilities:**

  - Full flexibility in filtering reviews:

    - `rated=0/1` → include/exclude unrated/rated reviews
    - `rating=num` → filter reviews by a specific rating between 1–10
    - `commented=0/1` → include/exclude reviews without comments

  - Can extract **timestamps** of reviews.
  - Supports **balanced downloads per game** (equal number of reviews per rating, double weight for neutral ratings 5–6) via `process_game_balanced`.

- **Trade-offs:**

  - Slower than the API due to browser rendering and page loading.
  - Requires a Chrome driver and proper Selenium setup.
  - Best suited when **fine-grained filtering** or **review-level timestamps** are needed.
  - Ideal for **balancing the dataset directly from the source**, avoiding natural imbalances (most reviews cluster around ratings 6–7, very few at extremes like 1 or 10).

- **Example Usage:**

```bash
python bgg_crawler.py --ids 50 51 52 --mode all --headless
```

---

### 2. BGG API (`bgg_api.py`)

- **Mechanism:** Uses the **official BGG XML API** to fetch game metadata and reviews.

- **Capabilities:**

  - Efficient extraction of **metadata** (game properties, designers, categories, mechanics).
  - Fast retrieval for **massive review datasets**.
  - Handles retries for `202 Processing` responses.

- **Limitations:**

  - Less flexible filtering; cannot easily exclude reviews by `rated`/`commented`.
  - Timestamps and advanced review flags may be limited or require extra parsing.
  - Not ideal for **balanced downloads per rating** — subsampling would be required afterward.

- **Example Usage:**

```bash
python bgg_api.py --ids 50 51 52 --mode all
```

---

## Key Differences

| Feature                   | Crawler                                            | API                          |
| ------------------------- | -------------------------------------------------- | ---------------------------- |
| Filtering options         | ✅ Flexible (`rated`, `commented`, rating, custom) | ❌ Limited                   |
| Timestamps extraction     | ✅ Can parse exact timestamps                      | ⚠ Partial or slower to parse |
| Metadata extraction       | ⚠ Slower, needs page parsing                       | ✅ Fast and structured       |
| Speed                     | ⚠ Slower                                           | ✅ Fast for large datasets   |
| Scale / Massive downloads | ⚠ Not optimal                                      | ✅ Better suited for bulk    |
| Balancing reviews         | ✅ Supports per-rating balanced downloads          | ❌ Needs post-processing     |
| Setup                     | Selenium + Chrome driver needed                    | Standard `requests` library  |

---

## Summary

- **Use the Crawler** when you need:

  - Fine-grained filtering of reviews.
  - Exact timestamps of user comments.
  - Balanced downloads per rating to handle natural review imbalances.
  - Controlled page-by-page scraping.

- **Use the API** when you need:

  - Rapid metadata extraction.
  - Large-scale review downloads.
  - Structured, reliable XML data with retries.

Both methods complement each other and can be combined depending on the **dataset size, filtering needs, and balancing requirements**.

---

## 🔍 Further Discussion: Using Both Downloaders Together

To build a **complete and consistent BGG corpus**, you should **run both downloaders** in sequence:

| Downloader                               | Purpose                                                                       | Essential Outputs                                                                                                                                                                   |
| :--------------------------------------- | :---------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 🕷️ `bgg_crawler.py`                      | Collects **review-level data** (ratings, comments, timestamps, balance stats) | Generates detailed per-rating stats such as:<br>`total_all`, `total_commented`, `total_rated`, `total_rated_and_commented`, `avgweight`, `numweights`, `poll_avg`, and `poll_votes` |
| 🌐 `bgg_api.py` (with `--mode metadata`) | Collects **game-level metadata**                                              | Provides structured data for game IDs, categories, designers, mechanics, and publication info                                                                                       |

Running both ensures that:

- The **crawler output** feeds detailed review-level information to the balancing phase.
- The **API metadata** enriches each `GameCorpus` with descriptive fields for downstream NLP or analytical tasks.

Each downloader saves its `.json` files automatically under:

| Path                 | Contents                     |
| :------------------- | :--------------------------- |
| `../../data/crawler` | Raw review data from crawler |
| `../../data/api`     | Metadata and/or API reviews  |

These files are later merged and standardized in **Phase 1** of the `build_corpus()` pipeline, as described in the [main README](../README.md#⚙️-data-preparation).

[⬅ Back to main README](../README.md)
