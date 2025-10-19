import re
import os
import html
import logging
import nltk
from langdetect import detect, DetectorFactory
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.stem import PorterStemmer, SnowballStemmer
from textblob import TextBlob
import pandas as pd
import emoji
import unidecode
import spacy

# ---------------- configuración inicial ----------------
DetectorFactory.seed = 0

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

nltk_data_dir = os.path.join(os.path.expanduser("~"), "nltk_data")
os.makedirs(nltk_data_dir, exist_ok=True)
nltk.data.path.append(nltk_data_dir)

for pkg in ("punkt", "stopwords", "wordnet", "omw-1.4", "punkt_tab", "averaged_perceptron_tagger_eng"):
    try:
        nltk.data.find(f"tokenizers/{pkg}") if "punkt" in pkg else nltk.data.find(f"corpora/{pkg}")
    except LookupError:
        nltk.download(pkg, download_dir=nltk_data_dir, quiet=True)

NLTK_LANG_MAP = {
    "en": "english",
    "es": "spanish",
    "pt": "portuguese",
    "fr": "french",
    "de": "german",
    "it": "italian",
    "nl": "dutch"
}#... Add more as needed

STOPWORDS_CACHE = {}
for lang_code, nltk_name in NLTK_LANG_MAP.items():
    try:
        STOPWORDS_CACHE[nltk_name] = set(stopwords.words(nltk_name))
    except Exception:
        STOPWORDS_CACHE[nltk_name] = set()

# Cargar modelos de SpaCy para cada idioma soportado
# Importante: se deben descargar los modelos previamente
SPACY_MODELS = {}
SPACY_LANG_MAP = {
    "en": "en_core_web_sm",
    "es": "es_core_news_sm",
    "fr": "fr_core_news_sm",
    "de": "de_core_news_sm",
    "it": "it_core_news_sm",
    "pt": "pt_core_news_sm",
    "nl": "nl_core_news_sm"
}#... Add more as needed

for code, model_name in SPACY_LANG_MAP.items():
    try:
        SPACY_MODELS[code] = spacy.load(model_name, disable=["ner"])
    except Exception:
        SPACY_MODELS[code] = None

BGG_RANKS = "boardgames_ranks.csv"
try:
    ranks_df = pd.read_csv(BGG_RANKS)
    id2name = dict(zip(ranks_df["id"], ranks_df["name"]))
except FileNotFoundError:
    id2name = {}
    print(f"[warning] {BGG_RANKS} not found. Thing tag replacement disabled.")

# ---------------- regex para patrones ----------------
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
DATE_RE = re.compile(r"\b\d{2}[/-]\d{2}[/-]\d{4}\b")
PHONE_RE = re.compile(r"\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{4,10}")
HASHTAG_RE = re.compile(r"#\w+")
MENTION_RE = re.compile(r"@\w+")
URL_RE = re.compile(r"https?://\S+|www\.\S+")

ABBREVIATIONS = {
    "Sr": "Señor", "Sra": "Señora", "Dr": "Doctor", "Dra": "Doctora",
    "EE.UU": "Estados Unidos", "etc": "etcétera", "info": "information",
    "mins": "minutes", "hr": "hour", "yrs": "years"
}#... Add more as needed

# ---------------- funciones básicas ----------------
def detect_language(text):
    if not text or not text.strip():
        return "unknown"
    try:
        return detect(text)
    except:
        return "unknown"

def get_nltk_language(code):
    return NLTK_LANG_MAP.get(code, "english")

def get_spacy_lang_code(detected_code):
    if not detected_code or detected_code == "unknown":
        return "en"
    base = detected_code.split("-")[0].lower()
    return base if base in SPACY_LANG_MAP else "en"

def load_spacy_model_for(code):
    if code in SPACY_MODELS and SPACY_MODELS[code] is not None:
        return SPACY_MODELS[code]

    model_name = SPACY_LANG_MAP.get(code)
    if not model_name:
        SPACY_MODELS[code] = None
        return None

    try:
        nlp = spacy.load(model_name, disable=["ner"])
        SPACY_MODELS[code] = nlp
        return nlp
    except Exception as e:
        SPACY_MODELS[code] = None
        logger.warning(f"spaCy model {model_name} not available: {e}")
        return None

