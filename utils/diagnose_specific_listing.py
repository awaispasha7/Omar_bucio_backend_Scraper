
import os
import sys
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def diagnose_hashes():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("Missing credentials")
        return

    supabase = create_client(url, key)
    
    tables = [
        'zillow_fsbo_listings',
        'zillow_frbo_listings',
        'hotpads_listings',
        'trulia_listings',
        'redfin_listings',
        'apartments_listings'
    ]
    
    print("--- HASH LENGTH DIAGNOSTIC ---")
    
    # Check property_owners first
    print("\n[Target] property_owners:")
    res_owner = supabase.table('property_owners').select('address_hash').limit(1).execute()
    if res_owner.data:
        h = res_owner.data[0]['address_hash']
        print(f"  Example Hash: {h} (Length: {len(h) if h else 0})")
    
    for table in tables:
        print(f"\n[{table}]:")
        res = supabase.table(table).select('address_hash').limit(1).execute()
        if res.data:
            h = res.data[0]['address_hash']
            print(f"  Example Hash: {h} (Length: {len(h) if h else 0})")
        else:
            print("  Table empty")

if __name__ == "__main__":
    diagnose_hashes()

if __name__ == "__main__":
    diagnose_listing()
