"""
Linguistic Features Extraction Module
"""
# https://www.nltk.org/_modules/nltk/sentiment/vader.html
import logging
import json
import os
import pickle
from typing import Dict, List, Any
from collections import defaultdict
import numpy as np
from tqdm import tqdm

import nltk
from nltk.corpus import stopwords
from bgg_corpus import Review, CorpusDocument, GameCorpus, Corpus
from nltk.sentiment import SentimentIntensityAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Download required NLTK resources
required_nltk = ['vader_lexicon', 'averaged_perceptron_tagger', 'universal_tagset', 'punkt']
for resource in required_nltk:
    try:
        nltk.data.find(f'tokenizers/{resource}')
    except LookupError:
        nltk.download(resource)


# =====================================================
# ============  LEXICON LOADERS & UTILITIES  =========
# =====================================================

class SentimentLexicon:
    """Load and manage sentiment lexicons."""
    
    def __init__(self, base_path: str = "lexicons"):
        self.base_path = base_path
        self.positive_words = self._load_positive_lexicon()
        self.negative_words = self._load_negative_lexicon()
        self.intensifiers = self._load_intensifiers()
        self.mitigators = self._load_mitigators()
        self.negation_words = self._load_negations()
        self.domain_terms = self._load_domain_terms()

    def _load_lexicon(self, filename, fallback):
        """Load a lexicon from file if available, otherwise return fallback."""
        filepath = os.path.join(self.base_path, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return {line.strip().lower() for line in f if line.strip() and not line.startswith(';')}
        return fallback
    
    @staticmethod
    def _load_positive_lexicon():
        """Load positive sentiment words."""
        words = {
            'amazing', 'awesome', 'excellent', 'fantastic', 'great', 'good', 'wonderful',
            'love', 'enjoy', 'fun', 'engaging', 'brilliant', 'outstanding', 'superb',
            'delightful', 'thrilling', 'impressive', 'remarkable', 'beautiful', 'elegant',
            'clever', 'smart', 'intuitive', 'smooth', 'balanced', 'strategic', 'deep',
            'rewarding', 'satisfying', 'addictive', 'compelling', 'captivating', 'immersive',
            'intuitive', 'tight', 'polished', 'refined', 'intricate', 'sophisticated'
        }
        return words
    
    @staticmethod
    def _load_negative_lexicon():
        """Load negative sentiment words."""
        words = {
            'bad', 'awful', 'terrible', 'horrible', 'poor', 'weak', 'boring', 'tedious',
            'hate', 'dislike', 'frustrating', 'frustrate', 'annoying', 'annoyed', 'disappointed',
            'disappointing', 'dull', 'bland', 'broken', 'buggy', 'confusing', 'complicated',
            'convoluted', 'messy', 'messy', 'clunky', 'unbalanced', 'unplayable', 'unforgiving',
            'ugly', 'cheap', 'flimsy', 'slow', 'tedious', 'repetitive', 'shallow', 'forgettable'
        }
        return words
    
    @staticmethod
    def _load_intensifiers():
        """Load intensifying adverbs."""
        return {
            'extremely', 'very', 'so', 'really', 'quite', 'incredibly', 'absolutely',
            'utterly', 'completely', 'totally', 'entirely', 'definitely', 'certainly',
            'way', 'much', 'far', 'deeply', 'highly', 'awfully', 'incredibly', 'remarkably'
        }
    
    @staticmethod
    def _load_mitigators():
        """Load mitigating/softening adverbs."""
        return {
            'somewhat', 'kind of', 'sort of', 'rather', 'quite', 'fairly', 'reasonably',
            'almost', 'barely', 'hardly', 'scarcely', 'slightly', 'pretty', 'partially',
            'arguably', 'arguably', 'relatively', 'comparatively', 'marginally'
        }
    
    @staticmethod
    def _load_negations():
        """Load negation words."""
        return {
            'not', 'no', 'never', 'neither', 'nobody', 'nothing', 'nowhere', 'none',
            'cannot', 'can\'t', 'shouldn\'t', 'wouldn\'t', 'couldn\'t', 'won\'t',
            'isn\'t', 'aren\'t', 'wasn\'t', 'weren\'t', 'hasn\'t', 'haven\'t',
            'doesn\'t', 'don\'t', 'didn\'t', 'haven\'t', 'hadn\'t'
        }
    
    @staticmethod
    def _load_domain_terms():
        """Load board game domain-specific terms."""
        return {
            'mechanics': ['dice', 'roll', 'cards', 'tiles', 'tokens', 'board', 'pieces',
                         'meeples', 'components', 'setup', 'turn', 'round', 'phase'],
            'components': ['miniatures', 'quality', 'art', 'design', 'pieces', 'tokens',
                          'cards', 'board', 'box', 'packaging', 'production'],
            'rules': ['rulebook', 'rules', 'instructions', 'manual', 'clarity', 'flow',
                     'teaching', 'explanation', 'learning'],
            'gameplay': ['gameplay', 'playtime', 'length', 'pacing', 'turns', 'balance',
                        'replayability', 'variability', 'depth', 'strategy'],
            'theme': ['theme', 'immersion', 'atmosphere', 'setting', 'flavor', 'narrative',
                     'story', 'aesthetic']
        }


# =====================================================
# ============  LINGUISTIC FEATURES EXTRACTOR  ======
# =====================================================

class LinguisticFeaturesExtractor:
    """Extract linguistic features from board game reviews."""
    
    def __init__(self):
        self.lexicon = SentimentLexicon()
        self.sia = SentimentIntensityAnalyzer()
        self.stop_words = set(stopwords.words('english'))
    
    def extract_from_corpus_doc(self, doc: CorpusDocument) -> Dict[str, Any]:
        """Extract linguistic features from an already processed CorpusDocument."""
        if not doc.text or not doc.text.get("lemmas"):
            return self._empty_features()
        
        lemmas = [w.lower() for w in doc.text.get("lemmas", [])]
        pos_tags = doc.text.get("pos_tags", [])
        tokens = list(zip(lemmas, pos_tags))
        
        features = self._empty_features()

        # --- 1. Sentiment words ---
        pos_count = sum(1 for w, _ in tokens if w in self.lexicon.positive_words)
        neg_count = sum(1 for w, _ in tokens if w in self.lexicon.negative_words)
        total = pos_count + neg_count
        ratio = pos_count / max(total, 1) if total > 0 else 0
        features['sentiment_words'].update({
            'positive_count': pos_count,
            'negative_count': neg_count,
            'total_count': total,
            'ratio': ratio
        })

        # --- 2. Negations ---
        neg_positions = [i for i, (w, _) in enumerate(tokens) if w in self.lexicon.negation_words]
        features['negations'].update({
            'count': len(neg_positions),
            'positions': neg_positions
        })

        # --- 3. Modifiers ---
        intensifiers = sum(1 for w, _ in tokens if w in self.lexicon.intensifiers)
        mitigators = sum(1 for w, _ in tokens if w in self.lexicon.mitigators)
        features['intensifiers_mitigators'].update({
            'intensifiers': intensifiers,
            'mitigators': mitigators,
            'total_modifiers': intensifiers + mitigators
        })

        # --- 4. Domain-specific terms ---
        domain_features = {}
        for cat, terms in self.lexicon.domain_terms.items():
            mentions = [w for w in lemmas if w in terms]
            domain_features[cat] = {
                'count': len(mentions),
                'mentions': mentions
            }
        features['domain_specific'] = domain_features

        # --- 5. Vader sentiment (requires raw text) ---
        features['vader_scores'] = self._extract_vader_scores(doc.raw_text)

        # --- 6. Syntactic complexity ---
        dep_depths = [len(dep.split("/")) for dep in doc.text.get("dependencies", []) if isinstance(dep, str)]
        avg_dep = sum(dep_depths) / len(dep_depths) if dep_depths else 0
        features['syntactic_complexity'].update({
            'avg_dep_depth': avg_dep,
            'num_dependencies': len(dep_depths),
            'num_tokens': doc.text.get("num_tokens", 0),
            'num_sentences': doc.text.get("num_sentences", 0)
        })

        return features
    
    def _extract_vader_scores(self, text: str) -> Dict[str, float]:
        """Extract VADER sentiment scores."""
        scores = self.sia.polarity_scores(text)
        return {
            'compound': scores['compound'],
            'positive': scores['pos'],
            'neutral': scores['neu'],
            'negative': scores['neg']
        }
    
    def _empty_features(self) -> Dict[str, Any]:
        """Return empty features structure."""
        return {
            'sentiment_words': {'positive_count': 0, 'negative_count': 0, 'ratio': 0},
            'negations': {'count': 0, 'negated_sentiments': []},
            'intensifiers_mitigators': {'intensifiers': 0, 'mitigators': 0},
            'domain_specific': {cat: {'count': 0, 'nearby_sentiments': []} 
                               for cat in ['mechanics', 'components', 'rules', 'gameplay', 'theme']},
            'vader_scores': {'compound': 0, 'pos': 0, 'neu': 0, 'neg': 0},
            'syntactic_complexity': {'avg_dep_depth': 0, 'noun_chunks': 0},
            'sentence_level': {'sentiment_variance': 0, 'avg_sentiment': 0}
        }
    
    @staticmethod
    def _calculate_dependency_depth(token, depth=0) -> int:
        """Calculate dependency tree depth."""
        if token.head == token:
            return depth
        return LinguisticFeaturesExtractor._calculate_dependency_depth(token.head, depth + 1)
    
    def _extract_sentence_level_features(self, sentences: List) -> Dict[str, Any]:
        """Extract sentence-level sentiment features."""
        sentence_sentiments = []
        
        for sent in sentences:
            sentiment = self.sia.polarity_scores(sent.text)
            sentence_sentiments.append(sentiment['compound'])
        
        if sentence_sentiments:
            avg_sentiment = sum(sentence_sentiments) / len(sentence_sentiments)
            variance = np.var(sentence_sentiments) if len(sentence_sentiments) > 1 else 0
        else:
            avg_sentiment = 0
            variance = 0
        
        return {
            'num_sentences': len(sentences),
            'avg_sentiment': avg_sentiment,
            'sentiment_variance': variance,
            'sentence_sentiments': sentence_sentiments
        }


# =====================================================
# ========  CORPUS ANNOTATION & STORAGE  =============
# =====================================================

def extract_features_from_processed_doc(doc: CorpusDocument, extractor: LinguisticFeaturesExtractor) -> Dict[str, Any]:
    """
    Extrae rasgos lingüísticos usando los datos ya procesados en el CorpusDocument
    (lemmas, pos_tags, dependencias, etc.).
    """
    if not doc.text:
        return extractor._empty_features()

    lemmas = [w.lower() for w in doc.text.get("lemmas", [])]
    pos_tags = doc.text.get("pos_tags", [])
    tokens = list(zip(lemmas, pos_tags))

    features = extractor._empty_features()

    # --- 1. Sentiment words ---
    pos_count = sum(1 for w, _ in tokens if w in extractor.lexicon.positive_words)
    neg_count = sum(1 for w, _ in tokens if w in extractor.lexicon.negative_words)
    total = pos_count + neg_count
    ratio = pos_count / max(total, 1) if total > 0 else 0

    features['sentiment_words'] = {
        'positive_count': pos_count,
        'negative_count': neg_count,
        'total_count': total,
        'ratio': ratio
    }

    # --- 2. Negations ---
    negations = [i for i, (w, _) in enumerate(tokens) if w in extractor.lexicon.negation_words]
    features['negations'] = {
        'count': len(negations),
        'positions': negations
    }

    # --- 3. Modifiers (intensifiers / mitigators) ---
    intensifiers = sum(1 for w, _ in tokens if w in extractor.lexicon.intensifiers)
    mitigators = sum(1 for w, _ in tokens if w in extractor.lexicon.mitigators)
    features['intensifiers_mitigators'] = {
        'intensifiers': intensifiers,
        'mitigators': mitigators,
        'total_modifiers': intensifiers + mitigators
    }

    # --- 4. Domain-specific terms ---
    domain_features = {}
    for cat, terms in extractor.lexicon.domain_terms.items():
        mentions = [w for w in lemmas if w in terms]
        domain_features[cat] = {
            'count': len(mentions),
            'mentions': mentions
        }
    features['domain_specific'] = domain_features

    # --- 5. Vader sentiment (still uses text, for global polarity) ---
    features['vader_scores'] = extractor._extract_vader_scores(doc.raw_text)

    # --- 6. Syntactic complexity (from stored dependencies) ---
    dep_depths = [len(dep.split("/")) for dep in doc.text.get("dependencies", []) if isinstance(dep, str)]
    avg_dep = sum(dep_depths) / len(dep_depths) if dep_depths else 0
    features['syntactic_complexity'] = {
        'avg_dep_depth': avg_dep,
        'num_dependencies': len(dep_depths),
        'num_tokens': doc.text.get("num_tokens", 0),
        'num_sentences': doc.text.get("num_sentences", 0)
    }

    return features

def annotate_game_corpus(game_corpus: List[CorpusDocument]) -> List[CorpusDocument]:
    """
    Anota cada documento del GameCorpus con rasgos lingüísticos, 
    usando la información procesada ya disponible.
    """
    extractor = LinguisticFeaturesExtractor()
    annotated = []

    for doc in tqdm(game_corpus, desc="Annotating processed corpus"):
        try:
            features = extract_features_from_processed_doc(doc, extractor)
            doc.linguistic_features = features
            annotated.append(doc)
        except Exception as e:
            logger.error(f"Error processing doc (game_id={doc.game_id}): {e}")
            continue

    logger.info(f"✓ {len(annotated)} documentos anotados con rasgos lingüísticos")
    return annotated


def save_features_to_pickle(reviews, output_path='annotated_corpus.pkl'):
    """Save annotated corpus to pickle."""
    try:
        with open(output_path, 'wb') as f:
            pickle.dump(reviews, f)
        logger.info(f"✓ Annotated corpus saved to {output_path}")
    except Exception as e:
        logger.error(f"Error saving corpus: {e}")


def save_features_summary(reviews, output_path='features_summary.json'):
    """Save features summary as JSON."""
    summary = {
        'total_reviews': len(reviews),
        'features_extracted': []
    }
    
    for idx, review in enumerate(reviews[:100]):  # Sample first 100
        if hasattr(review, 'linguistic_features'):
            summary['features_extracted'].append({
                'review_id': idx,
                'game_id': getattr(review, 'game_id', None),
                'category': getattr(review, 'category', None),
                'features': review.linguistic_features
            })
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=4, default=str)
        logger.info(f"✓ Features summary saved to {output_path}")
    except Exception as e:
        logger.error(f"Error saving summary: {e}")


