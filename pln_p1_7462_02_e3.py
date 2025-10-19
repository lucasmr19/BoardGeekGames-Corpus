#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import argparse
from collections import Counter
import utilities_corpus as utils
from bgg_corpus import MongoCorpusStorage

# ----------------------------
# Configuración por defecto
# ----------------------------
DEFAULT_OUTPUT_DIR = "data_corpus"
DEFAULT_OUTPUT_NAME = "bgg_corpus.json"
DEFAULT_MAX_WORKERS = 4
DEFAULT_GAMES = [1,2,3,4]

# ----------------------------
# CLI
# ----------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="Construir corpus y generar estadísticas."
    )
    parser.add_argument(
        "--games", nargs="+", type=int,  default=DEFAULT_GAMES,
        help="Lista de game_ids a procesar (ej: --games 2 224517)."
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Procesar todos los game_ids detectados en data_api/data_crawler."
    )
    parser.add_argument(
        "--output-dir", type=str, default=DEFAULT_OUTPUT_DIR,
        help=f"Directorio donde se guardará el JSON (por defecto: {DEFAULT_OUTPUT_DIR})."
    )
    parser.add_argument(
        "--output-name", type=str, default=DEFAULT_OUTPUT_NAME,
        help=f"Nombre del fichero JSON de salida (por defecto: {DEFAULT_OUTPUT_NAME})."
    )
    parser.add_argument(
        "--no-parallel", action="store_true",
        help="Desactivar procesamiento paralelo."
    )
    parser.add_argument(
        "--max-workers", type=int, default=DEFAULT_MAX_WORKERS,
        help=f"Número máximo de workers para procesamiento paralelo (por defecto: {DEFAULT_MAX_WORKERS})."
    )
    return parser.parse_args()


# ----------------------------
# Ejecución principal
# ----------------------------
if __name__ == "__main__":
    args = parse_args()
    
    # Asegurar directorio de salida
    os.makedirs(args.output_dir, exist_ok=True)

    # Construir path completo de salida
    output_path = os.path.join(args.output_dir, args.output_name)

    # Determinar lista de juegos a procesar
    if args.all:
        game_ids = utils.list_game_ids_from_dirs()
        if not game_ids:
            raise SystemExit("No se han encontrado game_ids en los directorios 'data_api' o 'data_crawler'.")
    elif args.games:
        game_ids = args.games
    else:
        env_gid = os.getenv("GAME_ID")
        if env_gid:
            game_ids = [int(env_gid)]
        else:
            raise SystemExit("Indica --games o --all, o setea la variable de entorno GAME_ID.")

    print(f"Procesando game_ids: {game_ids}")

    # Construir corpus multi-juego
    corpus, stats = utils.build_corpus(
        game_ids,
        source="crawler",
        parallel=not args.no_parallel,
        max_workers=args.max_workers,
    )
    
    # Estadísticas generales
    print("\n📊 Estadísticas generales")
    print("- Total de reseñas:", corpus.num_reviews())
    print("- Con rating:", corpus.num_reviews_rated())
    print("- Con texto:", corpus.num_reviews_commented())
    print("- Con rating y texto:", corpus.num_reviews_rated_and_commented())
    print("- Nº usuarios únicos:", corpus.num_unique_users())
    print("- Nº usuarios no únicos:", corpus.num_no_unique_users())
    print("- Algunos usuarios no únicos:", corpus.no_unique_users()[:10])

    # Distribución de ratings
    print("\n⭐ Distribución de ratings (top 10)")
    rating_dist = corpus.rating_distribution()
    for rating, count in sorted(rating_dist.items(), key=lambda x: -x[1])[:10]:
        print(f"  {rating:>4}: {count}")

    # Ejemplo de texto crudo
    print("\n📝 Ejemplo de texto crudo:")
    print(corpus.raw()[:5], "...\n")

    # Contextos
    print("🔍 Contextos de la palabra 'a' (window=3, primeros 5):")
    for ctx in corpus.contexts("a", window=3)[:5]:
        print(" ", ctx)

    print("\n⚖️ 5 Contextos más comunes entre 'good' y 'bad' (window=2):")
    print(corpus.common_contexts(["good", "bad"], window=2)[:5])

    # Frecuencia de palabras
    print("\n📌 Palabras más frecuentes (top 15):")
    for word, freq in corpus.most_common(15):
        print(f"  {word}: {freq}")

    # Dispersión léxica
    print("\n📈 Dispersión léxica: mostrando gráfico...")
    corpus.lexical_dispersion_plot(["good", "game", "player"])

    # Hapax legomena
    print("\n🟢 Hapax legomena (primeros 20):")
    print(corpus.hapaxes()[:20])

    # Longitudes de palabras
    print("\n📏 Distribución de longitudes de palabra (top 10):")
    length_dist = corpus.word_length_distribution()
    for length, count in sorted(length_dist.items())[:10]:
        print(f"  Longitud {length}: {count} ocurrencias")

    print("\n📊 Mostrando gráfico de longitudes...")
    corpus.plot_word_length_distribution()

    # N-gramas y collocations
    print("\n🔗 Bigramas más frecuentes (top 10):")
    for bg, freq in Counter(corpus.bigrams()).most_common(10):
        print(f"  {bg}: {freq}")

    print("\n🔗 Trigramas más frecuentes (top 5):")
    for tg, freq in Counter(corpus.trigrams()).most_common(5):
        print(f"  {tg}: {freq}")

    print("\n📎 Collocations más comunes (top 10):")
    for coll, freq in corpus.collocations(10):
        print(f"  {coll}: {freq}")

    # Comparativa entre categorías
    print("\n📂 Comparativa nª tokens por categorías:")
    corpus.print_category_stats()
    
    print("\n📂 Conteo de reviews por categorías:")
    corpus.print_review_counts()

    # Frecuencia de palabras
    print("\n📊 Visualización de frecuencia de palabras (top 30):")
    corpus.plot_frequency_distribution(30, title="Frecuencia de palabras en el corpus")

    # Guardado
    corpus.to_json(output_path)
    #corpus.save_to_mongo(MongoCorpusStorage())
    print(f"\n✅ Corpus construido con {len(corpus.documents)} reviews. Guardado en {output_path}")