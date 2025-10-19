#pip install requests

import requests
import xml.etree.ElementTree as ET
import json

GAME_ID = 436217
OUTPUT_FILE = f"bgg_reviews_{GAME_ID}_api.json"

# Función auxiliar para obtener texto de etiquetas
def get_text(game, tag):
    element = game.find(tag)
    return element.text if element is not None else "N/A"

# Función para obtener el nombre principal del juego
def get_name(game):
    element = game.find("name[@primary='true']")
    return element.text if element is not None else "N/A"

# Descargar metadatos del juego (sin comentarios)
url_game = f"https://boardgamegeek.com/xmlapi/boardgame/{GAME_ID}"
response = requests.get(url_game)
if response.status_code != 200:
    raise Exception(f"Error descargando los datos del juego: {response.status_code}")

root = ET.fromstring(response.content)
game = root.find('boardgame')

# Guardar metadatos del juego
game_data = {
    "id": GAME_ID,
    "name": get_name(game),
    "yearpublished": get_text(game, 'yearpublished'),
    "minplayers": get_text(game, 'minplayers'),
    "maxplayers": get_text(game, 'maxplayers'),
    "minplaytime": get_text(game, 'minplaytime'),
    "maxplaytime": get_text(game, 'maxplaytime'),
    "age": get_text(game, 'age'),
    "description": get_text(game, 'description'),
    "image": get_text(game, 'image'),
    "thumbnail": get_text(game, 'thumbnail'),
    "publishers": [p.text for p in game.findall('boardgamepublisher')],
    "designers": [d.text for d in game.findall('boardgamedesigner')],
    "artists": [a.text for a in game.findall('boardgameartist')],
    "comments": []
}

# Descargar reseñas
url_comments = f"https://boardgamegeek.com/xmlapi/boardgame/{GAME_ID}?comments=1"
response = requests.get(url_comments)
if response.status_code != 200:
    print(f"Error descargando página {page} de comentarios: {response.status_code}")

root = ET.fromstring(response.content)
game_xml = root.find('boardgame')
comments = game_xml.findall('comment')

for comment in comments:
    comment_data = {
        "username": comment.attrib.get('username', 'N/A'),
        "rating": comment.attrib.get('rating', 'N/A'),
        "comment": comment.text.strip() if comment.text else ''
    }
    game_data["comments"].append(comment_data)

# Guardar reseñas en un archivo JSON
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(game_data, f, ensure_ascii=False, indent=4)

print(f"Se guardaron {len(game_data['comments'])} reseñas en {OUTPUT_FILE}")