def list_missing_spacy_models():
    missing = []
    for c, model_name in SPACY_LANG_MAP.items():
        if SPACY_MODELS.get(c) is None:
            missing.append(model_name)
    return missing

def replace_thing_tags(text, id2name):
    def repl(match):
        game_id = int(match.group(1))
        return id2name.get(game_id, "")
    return re.sub(r"\[thing=(\d+)\]\[\/thing\]", repl, text)

def analyze_text_spacy(text, detected_code):
    code = get_spacy_lang_code(detected_code)
    nlp = load_spacy_model_for(code)

    if nlp:
        doc = nlp(text)
        pos_tags = [(token.text, token.pos_, token.tag_) for token in doc]
        dependencies = [(token.text, token.dep_, token.head.text) for token in doc]
        lemmas = [token.lemma_ for token in doc if not token.is_stop and token.lemma_.strip()]
        return {
            "spacy_used": True,
            "pos_tags": pos_tags,
            "dependencies": dependencies,
            "lemmas": lemmas
        }

    # FALLBACK si spaCy no está disponible
    if code == "en":
        lemmatizer = WordNetLemmatizer()
        tokens = re.findall(r"\w+", text.lower())
        lemmas = [lemmatizer.lemmatize(t) for t in tokens if t.strip()]
        return {
            "spacy_used": False,
            "pos_tags": [],
            "dependencies": [],
            "lemmas": lemmas
        }

    # Otros idiomas: fallback al stemmer
    try:
        stemmer = SnowballStemmer(code)
    except Exception:
        stemmer = SnowballStemmer("english")
    tokens = re.findall(r"\w+", text.lower())
    pseudo_lemmas = [stemmer.stem(t) for t in tokens if t.strip()]
    return {
        "spacy_used": False,
        "pos_tags": [],
        "dependencies": [],
        "lemmas": pseudo_lemmas
    }

def normalize_text(text, lower=True, correct_spelling=False):
    if not text:
        return ""
    
    text = html.unescape(text)
    text = replace_thing_tags(text, id2name)
    text = re.sub(r"<.*?>", " ", text)
    text = re.sub(r"\[/?[ib]\]", " ", text)
    text = URL_RE.sub(" ", text)
    text = text.replace("\r", " ").replace("\n", " ")
    text = text.replace("&", " and ")
    text = re.sub(r"[\t\v\f]+", " ", text)
    text = re.sub(r"(.)\1{2,}", r"\1\1", text)
    text = re.sub(r"([!?])\1{1,}", r"\1\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\.{2,}", ".", text)
    
    if lower:
        text = text.lower()
    
    text = text.replace("'", "'")
    text = unidecode.unidecode(text)
    text = emoji.demojize(text, delimiters=(":", ":"))
    text = re.sub(r':[a-zA-Z0-9_]+:', '', text)
    text = re.sub(r'[:;=8][-~]?[)(DPpOo]', '', text)
    
    if correct_spelling:
        text = str(TextBlob(text).correct())
    
    words = text.split()
    words = [ABBREVIATIONS.get(w, w) for w in words]
    text = " ".join(words)
    text = re.sub(r"\s+", " ", text).strip()
    
    return text

def extract_special_patterns(text):
    return {
        "emails": EMAIL_RE.findall(text),
        "dates": DATE_RE.findall(text),
        "phones": PHONE_RE.findall(text),
        "hashtags": HASHTAG_RE.findall(text),
        "mentions": MENTION_RE.findall(text),
        "urls": URL_RE.findall(text),
        "emojis": [c for c in text.split() if c.startswith(":") and c.endswith(":")],
    }

def sentence_segmentation(text, nltk_lang):
    if not text or not text.strip():
        return []
    
    try:
        sentences = sent_tokenize(text, language=nltk_lang)
    except Exception as e:
        logger.warning(f"sent_tokenize failed: {e}. Using regex fallback.")
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    
    return [s for s in sentences if s.strip()]

