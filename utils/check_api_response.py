
import requests
import json

url = 'https://scraperfrontend-production.up.railway.app/api/zillow-frbo-listings'
print(f"Fetching: {url}")

try:
    r = requests.get(url)
    data = r.json()
    listings = data.get('listings', [])
    
    target_address = "5015 W Jackson"
    results = [l for l in listings if target_address in l.get('address', '')]
    
    print(f"Found {len(results)} matching listings:")
    for l in results:
        print("\n--- Listing ---")
        print(f"ID: {l.get('id')}")
        print(f"Address: {l.get('address')}")
        print(f"Status: {l.get('enrichment_status')}")
        print(f"Owner Name: {l.get('owner_name')}")
        print(f"Hash: {l.get('address_hash')}")
        print(f"Has Owner Data? {bool(l.get('owner_name') or l.get('owner_email') or l.get('owner_phone'))}")

except Exception as e:
    print(f"Error: {e}")
