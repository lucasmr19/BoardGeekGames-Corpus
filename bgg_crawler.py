#pip install selenium

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time

BASE_URL = "https://boardgamegeek.com/boardgame/436217/the-lord-of-the-rings-fate-of-the-fellowship/ratings"
OUTPUT_FILE = "bgg_reviews_436217_crawler.json"

def download_reviews():
    reviews = []

    # Configurar Selenium (modo headless para que no abra ventana)
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=options)

    try:
        print(f"Descargando reseñas...")
        url = BASE_URL
        driver.get(url)

        try:
            # Esperar a que aparezcan reviews
            WebDriverWait(driver, 3).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.summary-rating-item"))
            )
        except:
            print("No se encontraron más reviews. Fin.")
            return reviews

        items = driver.find_elements(By.CSS_SELECTOR, "li.summary-rating-item")
        if not items:
            return reviews

        for item in items:
            # username
            try:
                username_elem = item.find_element(By.CSS_SELECTOR, "a.comment-header-user")
                username = username_elem.get_attribute("innerText").strip()
            except:
                username = None

            # rating
            try:
                rating_elem = item.find_element(By.CSS_SELECTOR, "div.rating-angular")
                rating = rating_elem.get_attribute("innerText").strip()
            except:
                rating = None

            # comment
            try:
                comment_elem = item.find_element(By.CSS_SELECTOR, "div.comment-body p")
                comment = comment_elem.get_attribute("innerText").strip()
            except:
                comment = None

            reviews.append({
                "username": username,
                "rating": rating,
                "comment": comment
            })

    finally:
        driver.quit()

    return reviews

# Descargar reseñas
data = download_reviews()

# Guardar reseñas en un archivo JSON
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Se guardaron {len(data)} reseñas en {OUTPUT_FILE}")
