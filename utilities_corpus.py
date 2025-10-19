import os
import json
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial
from collections import defaultdict
import preprocessing_corpus as pp
from bgg_corpus import Review, CorpusDocument, GameCorpus, Corpus
from balance_corpus import collect_balanced_reviews_multi_game, save_balance_report

BGG_STATS = "data_crawler/bgg_stats.csv"
DATA_API_DIR = "data_api"
DATA_CRAWLER_DIR = "data_crawler"
BGG_RANKS = "boardgames_ranks.csv"
DEFAULT_OUTPUT = "data_corpus/bgg_corpus_multi.json"

# carga CSVs globalmente para performance
ranks_df = pd.read_csv(BGG_RANKS)
stats_df = pd.read_csv(BGG_STATS)

# ----------------------------
# Utilidades de I/O
# ----------------------------
def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)

# ----------------------------
# Metadata y reviews por juego
# ----------------------------
def load_metadata_from_api(game_id, data_api_dir=DATA_API_DIR):
    meta_file = os.path.join(data_api_dir, f"bgg_metadata_{game_id}_api.json")
    return load_json(meta_file) or {}

def build_metadata(game_id):
    """Construye metadata agrupada (game_info, stats, rankings, polls) para un game_id."""
    game_metadata = load_metadata_from_api(game_id)

    # ranks (from boardgames_ranks.csv)
    rank_row = ranks_df[ranks_df["id"] == game_id] if not ranks_df.empty else pd.DataFrame()
    rank_data = rank_row.iloc[0].to_dict() if not rank_row.empty else {}
    rank_data = {k: (None if pd.isna(v) else v) for k, v in rank_data.items()}

    # stats (from bgg_stats.csv)
    stats_row = stats_df[stats_df["game_id"] == game_id] if not stats_df.empty else pd.DataFrame()
    stats_data = stats_row.iloc[0].to_dict() if not stats_row.empty else {}
    stats_data = {k: (None if pd.isna(v) else v) for k, v in stats_data.items()}

    meta_raw = {**(game_metadata or {}), **rank_data, **stats_data}
    classifications_raw = meta_raw.get("classifications", {})

    metadata = {
        "game_info": {
            #"id": meta_raw.get("id", game_id),
            "name": meta_raw.get("name"),
            "yearpublished": meta_raw.get("yearpublished"),
            "minplayers": meta_raw.get("minplayers"),
            "maxplayers": meta_raw.get("maxplayers"),
            "minplaytime": meta_raw.get("minplaytime"),
            "maxplaytime": meta_raw.get("maxplaytime"),
            "age": meta_raw.get("age"),
            "description": meta_raw.get("description"),
            "image": meta_raw.get("image"),
            "thumbnail": meta_raw.get("thumbnail"),
            "designers": meta_raw.get("designers", []),
            "artists": meta_raw.get("artists", []),
            "publishers": meta_raw.get("publishers", []),
            "is_expansion": bool(meta_raw.get("is_expansion", 0))
        },
        "stats": {
            "num_reviews": meta_raw.get("total_all"),
            "num_reviews_commented": meta_raw.get("total_commented"),
            "num_reviews_rated": meta_raw.get("total_rated"),
            "num_reviews_rated_and_commented": meta_raw.get("total_rated_and_commented"),
            "avg_rating": meta_raw.get("average"),
            "bayes_average": meta_raw.get("bayesaverage"),
            "avg_weight": meta_raw.get("avgweight"),
            "num_weights": meta_raw.get("numweights")
        },
        "rankings": {
            "overall_rank": meta_raw.get("rank"),
            "strategygames_rank": meta_raw.get("strategygames_rank"),
            "thematic_rank": meta_raw.get("thematic_rank"),
            "familygames_rank": meta_raw.get("familygames_rank"),
            "partygames_rank": meta_raw.get("partygames_rank"),
            "cgs_rank": meta_raw.get("cgs_rank"),
            "childrensgames_rank": meta_raw.get("childrensgames_rank"),
            "abstracts_rank": meta_raw.get("abstracts_rank"),
            "wargames_rank": meta_raw.get("wargames_rank")
        },
        "classifications": {
            "mechanics": classifications_raw.get("mechanics", []),
            "categories": classifications_raw.get("categories", []),
            "families": classifications_raw.get("families", [])
        },
        "polls": {
            "complexity_poll": {
                "poll_avg": meta_raw.get("poll_avg"),
                "poll_votes": meta_raw.get("poll_votes")
            }
        }
    }
    return metadata

