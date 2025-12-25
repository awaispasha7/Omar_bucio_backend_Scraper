import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(Path(__file__).parent / '.env')
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

tables = [
    "listings",
    "zillow_fsbo_listings", 
    "zillow_frbo_listings",
    "trulia_listings",
    "redfin_listings",
    "hotpads_listings",
    "apartments_frbo_chicago"
]

print("TABLE COUNTS:")
total = 0
for t in tables:
    try:
        r = supabase.table(t).select("*", count="exact").limit(0).execute()
        c = r.count or 0
        total += c
        print(f"  {t}: {c}")
    except Exception as e:
        print(f"  {t}: ERROR - {e}")

print(f"\nTOTAL LISTINGS: {total}")

# Enrichment queue
try:
    q = supabase.table("property_owner_enrichment_state").select("*", count="exact").limit(0).execute()
    nc = supabase.table("property_owner_enrichment_state").select("*", count="exact").eq("status", "never_checked").limit(0).execute()
    print(f"\nENRICHMENT QUEUE: {q.count or 0} total, {nc.count or 0} pending")
except Exception as e:
    print(f"\nENRICHMENT QUEUE: ERROR - {e}")

# Property owners
try:
    po = supabase.table("property_owners").select("*", count="exact").limit(0).execute()
    print(f"PROPERTY OWNERS: {po.count or 0} records")
except Exception as e:
    print(f"PROPERTY OWNERS: ERROR - {e}")
