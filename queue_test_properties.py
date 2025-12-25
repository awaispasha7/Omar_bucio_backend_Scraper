import os
import hashlib
from supabase import create_client
from dotenv import load_dotenv

def main():
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
    supabase = create_client(url, key)

    print("--- Queuing 2 Properties for Testing ---")
    
    # 1. Get 2 listings from Zillow FSBO
    res = supabase.table("zillow_fsbo_listings").select("address").limit(2).execute()
    if not res.data:
        print("Error: No listings found in zillow_fsbo_listings table.")
        return

    for item in res.data:
        address = item['address']
        # Generate hash (MD5 as used in the project)
        normalized = address.upper().strip() # Simple normalization for test
        addr_hash = hashlib.md5(normalized.encode('utf-8')).hexdigest()
        
        print(f"Queuing: {address}")
        
        # 2. Insert into enrichment_state
        try:
            supabase.table("property_owner_enrichment_state").upsert({
                "address_hash": addr_hash,
                "normalized_address": address,
                "status": "never_checked",
                "locked": False
            }).execute()
            print(f"  Result: Success (Hash: {addr_hash})")
        except Exception as e:
            print(f"  Result: Error - {e}")

if __name__ == "__main__":
    main()