# ----------------------------
# Merge reviews (API + crawler) por juego
# ----------------------------
def merge_reviews(game_id, source="combined", data_api_dir=DATA_API_DIR, data_crawler_dir=DATA_CRAWLER_DIR):
    """
    Carga y mezcla reseñas del crawler y de la API para un game_id.
    Normaliza comentarios para key de merge (pre_normalize + pp.normalize_text).
    """
    api_file = os.path.join(data_api_dir, f"bgg_reviews_{game_id}_api.json")
    crawler_file = os.path.join(data_crawler_dir, f"bgg_reviews_{game_id}_crawler.json")

    data_api = load_json(api_file)
    data_crawler = load_json(crawler_file)

    reviews_api = data_api.get("comments", []) if isinstance(data_api, dict) else data_api

    merged = {}

    def normalized_key(username, comment):
        # pre-normalize (decode html, replace thing tags) then pasar por pp.normalize_text
        norm_comment = pp.normalize_text(comment, lower=True, correct_spelling=False)
        return (username.strip().lower(), norm_comment)

    # crawler primero (trae timestamp)
    if source in ("crawler", "combined"):
        for r in data_crawler:
            user = r.get("username", "unknown")
            comment = r.get("comment", "") or ""
            key = normalized_key(user, comment)
            merged[key] = Review(
                username=user,
                rating=r.get("rating"),
                comment=comment,
                timestamp=r.get("timestamp"),
                game_id=game_id
            )

    # luego API (enriquece)
    if source in ("api", "combined"):
        for r in reviews_api:
            user = r.get("username", "unknown")
            comment = r.get("comment", "") or ""
            key = normalized_key(user, comment)
            rating_api = r.get("rating")

            # saltar si rating no válido
            if rating_api in (None, "N/A"):
                continue

            if key in merged:
                review = merged[key]
                # preferir comment de la API si trae shortcodes de emoji
                if r.get("comment") and ":" in r["comment"]:
                    review.comment = r["comment"]
            else:
                # si no existe en merged, lo añadimos (sin timestamp porque API no lo trae)
                merged[key] = Review(
                    username=user,
                    rating=rating_api,
                    comment=comment,
                    timestamp=None,
                    game_id=game_id
                )

    return list(merged.values())

# ----------------------------
# Procesamiento de reseña -> CorpusDocument
# ----------------------------
def process_single_review(review_item):
    """
    Procesa un Review o un dict en un CorpusDocument.
    Acepta:
      - instancia de Review
      - dict con keys 'username','rating','raw_text'/'comment','timestamp','game_id'
    Devuelve CorpusDocument o None.
    """
    # normalizar input: reconstruir Review si viene dict
    if isinstance(review_item, dict):
        rev = Review.from_dict(review_item)
    else:
        rev = review_item

    processed = None
    if (rev.comment or "").strip():
        # aplicar pre_normalize antes de procesar para asegurar [thing] y html fixes
        processed = pp.process_review_item(
            {
                "username": rev.username,
                "rating": rev.rating,
                "timestamp": rev.timestamp,
                "raw_text": rev.comment
            },
            lower=True,
            remove_stopwords=True,
            lemmatize=True,
            correct_spelling=False
        )
        # inyectar label en processed para consistencia
        processed.setdefault("label", getattr(rev, "label", None))
    return CorpusDocument(rev, processed) if processed else None


