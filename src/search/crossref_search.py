from habanero import Crossref
from loguru import logger
from typing import List, Dict, Any
import os

class CrossrefSearcher:
    """Wrapper for Crossref API to search academic papers."""
    
    def __init__(self):
        self.cr = Crossref(mailto=os.getenv("CROSSREF_EMAIL", "scholar@example.com"))
        self.timeout = int(os.getenv("CROSSREF_TIMEOUT", "10"))

    def search_papers(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for academic papers.
        Limit is determined by the research tier (Student=1, Master=3, PhD=5, Project=10).
        """
        try:
            logger.info(f"Searching Crossref for: {query} with limit {limit}")
            res = self.cr.works(query=query, limit=limit, select=["title", "author", "published-print", "abstract", "DOI", "URL"])
            
            items = res.get('message', {}).get('items', [])
            results = []
            
            for item in items:
                results.append({
                    "title": item.get('title', ["No Title"])[0],
                    "authors": [a.get('family', '') for a in item.get('author', [])],
                    "year": item.get('published-print', {}).get('date-parts', [[0]])[0][0],
                    "abstract": item.get('abstract', "No abstract available."),
                    "doi": item.get('DOI', ''),
                    "url": item.get('URL', ''),
                    "source": "Crossref"
                })
            return results
        except Exception as e:
            logger.error(f"Crossref Search Error: {str(e)}")
            return []

crossref_searcher = CrossrefSearcher()
