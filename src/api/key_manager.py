import os
import threading
from typing import List, Optional
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class KeyManager:
    """
    Manages API key rotation for Gemini and Groq to handle rate limits.
    Supports up to 5 keys for each service as per architecture.
    """
    
    def __init__(self):
        self._gemini_keys: List[str] = self._load_keys("GEMINI_API_KEY")
        self._groq_keys: List[str] = self._load_keys("GROQ_API_KEY")
        
        self._gemini_index = 0
        self._groq_index = 0
        
        self._lock = threading.Lock()
        
        logger.info(f"KeyManager initialized with {len(self._gemini_keys)} Gemini keys and {len(self._groq_keys)} Groq keys.")

    def _load_keys(self, base_name: str) -> List[str]:
        """
        Loads keys from environment variables.
        Tries base_name (e.g. GEMINI_API_KEY) then base_name_1, base_name_2... up to 5.
        """
        keys = []
        
        # Check single key first
        primary_key = os.getenv(base_name)
        if primary_key and primary_key != "your_gemini_api_key_here" and primary_key != "your_groq_api_key_here":
            keys.append(primary_key)
            
        # Check for indexed keys 1-5
        for i in range(1, 6):
            indexed_key = os.getenv(f"{base_name}_{i}")
            if indexed_key and indexed_key not in keys:
                keys.append(indexed_key)
                
        return [k for k in keys if k]

    def get_gemini_key(self) -> str:
        """Returns the next available Gemini API key in rotation."""
        with self._lock:
            if not self._gemini_keys:
                logger.error("No Gemini API keys found in environment variables.")
                raise ValueError("GEMINI_API_KEY is not configured.")
            
            key = self._gemini_keys[self._gemini_index]
            self._gemini_index = (self._gemini_index + 1) % len(self._gemini_keys)
            return key

    def get_groq_key(self) -> str:
        """Returns the next available Groq API key in rotation."""
        with self._lock:
            if not self._groq_keys:
                logger.error("No Groq API keys found in environment variables.")
                raise ValueError("GROQ_API_KEY is not configured.")
            
            key = self._groq_keys[self._groq_index]
            self._groq_index = (self._groq_index + 1) % len(self._groq_keys)
            return key

    def get_status(self):
        """Returns status of key pools."""
        return {
            "gemini": {"count": len(self._gemini_keys), "current_index": self._gemini_index},
            "groq": {"count": len(self._groq_keys), "current_index": self._groq_index}
        }

# Global instance for easy import
key_manager = KeyManager()
