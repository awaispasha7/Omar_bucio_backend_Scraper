"""
Simple script to fix IDs starting from 1.
Run the SQL command in Supabase SQL Editor first, then run this script.
"""
import os
import csv
import re
from pathlib import Path
from datetime import datetime
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

def parse_beds_baths(beds_baths_str):
    """Parse '2 Beds 1.5 Baths' into separate beds and baths values"""
    if not beds_baths_str or beds_baths_str.strip() == '':
        return None, None
    beds_match = re.search(r'(\d+(?:\.\d+)?)\s*Bed', beds_baths_str, re.IGNORECASE)
    beds = beds_match.group(1) if beds_match else None
    baths_match = re.search(r'(\d+(?:\.\d+)?)\s*Bath', beds_baths_str, re.IGNORECASE)
    baths = baths_match.group(1) if baths_match else None
    return beds, baths

def clean_value(value):
    """Clean CSV values"""
    if not value or value.strip() == '' or value.strip().lower() == 'no data':
        return None
    return value.strip()

def fix_ids(csv_path):
    """Delete all records and re-upload to get IDs starting from 1"""
    
    print("=" * 60)
    print("Fix IDs - Delete and Re-upload")
    print("=" * 60)
    
    print("\nSTEP 1: Please run this SQL in Supabase SQL Editor first:")
    print("-" * 60)
    print("DELETE FROM trulia_listings;")
    print("ALTER SEQUENCE trulia_listings_id_seq RESTART WITH 1;")
    print("-" * 60)
    print("\nPress Enter after running the SQL commands...")
    input()
    
    print("\nConnecting to Supabase...")
    supabase: Client = create_client(url, key)
    print("[OK] Connected")
    
    # Read CSV
    print("\nReading CSV file...")
    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"[ERROR] CSV file not found: {csv_path}")
        return
    
    records_to_upload = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            listing_link = clean_value(row.get('Url', ''))
            if not listing_link:
                continue
            
            beds_baths_str = clean_value(row.get('Beds / Baths', ''))
            beds, baths = parse_beds_baths(beds_baths_str) if beds_baths_str else (None, None)
            
            data = {
                'listing_link': listing_link,
                'address': clean_value(row.get('Address', '')),
                'price': clean_value(row.get('Asking Price', '')),
                'beds': beds,
                'baths': baths,
                'owner_name': clean_value(row.get('Owner Name', '')),
                'mailing_address': clean_value(row.get('Mailing Address', '')),
                'emails': clean_value(row.get('Email', '')),
                'phones': clean_value(row.get('Phone Number', '')),
                'square_feet': None,
                'property_type': None,
                'lot_size': None,
                'description': None,
                'scrape_date': datetime.now().strftime('%Y-%m-%d'),
            }
            records_to_upload.append(data)
    
    print(f"[OK] Prepared {len(records_to_upload)} records")
    
    # Upload
    print("\nUploading to Supabase...")
    batch_size = 100
    total_uploaded = 0
    
    for i in range(0, len(records_to_upload), batch_size):
        batch = records_to_upload[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(records_to_upload) + batch_size - 1) // batch_size
        
        try:
            supabase.table("trulia_listings").insert(batch).execute()
            total_uploaded += len(batch)
            print(f"[OK] Batch {batch_num}/{total_batches}: {len(batch)} records")
        except Exception as e:
            print(f"[ERROR] Batch {batch_num}: {e}")
    
    # Verify
    print("\nVerifying...")
    try:
        count_response = supabase.table("trulia_listings").select("id", count="exact").execute()
        first_record = supabase.table("trulia_listings").select("id").order("id", desc=False).limit(1).execute()
        
        print(f"Total records: {count_response.count}")
        if first_record.data:
            first_id = first_record.data[0]['id']
            print(f"First ID: {first_id}")
            if first_id == 1:
                print("[OK] IDs start from 1!")
            else:
                print(f"[WARN] First ID is {first_id}. Sequence may need manual reset.")
    except Exception as e:
        print(f"[WARN] Verification failed: {e}")
    
    print("\n[OK] Done!")

if __name__ == "__main__":
    fix_ids("output/Trulia_Data.csv")

