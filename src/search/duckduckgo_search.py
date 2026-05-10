from duckduckgo_search import DDGS
from loguru import logger
from typing import List, Dict, Any

class DuckDuckGoSearcher:
    """Wrapper for DuckDuckGo to search general web and news results."""
    
    def search_web(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search the web for general context and news."""
        results = []
        try:
            with DDGS() as ddgs:
                ddgs_gen = ddgs.text(query, max_results=limit)
                for r in ddgs_gen:
                    results.append({
                        "title": r.get('title'),
                        "link": r.get('href'),
                        "snippet": r.get('body'),
                        "source": "DuckDuckGo"
                    })
            return results
        except Exception as e:
            logger.error(f"DuckDuckGo Search Error: {str(e)}")
            return []

duckduckgo_searcher = DuckDuckGoSearcher()
