Here’s the **complete, polished `README.md`**, fully updated to match the actual implementation of `build_corpus()` and include the embedded workflow diagram:

---

````markdown
# BoardGameGeek Corpus creation (`bgg_corpus`)

This project builds a **structured corpus of BoardGameGeek (BGG) reviews**, integrating both metadata and user reviews from **crawler and API sources**, with support for **review preprocessing, balancing, and corpus assembly**.

---

## 1. Full Pipeline Overview

<p align="center">
  <img src="/BoardGeekGames-Corpus/docs/bgg_corpus_workflow.svg" alt="BoardGameGeek Corpus Workflow" width="100%">
</p>

```mermaid
%%{init: {'theme':'neutral','themeVariables':{ 'fontSize':'13px','nodeTextColor':'#333','primaryColor':'#e3eaf2','edgeLabelBackground':'#fff'}}}%%
flowchart TD
    %% STYLE CLASSES
    classDef dataSource fill:#d9e8ff,stroke:#003366,stroke-width:1px,color:#000,font-weight:bold
    classDef ingestion fill:#b8d8ff,stroke:#004c99,stroke-width:1px,color:#000
    classDef preprocessing fill:#c7f0c0,stroke:#1d632f,stroke-width:1px,color:#000
    classDef feature fill:#a8f0f8,stroke:#007c91,stroke-width:1px,color:#000
    classDef balancing fill:#ffd8a8,stroke:#b85c00,stroke-width:1px,color:#000
    classDef model fill:#e2c4ff,stroke:#6030b0,stroke-width:1px,color:#000
    classDef util fill:#d9d9d9,stroke:#666,stroke-width:1px,color:#000
    classDef storage fill:#e3b7eb,stroke:#803080,stroke-width:1px,color:#000
    classDef analysis fill:#cccccc,stroke:#333,stroke-width:1px,color:#000

    %% DATA SOURCES
    subgraph "Data Sources"
        API["BGG API JSON"]:::dataSource
        CRAWLER["BGG Crawler JSON"]:::dataSource
        RAWCSV["Boardgames Ranks CSV"]:::dataSource
        LEX["Lexicon Files"]:::dataSource
    end

    %% INGESTION LAYER
    subgraph "Ingestion Layer"
        API_D["API Downloader"]:::ingestion
        CRAWLER_D["Crawler Downloader"]:::ingestion
        NLTK_DL["NLTK Resource Downloader"]:::ingestion
    end

    %% PREPROCESSING LAYER
    subgraph "Preprocessing Layer"
        CLEAN["Cleaning"]:::preprocessing
        LANG_DET["Language Detection"]:::preprocessing
        SEGMENT["Tokenization / Segmentation"]:::preprocessing
        STEM["Stemming"]:::preprocessing
        REGISTRY["Tokenizer Registry"]:::preprocessing
        REVIEW_PROC["Review Processor"]:::preprocessing
        SPACY_UTILS["spaCy Utilities"]:::preprocessing
        SPACY_ANAL["spaCy-based Analysis"]:::preprocessing
    end

    %% FEATURE EXTRACTION
    subgraph "Feature Extraction"
        LEX_LOADER["Lexicon Loader"]:::feature
        LING_FEAT["Linguistic Feature Extractor"]:::feature
        VECT["Vectorization"]:::feature
    end

    %% BALANCING & LABELING
    subgraph "Balancing & Labeling"
        SINGLE_BAL["Single-game Balancing"]:::balancing
        MULTI_BAL["Multi-game Balancing"]:::balancing
        AUG["Data Augmentation"]:::balancing
        HELPERS["Balancing Helpers"]:::balancing
        SAVE_BAL["Save Balance Report"]:::balancing
    end

    %% CORPUS & MODELS
    subgraph "Corpus & Model Abstractions"
        CORPUS["Corpus Model"]:::model
        GAME_CORPUS["GameCorpus"]:::model
        REVIEW_DOC["Review"]:::model
        CORPUS_DOC["CorpusDocument"]:::model
        CLI["CLI Entrypoint"]:::model
        CONFIG["Config Definitions"]:::model
    end

    %% UTILITIES & RESOURCES
    subgraph "Utilities & Resources"
        UTIL_CB["Corpus Builder"]:::util
        UTIL_IO["I/O Helpers"]:::util
        UTIL_META["Metadata Utils"]:::util
        UTIL_PROC["Processing Utils"]:::util
        UTIL_REV["Review Utils"]:::util
        RESOURCES["Packaged Resources"]:::util
    end

    %% STORAGE / PERSISTENCE
    subgraph "Storage / Persistence"
        MONGO["MongoDB Backend"]:::storage
        JSON_CORP["JSON Corpora Export"]:::storage
        DATASETS["Train/Val/Test Datasets"]:::storage
        VECT_EXPORT["Vector & Vectorizer Exports"]:::storage
    end

    %% ANALYSIS / DOWNSTREAM
    subgraph "Analysis / Downstream"
        NOTEBOOKS["Jupyter Notebooks"]:::analysis
        SCRIPTS["Analysis Scripts"]:::analysis
    end

    %% MAIN DATA FLOW
    API -->|JSON| API_D
    CRAWLER -->|JSON| CRAWLER_D
    RAWCSV -->|CSV| API_D
    API_D --> CLEAN
    CRAWLER_D --> CLEAN
    NLTK_DL --> CLEAN
    CLEAN --> LANG_DET --> SEGMENT --> STEM --> REGISTRY --> REVIEW_PROC --> SPACY_UTILS --> SPACY_ANAL
    SPACY_ANAL --> LEX_LOADER --> LING_FEAT --> VECT
    LEX --> LEX_LOADER
    LEX --> CLEAN
    VECT --> SINGLE_BAL --> MULTI_BAL --> AUG --> HELPERS --> SAVE_BAL
    SAVE_BAL --> CORPUS_DOC --> REVIEW_DOC --> GAME_CORPUS --> CORPUS
    CORPUS --> UTIL_CB
    UTIL_CB --> CLI
    CONFIG --> CLI
    CLI --> JSON_CORP
    CLI --> MONGO
    JSON_CORP --> DATASETS --> VECT_EXPORT
    MONGO --> NOTEBOOKS
    MONGO --> SCRIPTS
    VECT_EXPORT --> NOTEBOOKS
    VECT_EXPORT --> SCRIPTS

    %% CLICKABLE LINKS (optional for GitHub Markdown)
    click API "data/api/"
    click CRAWLER "data/crawler/"
    click RAWCSV "data/raw/boardgames_ranks.csv"
    click LEX "data/lexicons/"
    click API_D "src/bgg_corpus/downloaders/bgg_api.py"
    click CRAWLER_D "src/bgg_corpus/downloaders/bgg_crawler.py"
    click CLEAN "src/bgg_corpus/preprocessing/cleaning.py"
    click LANG_DET "src/bgg_corpus/preprocessing/language/detection.py"
    click SPACY_UTILS "src/bgg_corpus/preprocessing/language/spacy_utils.py"
    click SEGMENT "src/bgg_corpus/preprocessing/tokenization/segmentation.py"
    click STEM "src/bgg_corpus/preprocessing/tokenization/stemming.py"
    click REGISTRY "src/bgg_corpus/preprocessing/tokenization/tokenizers_registry.py"
    click REVIEW_PROC "src/bgg_corpus/preprocessing/review_processor.py"
    click SPACY_ANAL "src/bgg_corpus/preprocessing/spacy_analysis.py"
    click LEX_LOADER "src/bgg_corpus/features/lexicons.py"
    click LING_FEAT "src/bgg_corpus/features/linguistic_extractor.py"
    click VECT "src/bgg_corpus/features/vectorization.py"
    click SINGLE_BAL "src/bgg_corpus/balancing/single_game_balance.py"
    click MULTI_BAL "src/bgg_corpus/balancing/multi_game_balance.py"
    click AUG "src/bgg_corpus/balancing/augmentation.py"
    click HELPERS "src/bgg_corpus/balancing/helpers.py"
    click SAVE_BAL "src/bgg_corpus/balancing/save_balance.py"
    click CORPUS "src/bgg_corpus/models/corpus.py"
    click GAME_CORPUS "src/bgg_corpus/models/game_corpus.py"
    click REVIEW_DOC "src/bgg_corpus/models/review.py"
    click CORPUS_DOC "src/bgg_corpus/models/corpus_document.py"
    click CLI "src/bgg_corpus/cli.py"
    click CONFIG "src/bgg_corpus/config.py"
    click MONGO "src/bgg_corpus/storage/mongodb_storage.py"
    click JSON_CORP "data/processed/corpora/"
    click DATASETS "data/processed/datasets/"
    click VECT_EXPORT "data/processed/vectors/"
    click NOTEBOOKS "notebooks/"
    click SCRIPTS "scripts/"
```

