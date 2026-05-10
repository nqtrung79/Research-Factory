import re

def is_spam(content):
    """
    Simple heuristic spam check.
    """
    if not content or len(content.strip()) < 3:
        return True
    
    # Check for excessive links
    links = re.findall(r'http[s]?://', content)
    if len(links) > 2:
        return True
    
    # Check for repetitive characters
    if any(content.count(char) > 50 for char in set(content) if char not in " ."):
        return True
    
    # Check for excessive uppercase
    uppers = [c for c in content if c.isupper()]
    if len(content) > 20 and len(uppers) / len(content) > 0.6:
        return True

    return False
