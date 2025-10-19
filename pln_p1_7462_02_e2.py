#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import os
import pandas as pd
import xml.etree.ElementTree as ET
import json
import time
import logging

# ----------------------------
# Configuración
# ----------------------------

BGG_RANKS = "boardgames_ranks.csv"
ranks_df = pd.read_csv(BGG_RANKS)
ALL_GAME_IDS = ranks_df["id"].tolist() # Todos los juegos 
IDS = [1, 3] # Juegos a probar
GAME_IDS = ranks_df[ranks_df["id"].isin(IDS)]["id"].tolist() # Lista de IDs de juegos a analizar
MAX_PAGES = None        # Número máximo de páginas de comentarios (None = sin límite)
RETRY_WAIT = 2
RETRIES = 5
OUTPUT_DIR = "data_api"


os.makedirs(OUTPUT_DIR, exist_ok=True)


# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ----------------------------
# Funciones auxiliares
# ----------------------------
def fetch_with_retry(url, retries=RETRIES, wait=RETRY_WAIT):
    """Hace una petición a la API BGG con reintentos si devuelve 202 (procesando)."""
    for attempt in range(retries):
        response = requests.get(url)
        if response.status_code == 200:
            return response
        elif response.status_code == 202:
            logger.info(f"Reintentando URL (procesando) {url}... intento {attempt + 1}")
            time.sleep(wait)
        else:
            response.raise_for_status()
    raise Exception(f"No se pudo obtener respuesta válida de la API para {url}.")

def parse_text(element):
    """Obtiene el texto de un elemento XML, devuelve 'N/A' si no existe."""
    return element.text if element is not None else "N/A"

# ----------------------------
# Funciones de extracción
# ----------------------------

def get_text(game_xml, tag):
    """Obtiene el texto de un campo XML, devuelve 'N/A' si no existe."""
    element = game_xml.find(tag)
    return element.text if element is not None else "N/A"

def get_name(game_xml):
    """Devuelve el nombre principal del juego."""
    name_elem = game_xml.find("name[@primary='true']")
    return name_elem.text if name_elem is not None else "N/A"

def extract_metadata(game_xml, game_id):
    """Extrae los metadatos de un juego a partir del XML (sin comentarios)."""
    
    # Función auxiliar para obtener texto
    def get_text(element, tag):
        el = element.find(tag)
        return el.text if el is not None else "N/A"

    # Extraer clasificaciones en un subdiccionario
    classifications = {
        "mechanics": [elem.text for elem in game_xml.findall("boardgamemechanic")],
        "categories": [elem.text for elem in game_xml.findall("boardgamecategory")],
        "families": [elem.text for elem in game_xml.findall("boardgamefamily")]
    }

    # Construir diccionario principal de metadata
    metadata = {
        "id": game_id,
        "name": get_name(game_xml),
        "yearpublished": get_text(game_xml, "yearpublished"),
        "minplayers": get_text(game_xml, "minplayers"),
        "maxplayers": get_text(game_xml, "maxplayers"),
        "minplaytime": get_text(game_xml, "minplaytime"),
        "maxplaytime": get_text(game_xml, "maxplaytime"),
        "age": get_text(game_xml, "age"),
        "description": get_text(game_xml, "description"),
        "image": get_text(game_xml, "image"),
        "thumbnail": get_text(game_xml, "thumbnail"),
        "publishers": [p.text for p in game_xml.findall("boardgamepublisher")],
        "designers": [d.text for d in game_xml.findall("boardgamedesigner")],
        "artists": [a.text for a in game_xml.findall("boardgameartist")],
        "classifications": classifications  # <-- Aquí metemos el subdiccionario
    }

    return metadata

def save_metadata(metadata, game_id):
    """Guarda los metadatos de un juego en JSON."""
    output_file = f"{OUTPUT_DIR}/bgg_metadata_{game_id}_api.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)
    logger.info(f"Metadatos guardados en {output_file}")

def save_reviews(comments, game_id):
    """Guarda las reviews de un juego en JSON."""
    output_file = f"{OUTPUT_DIR}/bgg_reviews_{game_id}_api.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(comments, f, ensure_ascii=False, indent=4)
    logger.info(f"{len(comments)} comentarios guardados en {output_file}")

def extract_comments(game_id, max_pages=MAX_PAGES):
    """Descarga todas las reseñas de un juego (con comentarios incluidos) con paginación."""
    comments = []
    page = 1

    while True:
        if max_pages is not None and page > max_pages:
            logger.info(f"Límite de {max_pages} páginas alcanzado para juego {game_id}.")
            break

        url = f"https://boardgamegeek.com/xmlapi/boardgame/{game_id}?comments=1&page={page}"
        response = fetch_with_retry(url)
        root = ET.fromstring(response.content)
        game_xml = root.find('boardgame')
        page_comments = game_xml.findall('comment')

        if not page_comments:
            logger.info(f"No hay más comentarios disponibles en página {page} para juego {game_id}.")
            break

        for comment in page_comments:
            raw_rating = comment.attrib.get('rating', 'N/A')
            try:
                rating = float(raw_rating)
            except (TypeError, ValueError):
                rating = None
            comments.append({
                "username": comment.attrib.get('username', 'N/A'),
                "rating": rating,
                "comment": comment.text.strip() if comment.text else ''
            })

        logger.info(f"Juego {game_id}: página {page} descargada con {len(page_comments)} comentarios.")
        page += 1

    return comments

def save_to_json(data, game_id):
    """Guarda los datos en un archivo JSON."""
    output_file = f"{OUTPUT_DIR}/bgg_reviews_{game_id}_api.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logger.info(f"Guardados {len(data['comments'])} comentarios en {output_file}")

# ----------------------------
# Flujo principal
# ----------------------------
def process_game(game_id):
    """Procesa un juego: descarga metadatos y comentarios por separado."""
    logger.info(f"Procesando juego {game_id}...")

    # --- Metadatos ---
    url_game = f"https://boardgamegeek.com/xmlapi/boardgame/{game_id}"
    response = fetch_with_retry(url_game)
    root = ET.fromstring(response.content)
    game_xml = root.find("boardgame")
    metadata = extract_metadata(game_xml, game_id)
    save_metadata(metadata, game_id)

    # --- Comentarios ---
    comments = extract_comments(game_id)
    save_reviews(comments, game_id)

# ----------------------------
# Descarga independiente
# ----------------------------
def process_metadata_only(game_id):
    """Descarga y guarda solo los metadatos de un juego."""
    logger.info(f"Procesando metadata del juego {game_id}...")
    url_game = f"https://boardgamegeek.com/xmlapi/boardgame/{game_id}"
    response = fetch_with_retry(url_game)
    root = ET.fromstring(response.content)
    game_xml = root.find("boardgame")
    metadata = extract_metadata(game_xml, game_id)
    save_metadata(metadata, game_id)


def process_reviews_only(game_id, max_pages=MAX_PAGES):
    """Descarga y guarda solo las reviews de un juego."""
    logger.info(f"Procesando reseñas del juego {game_id}...")
    comments = extract_comments(game_id, max_pages=max_pages)
    save_reviews(comments, game_id)


# ----------------------------
# Ejecutar para todos los juegos
# ----------------------------
if __name__ == "__main__":
    for game_id in GAME_IDS:
        # Opción 1: todo (metadatos + reseñas)
        process_game(game_id)

        # Opción 2: solo metadatos
        #process_metadata_only(game_id)

        # Opción 3: solo reseñas
        #process_reviews_only(game_id, max_pages=MAX_PAGES)
