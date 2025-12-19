"""Quick script to check the first ID in Supabase"""
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
env_paths = [
    Path('.env'),
    Path(__file__).resolve().parent / '.env',
    Path(__file__).resolve().parent / 'trulia_scraper' / '.env',
]

env_path = None
for path in env_paths:
    if path.exists():
        env_path = path
        break

if env_path:
    load_dotenv(dotenv_path=env_path, override=True)
else:
    load_dotenv(override=True)

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")

if not url or not key:
    print("Error: Missing Supabase credentials")
    exit(1)

supabase: Client = create_client(url, key)

# Check first record ID
first_record = supabase.table("trulia_listings").select("id").order("id", desc=False).limit(1).execute()
count_response = supabase.table("trulia_listings").select("id", count="exact").execute()

print(f"Total records: {count_response.count}")
if first_record.data:
    first_id = first_record.data[0]['id']
    print(f"First ID: {first_id}")
    if first_id == 1:
        print("[OK] IDs are starting from 1!")
    else:
        print(f"[WARN] First ID is {first_id}, not 1.")
        print("Run this SQL in Supabase to fix:")
        print("DELETE FROM trulia_listings;")
        print("ALTER SEQUENCE trulia_listings_id_seq RESTART WITH 1;")

