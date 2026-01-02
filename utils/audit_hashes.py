
import os
import sys
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def audit_hash_lengths():
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
        'apartments_listings',
        'property_owners',
        'property_owner_enrichment_state'
    ]
    
    print("--- GLOBAL HASH LENGTH AUDIT ---")
    
    for table in tables:
        try:
            res = supabase.table(table).select('address_hash').limit(10).execute()
            if res.data:
                lengths = [len(str(item['address_hash'])) for item in res.data if item.get('address_hash')]
                avg_len = sum(lengths) / len(lengths) if lengths else 0
                max_len = max(lengths) if lengths else 0
                min_len = min(lengths) if lengths else 0
                
                print(f"[{table}]:")
                print(f"  Count: {len(res.data)}")
                print(f"  Hash Lengths: Min={min_len}, Max={max_len}, Avg={avg_len:.1f}")
                if len(res.data) > 0:
                   example = res.data[0]['address_hash']
                   print(f"  Example: {example}")
            else:
                print(f"[{table}]: Table empty or no address_hash")
        except Exception as e:
            print(f"[{table}]: Error - {e}")

if __name__ == "__main__":
    audit_hash_lengths()