# ----------------------------
# Build corpus multi-juego (modular)
# ----------------------------
def build_corpus(
    game_ids,
    source="combined",
    balance_strategy='hybrid',
    min_samples_for_balance=30,
    per_game_cap=1000,
    per_game_max_per_class=400,
    target_ratio=None,
    parallel=True,
    max_workers=4,
    save_report=True
):
    """
    Construye el corpus BGG completo combinando recolección balanceada multi-juego
    + procesamiento paralelo de reseñas.
    """

    print("===============================================")
    print("FASE 1: Recolección y balanceo por juego")
    print(f"Estrategia: {balance_strategy}")
    print(f"Caps: {per_game_cap} total, {per_game_max_per_class} por clase")
    print(f"Paralelismo: {parallel} ({max_workers} workers)")
    print("===============================================")

    # 1️⃣ Recolectar y balancear reseñas por juego
    merge_func = partial(merge_reviews, source=source)

    collected_reviews, stats = collect_balanced_reviews_multi_game(
        all_game_ids=game_ids,
        merge_reviews_func=merge_func,
        min_samples_for_balance=min_samples_for_balance,
        balance_strategy=balance_strategy,
        per_game_cap=per_game_cap,
        per_game_max_per_class=per_game_max_per_class,
        target_ratio=target_ratio,
        source=source,
        verbose=True
    )

    if save_report:
        save_balance_report(stats)

    # 2️⃣ Procesar reseñas a CorpusDocument
    print("\nFASE 2: Procesamiento a CorpusDocument")

    game_groups = defaultdict(list)
    for r in collected_reviews:
        gid = getattr(r, 'game_id', None)
        if gid:
            game_groups[gid].append(r)

    games = []

    def _ensure_review_obj(r, gid):
        """Convierte Review o dict a formato estándar."""
        if isinstance(r, dict):
            out = dict(r)
            out["game_id"] = gid
            out.setdefault("raw_text", out.get("comment", ""))
            return out
        return {
            "username": getattr(r, "username", "unknown"),
            "rating": getattr(r, "rating", None),
            "comment": getattr(r, "comment", ""),
            "raw_text": getattr(r, "raw_text", ""),
            "timestamp": getattr(r, "timestamp", None),
            "game_id": gid
        }

    for gid, reviews in tqdm(game_groups.items(), desc="Creando GameCorpus"):
        meta = build_metadata(gid)
        game_corpus = GameCorpus(game_id=gid, metadata=meta, documents=[])

        if parallel and len(reviews) > 0:
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for r in reviews:
                    rev_dict = _ensure_review_obj(r, gid)
                    futures[executor.submit(process_single_review, rev_dict)] = rev_dict

                for f in tqdm(as_completed(futures), total=len(futures),
                              desc=f"Procesando reseñas juego {gid}", leave=False):
                    try:
                        doc = f.result()
                        if doc:
                            doc.review.game_id = gid
                            doc.review.fileid = gid
                            doc.fileid = gid
                            game_corpus.add_document(doc)
                    except Exception as e:
                        print(f"⚠️ Error procesando reseña en juego {gid}: {e}")
        else:
            for r in tqdm(reviews, desc=f"Procesando reseñas juego {gid}", leave=False):
                rev_dict = _ensure_review_obj(r, gid)
                doc = process_single_review(rev_dict)
                if doc:
                    doc.review.game_id = gid
                    doc.review.fileid = gid
                    doc.fileid = gid
                    game_corpus.add_document(doc)

        games.append(game_corpus)

    print("\n✅ Corpus construido correctamente.")
    print(f"Juegos: {len(games)} | Documentos totales: {sum(len(g.documents) for g in games)}")

    return Corpus(games=games), stats

# CONFIGURACIONES RECOMENDADAS SEGÚN ESCENARIO:

# Escenario 1: Pocas negativos, quieres maximizar
CONFIG_MAXIMIZE_MINORITY = {
    'balance_strategy': 'adaptive',
    'min_samples_for_balance': 20,
    'per_game_cap': 1500,
    'per_game_max_per_class': 600,
    'target_ratio': None  # adaptativo automático
}

# Escenario 2: Balance estricto, dispuesto a perder positivos
CONFIG_STRICT_BALANCE = {
    'balance_strategy': 'adaptive',
    'min_samples_for_balance': 30,
    'per_game_cap': 900,
    'per_game_max_per_class': 300,
    'target_ratio': 0.8  # 80% del máximo
}

# Escenario 3: Conservador, poco procesamiento
CONFIG_CONSERVATIVE = {
    'balance_strategy': 'none',
    'min_samples_for_balance': 50,
    'per_game_cap': 2000,
    'per_game_max_per_class': 1000,
    'target_ratio': None
}