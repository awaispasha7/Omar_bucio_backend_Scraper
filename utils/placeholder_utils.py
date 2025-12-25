import re

# Known platform placeholder domains and specific emails
PLACEHOLDER_DOMAINS = [
    'hotpads.com',
    'zillow.com',
    'trulia.com',
    'apartments.com',
    'redfin.com',
    'streetlines.com',
]

PLACEHOLDER_EMAILS = [
    'support@hotpads.com',
    'noreply@zillow.com',
    'contact@trulia.com',
    'help@apartments.com',
]

# Patterns for fake or generic phone numbers
PLACEHOLDER_PHONE_PATTERNS = [
    r'000-000-0000',
    r'111-111-1111',
    r'123-456-7890',
    r'\(800\) 000-0000',
]

def is_placeholder_email(email):
    """
    Checks if an email is a platform placeholder.
    """
    if not email:
        return True
    
    email = str(email).lower().strip()
    
    if email in PLACEHOLDER_EMAILS:
        return True
        
    for domain in PLACEHOLDER_DOMAINS:
        if email.endswith(f"@{domain}"):
            return True
            
    return False

def is_placeholder_phone(phone):
    """
    Checks if a phone number is a placeholder.
    """
    if not phone:
        return True
        
    phone_clean = re.sub(r'\D', '', str(phone))
    
    # Check if it's all same digits (0000000000)
    if len(phone_clean) >= 10 and len(set(phone_clean)) == 1:
        return True
        
    # Check common fake patterns
    for pattern in PLACEHOLDER_PHONE_PATTERNS:
        if re.search(pattern, str(phone)):
            return True
            
    return False

def clean_owner_data(owner_name, email, phone):
    """
    Cleans owner data, returning None for placeholders.
    """
    clean_email = email if not is_placeholder_email(email) else None
    clean_phone = phone if not is_placeholder_phone(phone) else None
    
    # If name is just "Support" or "Admin", it's likely a placeholder
    clean_name = owner_name
    if owner_name and str(owner_name).lower().strip() in ['support', 'admin', 'hotpads support', 'listing agent']:
        clean_name = None
        
    return clean_name, clean_email, clean_phone
