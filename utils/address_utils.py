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
