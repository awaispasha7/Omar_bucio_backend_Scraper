
import os
import sys
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def check_truncated():
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
    
    print("--- TRUNCATION CHECK ---")
    
    for table in tables:
        try:
            res = supabase.table(table).select('id, address_hash').execute()
            data = res.data
            if not data:
                print(f"[{table}]: Empty")
                continue
                
            truncated = [item for item in data if item.get('address_hash') and len(str(item['address_hash'])) < 32]
            missing = [item for item in data if not item.get('address_hash')]
            
            print(f"[{table}]:")
            print(f"  Total Listings: {len(data)}")
            print(f"  Truncated Hashes (<32 chars): {len(truncated)}")
            print(f"  Missing Hashes: {len(missing)}")
            if truncated:
                print(f"  Example Truncated: ID {truncated[0]['id']} -> {truncated[0]['address_hash']}")
                
        except Exception as e:
            print(f"[{table}]: Error - {e}")

if __name__ == "__main__":
    check_truncated()
