#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BGG crawler simplificado — robusto pero más limpio.
Cambia IDS = [...] para probar juegos distintos.
"""

import os
import json
import logging
import pandas as pd
import re
import requests
from datetime import datetime, timedelta
from typing import Optional, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# ---------- CONFIG ----------
BGG_RANKS = "boardgames_ranks.csv"
ranks_df = pd.read_csv(BGG_RANKS)

IDS = [1]  # <<-- IDs a procesar
GAME_IDS = ranks_df[ranks_df["id"].isin(IDS)]["id"].tolist()

OUTPUT_DIR = "data_crawler"
os.makedirs(OUTPUT_DIR, exist_ok=True)

MAX_PAGES = None
PAGE_SLEEP = 1
RETRY_WAIT = 2
RETRIES = 3

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ---------- helpers ----------
def normalize_timestamp(ts: Optional[str]) -> Optional[int]:
    """Convierte 'Last updated: ...' o 'Today/Yesterday at ...' a timestamp."""
    if not ts:
        return None
    ts = ts.strip().lower()
    meses_map = {"ene":1,"feb":2,"mar":3,"abr":4,"may":5,"jun":6,"jul":7,
                 "ago":8,"sep":9,"sept":9,"oct":10,"nov":11,"dic":12}
    try:
        if ts.startswith("last updated:"):
            ts = ts.replace("last updated:", "").strip()
        if ts.startswith("today at"):
            h, m = map(int, ts.replace("today at","").strip().split(":"))
            now = datetime.now()
            return int(datetime(now.year, now.month, now.day, h, m).timestamp())
        if ts.startswith("yesterday at"):
            h, m = map(int, ts.replace("yesterday at","").strip().split(":"))
            now = datetime.now() - timedelta(days=1)
            return int(datetime(now.year, now.month, now.day, h, m).timestamp())
        parts = ts.split()
        if len(parts) == 3:
            dia = int(parts[0])
            mes = meses_map.get(parts[1])
            anio = int(parts[2])
            if mes:
                return int(datetime(anio, mes, dia).timestamp())
    except:
        return None
    return None

def init_driver(headless: bool = True) -> webdriver.Chrome:
    """Inicializa Selenium Chrome con opciones básicas."""
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")
    return webdriver.Chrome(options=options)

def normalize_flag(flag: Any) -> Optional[int]:
    """Convierte 1/0/True/False/'1'/'0'/None a 1/0/None."""
    if flag is None: return None
    if isinstance(flag, bool): return int(flag)
    if isinstance(flag, int) and flag in (0,1): return flag
    if isinstance(flag, str):
        s = flag.strip()
        if s in ("0","1"): return int(s)
    return None

def build_ratings_page_url(base_ratings_url: str, page: int = 1,
                           comment: Any = None, rated: Any = None) -> str:
    """Construye URL de página de reseñas de BGG con flags comment/rated."""
    comment_n = normalize_flag(comment)
    rated_n = normalize_flag(rated)
    base = base_ratings_url.split("?")[0].rstrip("/")
    url = f"{base}?pageid={page}"
    if comment_n is not None: url += f"&comment={comment_n}"
    if rated_n is not None: url += f"&rated={rated_n}"
    return url

def get_total_reviews_count(base_ratings_url: str, driver: webdriver.Chrome,
                            comment: Any = None, rated: Any = None,
                            page: int = 1, timeout: int = 8) -> Optional[int]:
    """Obtiene el total de reseñas usando XPath simple al <strong> correcto."""
    url = build_ratings_page_url(base_ratings_url, page=page, comment=comment, rated=rated)
    try:
        driver.get(url)
        elem = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.XPATH, "//span[contains(text(),'Showing')]/following::strong[@class='ng-binding'][1]")
            )
        )
        txt = (elem.text or "").strip()
        return int(txt.replace(",", "").replace(".", ""))
    except Exception as e:
        logger.warning(f"No se pudo extraer total de {url}: {e}")
        return None

def get_weight_stats(game_id: int) -> dict:
    """Extrae métricas de weight/complexity desde geekitemPreload en BGG."""
    url = f"https://boardgamegeek.com/boardgame/{game_id}"
    try:
        html = requests.get(url, timeout=10).text
        match = re.search(r"GEEK\.geekitemPreload\s*=\s*(\{.*?\});", html, re.DOTALL)
        if not match:
            return {}
        data = json.loads(match.group(1))

        stats = data.get("item", {}).get("stats", {})
        polls = data.get("item", {}).get("polls", {}).get("boardgameweight", {})

        return {
            "avgweight": float(stats.get("avgweight", 0)) if stats.get("avgweight") else None,
            "numweights": int(stats.get("numweights", 0)) if stats.get("numweights") else None,
            "poll_avg": float(polls.get("averageweight", 0)) if polls.get("averageweight") else None,
            "poll_votes": int(polls.get("votes", 0)) if polls.get("votes") else None,
        }
    except Exception as e:
        logger.warning(f"No se pudo extraer weight stats de {url}: {e}")
        return {}

def download_reviews(base_ratings_url: str, driver: webdriver.Chrome,
                     comment: Any = None, rated: Any = None,
                     max_pages: Optional[int] = None):
    """Descarga todas las reseñas de un juego, respetando flags comment/rated."""
    comment_n = normalize_flag(comment)
    rated_n = normalize_flag(rated)
    reviews = []
    seen = set()
    page = 1

    while True:
        
        if max_pages is not None and page > max_pages: 
            break
        
        url = build_ratings_page_url(base_ratings_url, page=page, comment=comment_n, rated=rated_n)
        loaded = False
        logger.info(f"Descargando página {page} de reseñas: {url}")
        
        for _ in range(RETRIES):
            try:
                driver.get(url)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.summary-rating-item"))
                )
                loaded = True
                break
            except Exception:
                time.sleep(RETRY_WAIT)
        if not loaded: break

        items = driver.find_elements(By.CSS_SELECTOR, "li.summary-rating-item")
        if not items: break

        new = 0
        for item in items:
            try:
                username_elem = item.find_element(By.CSS_SELECTOR, "a.comment-header-user")
                username = username_elem.get_attribute("innerText").strip()
            except:
                username = None
            try:
                rating_elem = item.find_element(By.CSS_SELECTOR, "div.rating-angular")
                rating = rating_elem.get_attribute("innerText").strip()
                rating = float(rating) if rating else None
            except: 
                rating = None
            try:
                comment_elem = item.find_element(By.CSS_SELECTOR, "div.comment-body p")
                comment = comment_elem.get_attribute("innerText").strip()
            except:
                comment = None
            try:
                ts_elem = item.find_element(By.CSS_SELECTOR, "span.ng-binding")
                ts_title = ts_elem.get_attribute("title") or ts_elem.text
                timestamp = normalize_timestamp(ts_title)
            except: timestamp = None

            key = (username, rating, timestamp)
            if key not in seen:
                seen.add(key)
                reviews.append({"username": username, "rating": rating, "comment": comment, "timestamp": timestamp})
                new += 1

        if new == 0:
            logger.info(f"No se encontraron nuevas reseñas en la página {page}.")
            break
        
        page += 1
        time.sleep(PAGE_SLEEP)

    return reviews

# ---------- MAIN ----------
if __name__ == "__main__":
    driver = init_driver(headless=True)
    try:
        for game_id in GAME_IDS:
            logger.info(f"Procesando juego {game_id} ...")
            game_url = f"https://boardgamegeek.com/boardgame/{game_id}"
            driver.get(game_url)
            try:
                canonical = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "link[rel='canonical']"))
                )
                game_url = canonical.get_attribute("href")
            except: 
                pass
            ratings_url = f"{game_url}/ratings"

            # --- Estadísticas de reseñas ---
            total_all = get_total_reviews_count(ratings_url, driver, comment=None, rated=None)
            total_commented = get_total_reviews_count(ratings_url, driver, comment=1, rated=None)
            total_rated = get_total_reviews_count(ratings_url, driver, comment=None, rated=1)
            total_rated_and_commented = get_total_reviews_count(ratings_url, driver, comment=1, rated=1)

            logger.info(f"Totals -> all: {total_all}, commented: {total_commented}, "
                        f"rated: {total_rated}, rated+commented: {total_rated_and_commented}")

            # --- Descarga reseñas ---
            logger.info("Descargando reseñas con comentarios y ratings...")
            data = download_reviews(ratings_url, driver, comment=1, rated=1, max_pages=MAX_PAGES)

            # --- Guardar reseñas en JSON ---
            out_json = os.path.join(OUTPUT_DIR, f"bgg_reviews_{game_id}_crawler.json")
            with open(out_json, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            logger.info(f"Guardadas {len(data)} reseñas en {out_json}")

            # --- Crear CSV con métricas estadísticas ---
            stats = {
                "game_id": game_id,
                "total_all": total_all,
                "total_commented": total_commented,
                "total_rated": total_rated,
                "total_rated_and_commented": total_rated_and_commented,
            }
            
            weight_stats = get_weight_stats(game_id)
            stats.update(weight_stats)

            out_csv = os.path.join(OUTPUT_DIR, "bgg_stats.csv")

            # Si el CSV existe, lo leemos; si no, creamos uno vacío
            if os.path.exists(out_csv):
                existing_df = pd.read_csv(out_csv)
            else:
                existing_df = pd.DataFrame()

            # Convertimos los stats a DataFrame
            new_df = pd.DataFrame([stats])

            # Concatenamos y eliminamos duplicados por game_id (opcional)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df.drop_duplicates(subset=["game_id"], keep="last", inplace=True)

            # Guardamos de nuevo
            combined_df.to_csv(out_csv, index=False)
            logger.info(f"Guardadas estadísticas en {out_csv}\n")
    finally:
        driver.quit()