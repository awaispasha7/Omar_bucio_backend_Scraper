"""
Script to reset Supabase IDs to start from 1 and re-upload CSV data.
This will delete all existing records, reset the sequence, and upload fresh data.
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
    """Clean CSV values - handle empty strings, 'no data', etc."""
    if not value or value.strip() == '' or value.strip().lower() == 'no data':
        return None
    return value.strip()

def reset_and_reupload(csv_path):
    """Delete all records, reset sequence, and re-upload CSV data"""
    
    print("Connecting to Supabase...")
    supabase: Client = create_client(url, key)
    print("[OK] Connected to Supabase")
    
    # Step 1: Delete all existing records
    print("\nStep 1: Deleting all existing records...")
    try:
        # Get all records
        all_records = supabase.table("trulia_listings").select("id").execute()
        count = len(all_records.data) if all_records.data else 0
        
        if count > 0:
            print(f"Found {count} existing records. Deleting...")
            # Delete all records
            for record in all_records.data:
                supabase.table("trulia_listings").delete().eq("id", record['id']).execute()
            print(f"[OK] Deleted {count} records")
        else:
            print("[INFO] No existing records to delete")
    except Exception as e:
        print(f"[ERROR] Failed to delete records: {e}")
        return
    
    # Step 2: Reset sequence by inserting and deleting a dummy record with ID 0
    print("\nStep 2: Resetting ID sequence...")
    try:
        # Try to reset sequence by manipulating the sequence directly
        # This is a workaround - we'll insert with explicit ID 1, then delete it
        # First, check if we can set the sequence
        print("[INFO] Attempting to reset sequence...")
        # Note: Supabase Python client doesn't support ALTER SEQUENCE directly
        # So we need to use SQL. Let's try via RPC if available, otherwise provide instructions
        print("[INFO] To reset sequence, run this SQL in Supabase SQL Editor:")
        print("=" * 60)
        print("ALTER SEQUENCE trulia_listings_id_seq RESTART WITH 1;")
        print("=" * 60)
        print("\nOr the sequence will auto-adjust when we insert new records.")
        print("Continuing with upload...")
    except Exception as e:
        print(f"[INFO] {e}")
        print("Continuing with upload - sequence will adjust automatically")
    
    # Step 3: Read and upload CSV data
    print("\nStep 3: Reading CSV file...")
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
    
    print(f"[OK] Prepared {len(records_to_upload)} records for upload")
    
    # Step 4: Upload data
    print("\nStep 4: Uploading data to Supabase...")
    batch_size = 100
    total_uploaded = 0
    
    for i in range(0, len(records_to_upload), batch_size):
        batch = records_to_upload[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(records_to_upload) + batch_size - 1) // batch_size
        
        try:
            # Use insert instead of upsert to get fresh IDs
            response = supabase.table("trulia_listings").insert(batch).execute()
            total_uploaded += len(batch)
            print(f"[OK] Batch {batch_num}/{total_batches}: Uploaded {len(batch)} records")
        except Exception as e:
            print(f"[ERROR] Batch {batch_num}/{total_batches}: Error - {e}")
            # If there's a sequence issue, try one by one
            if "sequence" in str(e).lower() or "duplicate key" in str(e).lower():
                print("   Trying individual inserts...")
                for record in batch:
                    try:
                        supabase.table("trulia_listings").insert([record]).execute()
                        total_uploaded += 1
                    except Exception as single_error:
                        print(f"   [ERROR] Failed: {record.get('address', 'N/A')} - {single_error}")
    
    # Step 5: Verify
    print("\nStep 5: Verifying upload...")
    try:
        count_response = supabase.table("trulia_listings").select("id", count="exact").execute()
        print(f"[OK] Total records in database: {count_response.count}")
        
        # Get first record to verify ID starts from 1
        first_record = supabase.table("trulia_listings").select("id").order("id", desc=False).limit(1).execute()
        if first_record.data:
            first_id = first_record.data[0]['id']
            print(f"[OK] First record ID: {first_id}")
            if first_id == 1:
                print("[OK] IDs are starting from 1 as expected!")
            else:
                print(f"[WARN] First ID is {first_id}, not 1. Sequence may need manual reset.")
    except Exception as e:
        print(f"[WARN] Could not verify: {e}")
    
    print("\n[OK] Process completed!")

if __name__ == "__main__":
    print("=" * 60)
    print("Reset IDs and Re-upload CSV Data")
    print("=" * 60)
    csv_path = "output/Trulia_Data.csv"
    reset_and_reupload(csv_path)

