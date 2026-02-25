import re
import hashlib

def normalize_address(address):
    """
    Normalizes a US address for consistent hashing.
    Examples: 
    - "123 Main Street" -> "123 MAIN ST"
    - "Apt 4B" -> "UNIT 4B"
    """
    if not address:
        return ""
        
    # Standardize to uppercase and strip whitespace
    addr = str(address).upper().strip()
    
    # Remove common punctuation
    addr = re.sub(r'[.,#\-]', ' ', addr)
    addr = re.sub(r'\s+', ' ', addr).strip()
    
    # Common Suffix Abbreviations
    suffixes = {
        r'\bSTREET\b': 'ST',
        r'\bAVENUE\b': 'AVE',
        r'\bBOULEVARD\b': 'BLVD',
        r'\bDRIVE\b': 'DR',
        r'\bLANE\b': 'LN',
        r'\bCOURT\b': 'CT',
        r'\bROAD\b': 'RD',
        r'\bPLACE\b': 'PL',
        r'\bSQUARE\b': 'SQ',
        r'\bTERRACE\b': 'TER',
        r'\bPARKWAY\b': 'PKWY',
        r'\bCIRCLE\b': 'CIR',
        r'\bTRAIL\b': 'TRL',
        r'\bAPARTMENT\b': 'UNIT',
        r'\bAPT\b': 'UNIT',
        r'\bSTE\b': 'UNIT',
        r'\bSUITE\b': 'UNIT',
        r'\bFL\b': 'UNIT',
        r'\bFLOOR\b': 'UNIT',
    }
    
    for pattern, replacement in suffixes.items():
        addr = re.sub(pattern, replacement, addr)
        
    # Directions
    directions = {
        r'\bNORTH\b': 'N',
        r'\bSOUTH\b': 'S',
        r'\bEAST\b': 'E',
        r'\bWEST\b': 'W',
        r'\bNORTHEAST\b': 'NE',
        r'\bNORTHWEST\b': 'NW',
        r'\bSOUTHEAST\b': 'SE',
        r'\bSOUTHWEST\b': 'SW',
    }
    
    for pattern, replacement in directions.items():
        addr = re.sub(pattern, replacement, addr)
        
    # Remove extra spaces again after replacements
    addr = re.sub(r'\s+', ' ', addr).strip()
    
    return addr

def generate_address_hash(normalized_address):
    """
    Generates a unique MD5 hash for a normalized address.
    """
    if not normalized_address:
        return None
    return hashlib.md5(normalized_address.encode('utf-8')).hexdigest()


def redfin_address_from_url(url):
    """
    Parse a Redfin property URL into a readable address.
    URL format: https://www.redfin.com/IL/Chicago/4323-W-Peterson-Ave-60648/home/123456
    Returns e.g. "4323 W Peterson Ave, Chicago, IL 60648" (no "home," or raw slug).
    """
    if not url:
        return ""
    parts = [p for p in str(url).rstrip("/").split("/") if p]
    # .../STATE/City/Street-Slug-Zip/home/ID -> state=STATE, city=City, street_slug=Street-Slug-Zip
    if len(parts) < 5:
        return ""
    # Find "home" and take the segment before it as street slug, before that as city, before that as state
    try:
        home_idx = parts.index("home") if "home" in parts else -1
        if home_idx >= 3:
            street_slug = parts[home_idx - 1]  # e.g. 4323-W-Peterson-Ave-60648
            city = parts[home_idx - 2]  # e.g. Chicago
            state = parts[home_idx - 3]  # e.g. IL
        else:
            # Fallback: last meaningful segments before id
            state = parts[-5] if len(parts) >= 5 else ""
            city = parts[-4] if len(parts) >= 4 else ""
            street_slug = parts[-3] if len(parts) >= 3 else ""
        # Convert slug to readable: 4323-W-Peterson-Ave-60648 -> 4323 W Peterson Ave, 60648
        street_slug = street_slug.replace("-", " ").strip()
        # Capitalize words (and keep digits)
        street_parts = street_slug.split()
        formatted = []
        for w in street_parts:
            if w.isdigit():
                formatted.append(w)
            else:
                formatted.append(w.capitalize() if w else w)
        street_display = " ".join(formatted)
        # If last token looks like zip (5 digits), keep as "Street, City, ST Zip"
        if len(formatted) >= 2 and formatted[-1].isdigit() and len(formatted[-1]) == 5:
            street_display = " ".join(formatted[:-1])
            zip_code = formatted[-1]
            return f"{street_display}, {city}, {state} {zip_code}".strip(", ")
        return f"{street_display}, {city}, {state}".strip(", ")
    except (ValueError, IndexError):
        return ""
