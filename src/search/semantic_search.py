import streamlit as st
from semanticscholar import SemanticScholar
from loguru import logger

# Khởi tạo s2 là một instance duy nhất (Singleton pattern)
s2 = SemanticScholar()

@st.cache_data(ttl=3600) # Lưu cache 1 giờ để không tốn token/API call
def get_s2_results(query, limit):
    logger.info(f"Searching S2: {query} with limit {limit}")
    try:
        papers = s2.search_paper(
            query, 
            limit=limit, 
            fields=['title', 'authors', 'year', 'abstract', 'url', 'doi']
        )
        # Chuyển đổi sang list dictionary ngay tại đây
        return [{
            "title": p.title or "No Title",
            "authors": [a.name for a in p.authors] if p.authors else [],
            "year": p.year or 0,
            "abstract": p.abstract or "No abstract available.",
            "doi": p.doi or "",
            "url": p.url or "",
            "source": "Semantic Scholar"
        } for p in papers]
    except Exception as e:
        logger.error(f"Semantic Scholar Error: {e}")
        return []

class SemanticSearcher:
    def search(self, query: str, limit: int = 5):
        # Truyền limit từ main.py vào đây
        return get_s2_results(query, limit)

searcher = SemanticSearcher()
