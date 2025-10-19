import random
import logging
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
from tqdm import tqdm
import nlpaug.augmenter.word as naw

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


# =====================================================
# ===============  AUGMENTATION MANAGER  ===============
# =====================================================

class AugmentationManager:
    def __init__(self, supported_langs=None, device="cpu"):
        if supported_langs is None:
            supported_langs = {'en', 'es', 'fr', 'de', 'it', 'pt', 'nl'}
        self.supported_langs = supported_langs
        self.device = device
        self.augmenters = {}
        self._init_augmenters()

    def _init_augmenters(self):
        for lang in self.supported_langs:
            try:
                if lang == 'en':
                    self.augmenters[lang] = naw.SynonymAug(aug_src='wordnet')
                else:
                    # BackTranslationAug está en naw (word)
                    self.augmenters[lang] = naw.BackTranslationAug(
                        from_model_name=f"Helsinki-NLP/opus-mt-{lang}-en",
                        to_model_name=f"Helsinki-NLP/opus-mt-en-{lang}",
                        device=self.device
                    )
                logger.info(f"✓ Augmenter initialized for {lang}")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize augmenter for {lang}: {e}")

    def augment(self, text: str, lang: str = 'en', num_augmentations: int = 1) -> List[str]:
        """
        Return *only* augmented variants (without including original).
        If nothing new is produced, returns [].
        """
        if not text or len(text.strip()) < 5:
            return []

        augmenter = self.augmenters.get(lang) or self.augmenters.get('en')
        if augmenter is None:
            logger.debug(f"No augmenter available for {lang}")
            return []

        augmented_texts = []
        for _ in range(max(1, num_augmentations)):
            try:
                aug = augmenter.augment(text)
                # aug can be list or str
                if isinstance(aug, list):
                    for a in aug:
                        if isinstance(a, str):
                            augmented_texts.append(a)
                elif isinstance(aug, str):
                    augmented_texts.append(aug)
            except Exception as e:
                logger.debug(f"Augmentation failed for lang={lang}: {e}")

        # Normalize, remove empties and strings identical to original
        cleaned = []
        for a in augmented_texts:
            if not a or not isinstance(a, str):
                continue
            a_stripped = a.strip()
            if not a_stripped or a_stripped == text.strip():
                continue
            cleaned.append(a_stripped)

        # deduplicate preserving order
        cleaned = list(dict.fromkeys(cleaned))
        if not cleaned:
            logger.debug(f"Augmentation returned no new variants for text (lang={lang})")
        else:
            logger.debug(f"Augmentation produced {len(cleaned)} variants for lang={lang}")

        return cleaned  # <-- NOTE: do NOT include the original here


# =====================================================
# ==============  HELPER FUNCTIONS  ===================
# =====================================================

def create_augmented_review(original_review, augmented_text, review_class):
    """Create an augmented copy of a review."""
    aug_review = type(original_review)()
    for attr in ['username', 'rating', 'timestamp', 'game_id', 'category', 'label', 'fileid']:
        if hasattr(original_review, attr):
            setattr(aug_review, attr, getattr(original_review, attr))
    aug_review.comment = augmented_text
    aug_review.raw_text = augmented_text
    aug_review.is_augmented = True
    aug_review.augmented_from = id(original_review)
    return aug_review


# =====================================================
# =======  BALANCING WITH AUGMENTATION & SUBSAMPLING  ==
# =====================================================

