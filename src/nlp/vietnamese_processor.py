import re
import time
from typing import List, Dict, Any, Optional
from underthesea import word_tokenize
from deep_translator import GoogleTranslator, MyMemoryTranslator
from loguru import logger
import collections

class NLPCache:
    """Simple in-memory cache with TTL and LRU eviction."""
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
        self.stats = {"hits": 0, "misses": 0}

    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            entry = self.cache[key]
            if time.time() < entry['expiry']:
                self.stats["hits"] += 1
                return entry['value']
            else:
                del self.cache[key]
        self.stats["misses"] += 1
        return None

    def set(self, key: str, value: Any, ttl: int = 3600):
        if len(self.cache) >= self.max_size:
            # Simple LRU: remove oldest based on insertion (Python 3.7+ dict is ordered)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[key] = {
            'value': value,
            'expiry': time.time() + ttl
        }

    def get_stats(self) -> Dict[str, int]:
        return {**self.stats, "size": len(self.cache)}

# Global cache instance
nlp_cache = NLPCache()

# Basic Vietnamese stopwords (minimal list for illustration, usually expanded from a file)
VIETNAMESE_STOPWORDS = {
    "là", "cái", "được", "những", "của", "và", "trong", "có", "cho", "đến", 
    "một", "với", "tại", "vào", "như", "này", "khi", "ra", "về", "các", "này"
}

def normalize_text(text: str) -> str:
    """Normalize text: lowercase, remove extra whitespace."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text

def tokenize_vietnamese(text: str) -> List[str]:
    """Tokenize Vietnamese text using underthesea with fallback."""
    if not text:
        return []
    try:
        tokens = word_tokenize(text)
        logger.info(f"Tokenization successful for: {text[:30]}...")
        return tokens
    except Exception as e:
        logger.error(f"Underthesea tokenization failed: {str(e)}. Falling back to whitespace split.")
        return text.split()

def remove_stopwords(tokens: List[str]) -> List[str]:
    """Remove Vietnamese stopwords from a list of tokens."""
    return [t for t in tokens if t.lower() not in VIETNAMESE_STOPWORDS]

def process_vietnamese_keywords(text: str) -> List[str]:
    """Complete NLP workflow: normalize -> tokenize -> remove_stopwords."""
    cache_key = f"process_{hash(text)}"
    cached = nlp_cache.get(cache_key)
    if cached:
        return cached

    normalized = normalize_text(text)
    tokens = tokenize_vietnamese(normalized)
    keywords = remove_stopwords(tokens)
    
    nlp_cache.set(cache_key, keywords)
    return keywords

def translate_to_english(text: str) -> str:
    """Translate text to English with fallback mechanism."""
    if not text:
        return ""
    
    cache_key = f"trans_{hash(text)}"
    cached = nlp_cache.get(cache_key)
    if cached:
        return cached

    try:
        # Primary translator: Google
        translator = GoogleTranslator(source='vi', target='en')
        translation = translator.translate(text)
        logger.info(f"Translation (Google) successful for: {text[:30]}...")
        nlp_cache.set(cache_key, translation)
        return translation
    except Exception as e:
        logger.warning(f"Google Translate failed: {str(e)}. Trying fallback MyMemoryTranslator.")
        try:
            # Fallback: MyMemory
            fallback = MyMemoryTranslator(source='vi', target='en')
            translation = fallback.translate(text)
            nlp_cache.set(cache_key, translation)
            return translation
        except Exception as fe:
            logger.error(f"Fallback translation failed: {str(fe)}. Returning original text.")
            return text

def process_and_translate(text: str) -> Dict[str, Any]:
    """Complete workflow: NLP processing + translation."""
    if not text:
        raise ValueError("Input text cannot be empty")

    cache_key = f"full_{hash(text)}"
    cached = nlp_cache.get(cache_key)
    if cached:
        return cached

    normalized = normalize_text(text)
    tokens = tokenize_vietnamese(normalized)
    keywords = remove_stopwords(tokens)
    
    english_translation = translate_to_english(text)
    english_tokens = english_translation.lower().split()
    
    result = {
        "original": text,
        "normalized": normalized,
        "tokens": tokens,
        "keywords": keywords,
        "english_translation": english_translation,
        "english_keywords": english_tokens,
        "error": None
    }
    
    nlp_cache.set(cache_key, result)
    return result
