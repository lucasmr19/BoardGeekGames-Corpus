# 🧩 BoardGeekGames Corpus

**BoardGeekGames Corpus** is a Python project for building and analyzing an annotated textual corpus of **board game reviews**.  
It focuses on sentiment analysis, linguistic annotation, and lexicon-based modeling from user-generated content gathered from [BoardGameGeek](https://boardgamegeek.com).

## 🚀 Overview

This project automates the **collection, processing, and annotation** of board game reviews to create a reusable **linguistic corpus** for NLP and sentiment classification tasks.

- **Corpus construction** from multiple sources (crawler/API).
- **Text preprocessing**: cleaning, normalization, tokenization, lemmatization, POS tagging.
- **Linguistic annotation**: sentiment, negations, intensifiers, domain terms, hedges.
- **Balanced datasets** for supervised sentiment classification.
- **Vectorization and modeling**: TF-IDF, opinion features, and classifiers.

For more details on the core corpus creation pipeline, see the **[bgg_corpus README](./src/bgg_corpus/README.md)**.

## 📁 Project Structure

```

BoardGeekGames-Corpus/
├── README.md
├── requirements.txt
├── data/
│   ├── api/                  # API metadata JSONs
│   ├── crawler/              # Crawler reviews JSONs and stats
│   ├── lexicons/             # Sentiment, hedge, domain lexicons
│   ├── processed/            # Balanced corpora, datasets, vectors, models
│   └── raw/                  # Original CSV and JSON files
├── docs/
├── notebooks/
├── scripts/                  # Executables post-corpus creation
├── src/
│   └── bgg_corpus/           # Core Python package
│       ├── preprocessing/    # Cleaning, tokenization, spaCy analysis
│       ├── features/         # Lexicons, vectorization
│       ├── models/           # Corpus and document classes
│       ├── utilities/        # Helpers, corpus builder
│       ├── balancing/        # Oversampling/undersampling/augmentation
│       ├── storage/          # MongoDB storage
│       └── downloaders/      # Crawler/API downloaders
└── tests/

````

## ⚙️ Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/lucasmr19/BoardGeekGames-Corpus.git
cd BoardGeekGames-Corpus
pip install -r requirements.txt
````

## 🧠 Project Goals

* Build a **domain-specific sentiment corpus** for board game reviews.
* Extract and annotate **linguistic and lexical features** for NLP.
* Provide structured datasets for **sentiment classification**.
* Offer an extensible framework for **feature engineering** and **corpus analysis**.

## 🛠 Scripts and Their Functionality

1. **Linguistic Feature Extraction**

   * Extract sentiment, negations, intensifiers, domain terms, hedges, etc.
   * Saved in the corpus.
   * ⚠️ **Note:** Redundant—these features are already computed in the main preprocessing pipeline:
     [`review_processor.py`](./src/bgg_corpus/preprocessing/review_processor.py).

   ```bash
   python scripts/pln_p2_7462_02_e1.py
   ```

2. **Vector Representation of Reviews**

   * TF-IDF n-grams + opinion/sentiment features.
   * Generates combined sparse vectors.

   ```bash
   python scripts/pln_p2_7462_02_e2.py \
       --corpus path/to/bgg_corpus.json \
       --output_dir path/to/save/vectors \
       --max_features 8000 \
       --ngram_range 1 2
   ```

3. **Dataset Creation**

   * Split corpus into train, validation, and test datasets.

   ```bash
   python scripts/pln_p2_7462_02_e3.py \
       --corpus_path data/bgg_corpus.json \
       --output_dir data/processed/datasets \
       --train_ratio 0.7 \
       --val_ratio 0.15 \
       --test_ratio 0.15 \
       --seed 42 \
       --format json \
       --verbose
   ```

4. **Classification Model Training**

   * Trains models to predict review polarity.
   * Implements:

     * Multinomial Naive Bayes
     * LinearSVC
     * Random Forest
     * XGBoost (if available)
   * Uses different feature subsets: TF-IDF, sentiment features, or both.

   ```bash
   python scripts/pln_p2_7462_02_e4.py \
       --vector_dir path/to/vectors \
       --output_dir path/to/models
   ```

5. **Model Evaluation and Report**

   * Performs evaluation on train/test/val splits.
   * Generates classification metrics and confusion matrices.
   * Creates a comprehensive technical report.

   ```bash
   python scripts/pln_p2_7462_02_e5.py \
       --vector_dir path/to/vectors \
       --dataset_dir path/to/datasets \
       --models_dir path/to/models \
       --output_dir path/to/results
   ```

## 📌 Key Notes

* The **core corpus pipeline** is in [`src/bgg_corpus/utilities/corpus_builder.py`](./src/bgg_corpus/utilities/corpus_builder.py).
* All preprocessing is handled via [`process_single_review`](./src/bgg_corpus/utilities/processing_utils.py) → generates **[`CorpusDocument`](./src/bgg_corpus/models/corpus_document.py) objects**.
* The scripts leverage the corpus and extracted features but **do not repeat preprocessing**.
* Corpus supports **multi-language preprocessing**, **balancing**, and **parallel processing** for scalability.

## License
This project is licensed under the [MIT License](LICENSE).