---

## 2. Pipeline Summary

1. **Downloaders:** Extract raw reviews and metadata using the **crawler** or **API**.
2. **Utilities:** Merge reviews, load metadata, standardize text, and build corpus objects.
3. **Balancing:** Apply oversampling, undersampling, or hybrid strategies to handle rating imbalance.
4. **Preprocessing:** Clean, normalize, and label review text via `process_single_review()`.
5. **Corpus Assembly:** Construct hierarchical corpus objects ready for downstream analysis.

---

## 3. Modules Overview

## 3. Modules Overview

| Module                                         | Purpose                                                      | Documentation                     |
| ---------------------------------------------- | ------------------------------------------------------------ | --------------------------------- |
| **[downloaders](./downloaders/README.md)**     | Fetch reviews and metadata from BGG (crawler/API).           | [docs](./downloaders/README.md)   |
| **[utilities](./utilities/README.md)**         | Load/merge reviews, build metadata, and assemble corpus.     | [docs](./utilities/README.md)     |
| **[preprocessing](./preprocessing/README.md)** | Clean and normalize review text.                             | [docs](./preprocessing/README.md) |
| **[balancing](./balancing/README.md)**         | Balance review distribution by ratings.                      | [docs](./balancing/README.md)     |
| **[models](./models/README.md)**               | Define `Corpus`, `GameCorpus`, and `CorpusDocument` classes. | [docs](./models/README.md)        |
| **[features](./features/README.md)**           | Handle linguistic and vector representations.                | [docs](./features/README.md)      |
| **[storage](./storage/README.md)**             | Save and load corpora from MongoDB or disk.                  | [docs](./storage/README.md)       |