def balance_single_game(
    reviews,
    categories=('positive', 'neutral', 'negative'),
    min_samples_for_balance=30,
    balance_strategy='oversample',  # 'oversample', 'undersample', 'hybrid'
    target_ratio=None,
    augmentation_manager: Optional[AugmentationManager] = None,
    augmentation_threshold=0.3,
    max_augmentations_per_review=2,
    verbose=False
) -> Tuple[List, Dict]:
    """
    Balance reviews for a single game using augmentation or subsampling.

    Returns:
        (balanced_reviews_list, stats_dict)
    """
    # Local logger (uses module logger if available)
    try:
        logger  # type: ignore
    except NameError:
        import logging
        logger = logging.getLogger(__name__)

    cat_dict = defaultdict(list)
    for r in reviews:
        cat = getattr(r, 'category', None)
        if cat in categories:
            cat_dict[cat].append(r)

    counts_before = {cat: len(cat_dict[cat]) for cat in categories}
    max_count = max(counts_before.values()) if counts_before else 0
    min_count = min((c for c in counts_before.values() if c > 0), default=0)

    if min_count == 0:
        if verbose:
            print("⚠️ Empty category, skipping balance.")
        logger.info("Skipping balance: at least one category is empty.")
        return reviews, {
            'before': counts_before,
            'after': counts_before,
            'strategy': 'none',
            'balanced': False,
            'augmented_count': 0,
            'subsampled_count': 0
        }

    # Determine target_count per strategy
    if balance_strategy == 'undersample':
        target_count = min_count
    elif balance_strategy == 'oversample':
        target_count = max_count
    else:  # hybrid
        if target_ratio is None:
            ratio = max_count / max(min_count, 1)
            target_ratio = 0.5 if ratio > 10 else 0.6 if ratio > 5 else 0.75 if ratio > 2 else 1.0
        target_count = max(int(max_count * target_ratio), min_samples_for_balance)

    balanced = []
    counts_after = {}
    augmented_count = 0
    subsampled_count = 0
    augmentation_used = False

    # Per-category balancing
    for cat in categories:
        cat_reviews = cat_dict[cat]
        current = len(cat_reviews)

        if current == 0:
            counts_after[cat] = 0
            continue

        if current < target_count:
            needed = target_count - current
            use_aug = augmentation_manager is not None  # Siempre usar augmentación si existe

            if use_aug:
                lang = getattr(cat_reviews[0], 'language', 'en') or 'en'
                logger.info(f"Augmenting category='{cat}' (current={current}, needed={needed}, lang={lang})")
                if verbose:
                    print(f"  {cat}: augmenting (need {needed})")

                augmented_reviews = []
                attempts = 0
                max_attempts = needed * 5  # evita bucles infinitos

                while len(augmented_reviews) < needed and attempts < max_attempts:
                    attempts += 1
                    base_review = random.choice(cat_reviews)
                    per_review_try = min(max_augmentations_per_review, 1 + needed // max(1, current))

                    try:
                        aug_texts = augmentation_manager.augment(
                            base_review.comment, lang=lang, num_augmentations=per_review_try
                        )
                    except Exception as e:
                        logger.debug(f"Augmentation error for review id={getattr(base_review, 'id', 'n/a')}: {e}")
                        continue

                    if not aug_texts:
                        continue

                    for aug_text in aug_texts if isinstance(aug_texts, list) else [aug_texts]:
                        if len(augmented_reviews) >= needed:
                            break
                        if not isinstance(aug_text, str):
                            continue
                        aug_str = aug_text.strip()
                        if not aug_str or aug_str == base_review.comment.strip():
                            continue

                        aug_review = create_augmented_review(base_review, aug_str, cat)
                        augmented_reviews.append(aug_review)
                        augmented_count += 1

                        if verbose:
                            print(f"    + augmented from user={getattr(base_review,'username','n/a')} ({len(augmented_reviews)}/{needed})")

                if len(augmented_reviews) < needed:
                    logger.warning(f"⚠️ Could not fully augment category '{cat}' ({len(augmented_reviews)}/{needed})")

                cat_reviews = cat_reviews + augmented_reviews[:needed]
                counts_after[cat] = len(cat_reviews)
                augmentation_used = True

                logger.info(f"Category '{cat}' augmented +{len(augmented_reviews[:needed])} (needed {needed}, attempts {attempts}).")

            else:
                logger.warning(f"No augmentation manager available for '{cat}', skipping.")
                counts_after[cat] = current

        elif current > target_count:
            if balance_strategy in ('undersample', 'hybrid'):
                removed = current - target_count
                cat_reviews = random.sample(cat_reviews, target_count)
                subsampled_count += removed
                if verbose:
                    print(f"  {cat}: -{removed} subsampled")
                logger.info(f"Category '{cat}' subsampled -{removed}.")

        balanced.extend(cat_reviews)
        counts_after[cat] = len(cat_reviews)

    random.shuffle(balanced)

    stats = {
        'before': counts_before,
        'after': counts_after,
        'strategy': balance_strategy,
        'balanced': True,
        'augmented_count': augmented_count,
        'subsampled_count': subsampled_count,
        'augmentation_used': augmentation_used
    }

    if verbose:
        print(f"Balance stats: before={counts_before} after={counts_after} augmented={augmented_count} subsampled={subsampled_count}")

    logger.info(f"Finished balancing: before={counts_before} after={counts_after} augmented={augmented_count} subsampled={subsampled_count}")
    return balanced, stats


# =====================================================
# ============  MULTI-GAME + REPORTING  ===============
# =====================================================

def collect_balanced_reviews_multi_game(
    all_game_ids,
    merge_reviews_func,
    categories=('positive', 'neutral', 'negative'),
    min_samples_for_balance=30,
    per_game_cap=1000,
    per_game_max_per_class=400,
    balance_strategy='hybrid',  # 'oversample', 'undersample', 'hybrid'
    target_ratio=0.6,
    use_augmentation=True,
    augmentation_threshold=0.3,
    source="combined",
    verbose=True
) -> Tuple[List, Dict]:
    """
    Apply multi-game balancing with augmentation and/or subsampling.
    """
    augmentation_manager = AugmentationManager() if use_augmentation else None
    collected_reviews = []
    game_stats = {}
    global_counts_before = defaultdict(int)
    global_counts_after = defaultdict(int)
    total_augmented = 0
    total_subsampled = 0

    for gid in tqdm(all_game_ids, desc="Processing games", disable=not verbose):
        reviews_raw = merge_reviews_func(gid, source=source) or []
        if not reviews_raw:
            continue

        cat_counts_before = defaultdict(int)
        for r in reviews_raw:
            cat = getattr(r, 'category', None)
            if cat in categories:
                cat_counts_before[cat] += 1
                global_counts_before[cat] += 1

        if verbose:
            total = sum(cat_counts_before.values())
            print(f"\nGame {gid}: {total} reviews | " + " | ".join([f"{c}:{cat_counts_before[c]}" for c in categories]))

        balanced_reviews, stats = balance_single_game(
            reviews_raw,
            categories,
            min_samples_for_balance,
            balance_strategy=balance_strategy,
            target_ratio=target_ratio,
            augmentation_manager=augmentation_manager,
            augmentation_threshold=augmentation_threshold,
            verbose=verbose
        )

        augmented_in_game = sum(1 for r in balanced_reviews if getattr(r, 'is_augmented', False))
        for r in balanced_reviews:
            cat = getattr(r, 'category', None)
            if cat in categories:
                global_counts_after[cat] += 1

        game_stats[gid] = {
            'counts_before': dict(cat_counts_before),
            'counts_after': {c: sum(1 for r in balanced_reviews if getattr(r, 'category', None) == c) for c in categories},
            'total_before': sum(cat_counts_before.values()),
            'total_after': len(balanced_reviews),
            'augmented_count': augmented_in_game,
            'subsampled_count': stats.get('subsampled_count', 0),
            'balance_stats': stats
        }

        total_augmented += augmented_in_game
        total_subsampled += stats.get('subsampled_count', 0)
        collected_reviews.extend(balanced_reviews)

    total_before = sum(global_counts_before.values())
    total_after = len(collected_reviews)
    ratio = max(global_counts_after.values()) / max(min(global_counts_after.values()), 1) if global_counts_after else 0

    if verbose:
        print(f"\n{'='*70}\nGLOBAL SUMMARY:")
        print(f"  Games processed: {len(game_stats)}/{len(all_game_ids)}")
        print(f"  Total reviews: {total_before} → {total_after}")
        print("  Before:  " + " | ".join([f"{c}:{global_counts_before[c]}" for c in categories]))
        print("  After:   " + " | ".join([f"{c}:{global_counts_after[c]}" for c in categories]))
        print(f"  Augmented: {total_augmented} ({(total_augmented/total_after*100 if total_after else 0):.1f}%)")
        print(f"  Subsampled: {total_subsampled}")
        print(f"  Final max/min ratio: {ratio:.2f}:1")
        print(f"  Strategy: {balance_strategy}\n{'='*70}\n")

    return collected_reviews, {
        'counts_before': dict(global_counts_before),
        'counts_after': dict(global_counts_after),
        'total_before': total_before,
        'total_after': total_after,
        'total_augmented': total_augmented,
        'total_subsampled': total_subsampled,
        'balance_ratio_max_min': ratio,
        'balance_strategy': balance_strategy,
        'game_stats': game_stats
    }


def save_balance_report(stats, output_path="balance_report.json"):
    """Save balancing report to JSON."""
    import json
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=4)
        logger.info(f"✓ Balance report saved to {output_path}")
    except Exception as e:
        logger.error(f"⚠️ Could not save report: {e}")