def generate_features_report(reviews, output_path='features_report.txt'):
    """Generate comprehensive features report."""
    report = []
    report.append("="*70)
    report.append("LINGUISTIC FEATURES EXTRACTION REPORT")
    report.append("="*70)
    
    total_reviews = len(reviews)
    report.append(f"\nTotal Reviews Processed: {total_reviews}\n")
    
    # Aggregate statistics
    sentiment_stats = defaultdict(list)
    negation_counts = []
    modifier_counts = []
    domain_mentions = defaultdict(int)
    
    for review in reviews:
        if hasattr(review, 'linguistic_features'):
            feat = review.linguistic_features
            
            sentiment_stats['positive'].append(feat['sentiment_words']['positive_count'])
            sentiment_stats['negative'].append(feat['sentiment_words']['negative_count'])
            negation_counts.append(feat['negations']['count'])
            modifier_counts.append(
                feat['intensifiers_mitigators']['intensifiers'] + 
                feat['intensifiers_mitigators']['mitigators']
            )
            
            for category in feat['domain_specific']:
                domain_mentions[category] += feat['domain_specific'][category]['count']
    
    # Report statistics
    if sentiment_stats['positive']:
        report.append("SENTIMENT WORDS STATISTICS:")
        report.append(f"  Avg positive words per review: {np.mean(sentiment_stats['positive']):.2f}")
        report.append(f"  Avg negative words per review: {np.mean(sentiment_stats['negative']):.2f}")
    
    if negation_counts:
        report.append(f"\nNEGATION STATISTICS:")
        report.append(f"  Avg negations per review: {np.mean(negation_counts):.2f}")
        report.append(f"  Max negations: {max(negation_counts)}")
    
    if modifier_counts:
        report.append(f"\nMODIFIER STATISTICS:")
        report.append(f"  Avg modifiers per review: {np.mean(modifier_counts):.2f}")
    
    report.append(f"\nDOMAIN-SPECIFIC MENTIONS:")
    for category, count in sorted(domain_mentions.items(), key=lambda x: x[1], reverse=True):
        report.append(f"  {category}: {count} total mentions")
    
    report.append("\n" + "="*70)
    
    # Save report
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        logger.info(f"✓ Features report saved to {output_path}")
    except Exception as e:
        logger.error(f"Error saving report: {e}")
    
    print('\n'.join(report))


# =====================================================
# ==================  MAIN SCRIPT  ===================
# =====================================================

if __name__ == "__main__":
    # Logging
    logger.info("Board Game Reviews - Linguistic Features Extraction")
    
    # Cargar corpus
    corpus = Corpus.from_json("data_corpus/bgg_corpus.json")
    
    # Anotar corpus con rasgos lingüísticos
    annotated_reviews = annotate_game_corpus(corpus.documents)
    
    # Guardar resumen de features en JSON
    #save_features_summary(annotated_reviews, output_path='features_summary.json')
    
    # Generar reporte completo en TXT
    #generate_features_report(annotated_reviews, output_path='features_report.txt')
    
    corpus.to_json("data_corpus/bgg_corpus.json")
    
    logger.info("✓ Linguistic features extraction pipeline completed successfully.")