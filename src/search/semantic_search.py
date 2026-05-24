import streamlit as st
from semanticscholar import SemanticScholar
from loguru import logger

s2 = SemanticScholar()

@st.cache_data(ttl=3600)
def get_s2_results(query, limit):
    logger.info(f"Searching S2: {query} with limit {limit}")
    try:
        # Giới hạn số lượng tài liệu theo đúng limit truyền vào
        papers = s2.search_paper(
            query, 
            limit=limit, 
            fields=['title', 'authors', 'year', 'abstract', 'url', 'doi']
        )
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
    # Không cần limit mặc định là 5 ở đây nữa, hãy để nó lấy từ main.py
    def search(self, query: str, limit: int):
        return get_s2_results(query, limit)

searcher = SemanticSearcher()
