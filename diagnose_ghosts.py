
import os
import json
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

targets = [
    "3550 N LAKE SHORE",
    "1061 W 16TH ST"
]

print("--- DIAGNOSTIC START ---")

for t in targets:
    print(f"\nScanning for: {t}")
    # 1. Get Enrichment State (Hash + Status)
    res = supabase.table("property_owner_enrichment_state") \
        .select("*") \
        .ilike("normalized_address", f"%{t}%") \
        .execute()
    
    if not res.data:
        print("  [State] NOT FOUND in enrichment_state")
        continue

    state_row = res.data[0]
    h = state_row['address_hash']
    print(f"  [State] FOUND. Hash: {h}")
    print(f"  [State] Status: {state_row.get('status')}")
    print(f"  [State] Source: {state_row.get('listing_source')}")
    print(f"  [State] Checked At: {state_row.get('checked_at')}")
    
    # 2. Check Property Owners (Did we save the payload?)
    res_owner = supabase.table("property_owners") \
        .select("*") \
        .eq("address_hash", h) \
        .execute()
    
    if res_owner.data:
        print(f"  [Owner] FOUND. Name: {res_owner.data[0].get('owner_name')}")
    else:
        print("  [Owner] MISSING! (Split Brain detected: Enriched in state, but no data saved)")

    # 3. Check Listings (Does the listing exist?)
    # Try generic 'listings' table (FSBO)
    res_listing = supabase.table("listings") \
        .select("*") \
        .eq("address_hash", h) \
        .execute()
        
    if res_listing.data:
         print(f"  [Listing] FOUND in 'listings'. Address: {res_listing.data[0].get('address')}")
    else:
         print("  [Listing] NOT FOUND by Hash in 'listings'")
         # Fallback check by generic address match
         res_add = supabase.table("listings").select("*").ilike("address", f"%{t}%").execute()
         if res_add.data:
             print(f"  [Listing] ... but FOUND by Address text! Listings Hash: {res_add.data[0].get('address_hash')}")
             if res_add.data[0].get('address_hash') != h:
                 print(f"  [MISMATCH] Hash mismatch! State Hash: {h} vs Listing Hash: {res_add.data[0].get('address_hash')}")
         else:
             print("  [Listing] DEFINITELY MISSING from 'listings' table.")

print("\n--- DIAGNOSTIC END ---")
