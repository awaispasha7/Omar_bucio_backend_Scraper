"""URL construction utilities for Trulia scraper"""
from urllib.parse import quote


def build_rental_url(location):
    """
    Build FSBO search URL for a given location using Trulia's FSBO format
    
    Args:
        location (str): Location like "Chicago,IL" or zipcode
        
    Returns:
        str: Complete Trulia FSBO search URL in format: https://www.trulia.com/for_sale/{location}/fsbo_lt/1_als/
    """
    # Exact format: https://www.trulia.com/for_sale/{location}/fsbo_lt/1_als/
    # URL encode the location to handle special characters
    encoded_location = quote(location, safe=',')
    return f"https://www.trulia.com/for_sale/{encoded_location}/fsbo_lt/1_als/"


def build_detail_url(home_data):
    """
    Build property detail URL from listing data
    
    Args:
        home_data (dict): Property listing dictionary
        
    Returns:
        str: Complete property detail URL
    """
    url = home_data.get('detailUrl', '') or home_data.get('url', '') or home_data.get('href', '')
    if not url:
        return ''
    if not url.startswith("https"):
        return f'https://www.trulia.com{url}'
    return url