def tokenize_and_filter(text, nltk_lang, stop_words_set, remove_stopwords=True):
    if not text or not text.strip():
        return [], []
    
    try:
        tokens = word_tokenize(text, language=nltk_lang)
    except Exception as e:
        logger.warning(f"word_tokenize failed: {e}. Using regex fallback.")
        tokens = re.findall(r"\w+", text)
    
    tokens_alpha = [t for t in tokens if re.search(r"\w", t)]
    
    if remove_stopwords:
        tokens_no_stop = [t for t in tokens_alpha if t.lower() not in stop_words_set]
    else:
        tokens_no_stop = tokens_alpha
    
    return tokens_alpha, tokens_no_stop

def apply_stemming(tokens, spacy_lang):
    if not tokens:
        return []
    
    lang = NLTK_LANG_MAP.get(spacy_lang, "english")
    
    if lang == "english":
        stemmer = PorterStemmer()
    else:
        try:
            stemmer = SnowballStemmer(lang)
        except Exception:
            stemmer = SnowballStemmer("english")
    
    return [stemmer.stem(t) for t in tokens]

def process_review_item(item, lower=True, remove_stopwords=True, lemmatize=True,
                        correct_spelling=False, stemming=True):
    raw = item.get("raw_text") or item.get("comment") or ""
    
    if not raw or not raw.strip():
        return {
            "username": item.get("username"),
            "rating": item.get("rating"),
            "timestamp": item.get("timestamp"),
            "raw_text": raw,
            "clean_text": "",
            "language_detected": "unknown",
            "language": "en",
            "sentences": [],
            "tokens": [],
            "tokens_no_stopwords": [],
            "stems": [],
            "lemmas": [],
            "pos_tags": [],
            "dependencies": [],
            "num_tokens": 0,
            "num_sentences": 0,
            "patterns": {
                "emails": [], "dates": [], "phones": [], "hashtags": [],
                "mentions": [], "urls": [], "emojis": []
            }
        }
    
    special_patterns = extract_special_patterns(raw)
    clean = normalize_text(raw, lower=lower, correct_spelling=correct_spelling)
    
    detected_lang = detect_language(clean if clean else raw)
    spacy_lang = get_spacy_lang_code(detected_lang)
    nltk_lang = get_nltk_language(spacy_lang)
    
    sentences = sentence_segmentation(clean, nltk_lang)
    
    stop_words_set = STOPWORDS_CACHE.get(nltk_lang, set())
    tokens, tokens_no_stop = tokenize_and_filter(clean, nltk_lang, stop_words_set, remove_stopwords)
    
    spacy_analysis = analyze_text_spacy(clean, detected_lang)
    
    stems = apply_stemming(tokens_no_stop, spacy_lang) if stemming else []
    
    lemmas_final = []
    if lemmatize:
        if spacy_analysis.get("spacy_used") and spacy_analysis.get("pos_tags"):
            # Mapear tokens_no_stop a sus lemmas correspondientes en spaCy
            nlp = load_spacy_model_for(spacy_lang)
            if nlp:
                lemmas_final = []
                for token_text in tokens_no_stop:
                    doc_token = nlp(token_text)
                    lemma = doc_token[0].lemma_ if doc_token else token_text
                    lemmas_final.append(lemma)
        else:
            # Fallback: lematización NLTK para cada token_no_stop
            lemmatizer = WordNetLemmatizer()
            lemmas_final = [lemmatizer.lemmatize(t) for t in tokens_no_stop]

    
    out = {
        "username": item.get("username"),
        "rating": item.get("rating"),
        "timestamp": item.get("timestamp"),
        "raw_text": raw,
        "clean_text": clean,
        "language_detected": detected_lang,
        "language": spacy_lang,
        "sentences": sentences,
        "tokens": tokens,
        "tokens_no_stopwords": tokens_no_stop,
        "stems": stems,
        "lemmas": lemmas_final,
        "pos_tags": spacy_analysis.get("pos_tags", []),
        "dependencies": spacy_analysis.get("dependencies", []),
        "num_tokens": len(tokens),
        "num_sentences": len(sentences),
        "patterns": special_patterns
    }
    return out