import PyPDF2
import io
from loguru import logger

def extract_abstract_from_pdf(pdf_file):
    """
    Extracts text from a PDF file and tries to find the abstract.
    """
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_file.read()))
        full_text = ""
        # Only read the first 2 pages to find the abstract
        for i in range(min(len(reader.pages), 2)):
            full_text += reader.pages[i].extract_text()
        
        # Simple extraction logic: find 'Abstract' keyword
        abstract_start = full_text.lower().find("abstract")
        if abstract_start != -1:
            # Try to find the next section (Introduction or similar) as end point
            intro_start = full_text.lower().find("introduction", abstract_start)
            if intro_start != -1:
                return full_text[abstract_start:intro_start].strip()
            return full_text[abstract_start:abstract_start + 2000].strip() # Fallback to 2000 chars
        
        return full_text[:1500].strip() # Just send the first chunk if no abstract keyword found
    except Exception as e:
        logger.error(f"Error extracting PDF: {e}")
        return ""
