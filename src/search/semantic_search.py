import streamlit as st
from semanticscholar import SemanticScholar
from loguru import logger
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer

s2 = SemanticScholar()

def get_summary(text, level):
    """Tóm tắt abstract dựa trên cấp bậc nghiên cứu"""
    if not text or text == "No abstract available.":
        return text
    
    # Định nghĩa số câu tóm tắt dựa trên cấp bậc
    # Càng cao cấp, càng giữ nhiều câu để tránh mất thông tin
    sentences_map = {"Undergraduate": 1, "Master": 2, "PhD": 3}
    count = sentences_map.get(level, 2)
    
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LsaSummarizer()
        summary = summarizer(parser.document, count)
        return " ".join([str(s) for s in summary])
    except:
        return text[:300] + "..." # Fallback nếu lỗi

@st.cache_data(ttl=3600)
def get_s2_results(query, limit, level):
    logger.info(f"Searching S2: {query} with limit {limit}")
    try:
        papers = s2.search_paper(
            query, limit=limit, 
            fields=['title', 'authors', 'year', 'abstract', 'url', 'doi']
        )
        results = []
        for p in papers:
            # Tóm tắt abstract ngay khi lấy về
            abstract = p.abstract or "No abstract available."
            results.append({
                "title": p.title or "No Title",
                "authors": [a.name for a in p.authors] if p.authors else [],
                "year": p.year or 0,
                "abstract": get_summary(abstract, level), # Đã tóm tắt!
                "doi": p.doi or "",
                "url": p.url or "",
                "source": "Semantic Scholar"
            })
        return results
    except Exception as e:
        logger.error(f"S2 Error: {e}")
        return []

class SemanticSearcher:
    def search(self, query: str, limit: int, level: str):
        return get_s2_results(query, limit, level)

searcher = SemanticSearcher()
