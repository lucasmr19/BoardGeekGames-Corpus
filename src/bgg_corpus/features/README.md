# Features Submodule

The `features` submodule provides tools for **feature extraction** from board game reviews. It supports **lexicon-based sentiment features, linguistic analysis, and vectorization** for machine learning.

```
features/
├── lexicons.py                # Sentiment and domain lexicons
├── linguistic_extractor.py    # Extract numeric and categorical linguistic features
├── vectorization.py           # TF-IDF and DictVectorizer for text and opinion features
└── __init__.py
```

---

## Lexicons

### `lexicons.py`

- Handles **loading and managing lexical resources** for board game reviews defined at `BoardGeekGames-Corpus/data/lexicons`.
- Includes:

  - **Sentiment words**: positive, negative
  - **Modifiers**: intensifiers, mitigators, negations
  - **Domain-specific terms**
  - **Hedges**: hedge words, propositional, relational, discourse markers

- Provides combined sets for fast access (e.g., `all_hedges`).
- These lexicons are used in downstream feature extraction to compute **counts, densities, and proximity-based metrics**.

---

## Linguistic Feature Extraction

### `linguistic_extractor.py`

- Extracts **rich linguistic and textual features** from processed reviews (`CorpusDocument`).
- Features include:

  - **Sentiment features**:

    - Counts of positive/negative words
    - Vader sentiment scores
    - Sentence-level sentiment statistics

  - **Syntactic features**:

    - Number of tokens
    - Average token length
    - Dependency depth and counts

  - **Lexical diversity**:

    - Type-token ratio
    - Hapax legomena ratio
    - Entropy of token distribution

  - **Readability and complexity**:

    - Flesch-Kincaid grade
    - Reading ease
    - Complex word ratio

  - **Hedging features**:

    - Counts by hedge type
    - Density of hedges
    - Relation to sentiment words

  - **Domain-specific co-occurrences** with sentiment terms
  - **POS ratios** (adjectives, adverbs, nouns, verbs)
  - **Negation scope** metrics
  - **Punctuation emphasis**

- Returns a **single dictionary of numeric and sequence features**, ready for vectorization.

---

## Vectorization

### `vectorization.py`

- Provides **vector representations** for ML models combining:

  - **Textual features**: TF-IDF over tokens
  - **Opinion/linguistic features**: DictVectorizer over feature dictionaries

- Multilingual-aware:

  - Adds **language prefixes** to tokens to avoid conflicts in TF-IDF.

- API:

  ```python
  vectorizer = ReviewVectorizer(max_features=5000, ngram_range=(1,2))
  X = vectorizer.fit_transform(tokens_per_doc, langs, opinion_features)
  X_new = vectorizer.transform(new_tokens, new_langs, new_opinion_features)
  ```

- Output: **sparse matrix** combining TF-IDF and opinion-based features.

---

## Summary

- `lexicons.py`: Load sentiment, hedges, and domain-specific lexicons from `BoardGeekGames-Corpus/data/lexicons`.
- `linguistic_extractor.py`: Compute **numeric, syntactic, lexical, and hedging features**.
- `vectorization.py`: Combine **text and opinion features** into a vector representation for ML pipelines.

This submodule enables **feature-rich, multilingual, and lexicon-aware representations** of board game reviews, ready for classification or regression tasks.

[⬅ Back to main README](../README.md)
