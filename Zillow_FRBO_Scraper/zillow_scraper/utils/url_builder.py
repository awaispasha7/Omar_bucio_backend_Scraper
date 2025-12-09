"""URL construction utilities for Zillow scraper"""


def build_rental_url(zipcode):
    """
    Build rental search URL for a given ZIP code
    
    Args:
        zipcode (str): ZIP code to search
        
    Returns:
        str: Complete Zillow rental search URL
    """
    return f"https://www.zillow.com/homes/for_rent/{zipcode}/"


def build_detail_url(home_data):
    """
    Build property detail URL from listing data
    
    Args:
        home_data (dict): Property listing dictionary
        
    Returns:
        str: Complete property detail URL
    """
    url = home_data.get('detailUrl', '')
    if not url.startswith("https"):
        return f'https://www.zillow.com{url}'
    return url
