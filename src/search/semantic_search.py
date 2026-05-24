from semanticscholar import SemanticScholar
from loguru import logger

class SemanticSearcher:
    def __init__(self):
        # Bạn không cần API Key, thư viện tự kết nối
        self.s2 = SemanticScholar()

    def search(self, query: str, limit: int = 5):
        """Chỉ tìm kiếm duy nhất qua Semantic Scholar"""
        logger.info(f"Searching Semantic Scholar for: {query}")
        
        try:
            # Tìm kiếm và lấy các trường thông tin cần thiết
            results = self.s2.search_paper(
                query, 
                limit=limit, 
                fields=['title', 'authors', 'year', 'abstract', 'url', 'doi']
            )
            
            clean_results = []
            for p in results:
                clean_results.append({
                    "title": p.title or "No Title",
                    "authors": [a.name for a in p.authors] if p.authors else [],
                    "year": p.year or 0,
                    "abstract": p.abstract or "No abstract available.",
                    "doi": p.doi or "",
                    "url": p.url or "",
                    "source": "Semantic Scholar"
                })
            return clean_results
            
        except Exception as e:
            logger.error(f"Semantic Scholar Error: {e}")
            return []

# Khởi tạo để main.py gọi
searcher = SemanticSearcher()