---

## 4. CLI Usage (`cli.py`)

```bash
# Build corpus for games 50, 51, 52 with default settings
python cli.py --games 50 51 52 --save-json --generate-stats

# Build corpus using hybrid balance, enable augmentation
python cli.py --games 50 51 52 --balance-strategy hybrid --use-augmentation

# Use API-only reviews and disable parallel processing
python cli.py --games 50 51 52 --source api --no-parallel
```
````

**Key Options:**

| Option                         | Description                                           |
| ------------------------------ | ----------------------------------------------------- |
| `--games`                      | List of BGG game IDs                                  |
| `--source`                     | `"crawler"`, `"api"`, or `"combined"`                 |
| `--balance-strategy`           | `"oversample"`, `"undersample"`, `"hybrid"`           |
| `--use-augmentation`           | Enable text augmentation for underrepresented ratings |
| `--save-json` / `--save-mongo` | Save corpus as JSON or MongoDB                        |
| `--generate-stats`             | Print corpus and balancing statistics                 |

---

## 5. Corpus Building Workflow

The `build_corpus()` function constructs the complete BGG review corpus in **four main phases**:

### **Phase 1 — Review Collection & Balancing**

- Merge API and crawler reviews with `merge_reviews()`.
- Apply `collect_balanced_reviews_multi_game()` to handle rating imbalances (oversample / undersample / hybrid).
- Optionally perform text augmentation.
- Save balancing reports via `save_balance_report()`.

### **Phase 2 — Grouping & Preparation**

- Standardize each review object with `ensure_review_obj()`.
- Group reviews by `game_id` into a structured dictionary for processing.

### **Phase 3 — Per-Game Processing**

- For each game:

  - Build metadata with `build_metadata()`.
  - Create a `GameCorpus` instance.
  - Convert reviews into `CorpusDocument` objects using `process_single_review()`.
  - Optionally parallelize processing with `ProcessPoolExecutor`.

### **Phase 4 — Assembly & Return**

- Aggregate all `GameCorpus` objects into a top-level `Corpus`.
- Compute total processed documents.
- Return the tuple `(Corpus, stats)`.

**Final Output Structure:**

```
Corpus
 ├─ GameCorpus (game_id)
 │   ├─ CorpusDocument (review)
 │   └─ ...
 └─ GameCorpus
 ...
```

---

## 6. Configuration (`config.py`)

Main configuration paths and constants

---

## 7. Example Python Usage

```python
from bgg_corpus.utilities import build_corpus

corpus, stats = build_corpus(
    game_ids=[50, 51, 52],
    source="combined",
    balance_strategy="hybrid",
    use_augmentation=True,
    parallel=True,
    max_workers=4
)

print(f"Total reviews processed: {sum(len(g.documents) for g in corpus.games)}")
```

---

## 8. Notes

- **Crawler** → Preferred for fine-grained review filtering (rated/commented/neutral).
- **API** → Best for fast large-scale metadata & review extraction.
- **Utilities** → Centralized helpers for merging, metadata, and preprocessing.
- **Preprocessing** → Ensures consistent, clean review text for analysis.
- **Balancing** → Addresses skewed rating distributions (e.g., few 1s or 10s, many 6s–7s).
- **Parallelism** → Accelerates review processing for large datasets.
