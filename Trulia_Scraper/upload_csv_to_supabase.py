import os
import csv
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
# Try multiple locations for .env file
env_paths = [
    Path('.env'),  # Current directory
    Path(__file__).resolve().parent / '.env',  # Script directory
    Path(__file__).resolve().parent / 'trulia_scraper' / '.env',  # trulia_scraper subdirectory
    Path(__file__).resolve().parents[1] / '.env',  # Parent directory
]

env_path = None
for path in env_paths:
    if path.exists():
        env_path = path
        break

if env_path:
    print(f"Loading .env from: {env_path.absolute()}")
    print(f"File exists: {env_path.exists()}")
    # Force override
    loaded = load_dotenv(dotenv_path=env_path, override=True)
    print(f"load_dotenv returned: {loaded}")
else:
    print("Warning: .env file not found in any of the following locations:")
    for path in env_paths:
        print(f"  - {path.absolute()}")
    print("Attempting to load from environment variables...")
    # Try loading without specifying path (will use default .env in current dir)
    loaded = load_dotenv(override=True)

# Try to get credentials from environment (either from .env or system env vars)
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")

print(f"SUPABASE_URL: '{url}'")
# Mask key for security
masked_key = f"{key[:10]}...{key[-5:]}" if key else "None"
print(f"SUPABASE_SERVICE_KEY: '{masked_key}'")

if not url or not key:
    print("\n" + "="*60)
    print("ERROR: Missing Supabase credentials")
    print("="*60)
    print("Please create a .env file in the project root with:")
    print("  SUPABASE_URL=your_supabase_url")
    print("  SUPABASE_SERVICE_KEY=your_service_key")
    print("\nOr set them as system environment variables:")
    print("  $env:SUPABASE_URL='your_url'")
    print("  $env:SUPABASE_SERVICE_KEY='your_key'")
    print("="*60)
    exit(1)

def parse_beds_baths(beds_baths_str):
    """Parse '2 Beds 1.5 Baths' into separate beds and baths values"""
    if not beds_baths_str or beds_baths_str.strip() == '':
        return None, None
    
    # Extract beds
    beds_match = re.search(r'(\d+(?:\.\d+)?)\s*Bed', beds_baths_str, re.IGNORECASE)
    beds = beds_match.group(1) if beds_match else None
    
    # Extract baths
    baths_match = re.search(r'(\d+(?:\.\d+)?)\s*Bath', beds_baths_str, re.IGNORECASE)
    baths = baths_match.group(1) if baths_match else None
    
    return beds, baths

def clean_value(value):
    """Clean CSV values - handle empty strings, 'no data', etc."""
    if not value or value.strip() == '' or value.strip().lower() == 'no data':
        return None
    return value.strip()

def upload_csv_to_supabase(csv_path):
    """Upload CSV data to Supabase trulia_listings table"""
    
    # Initialize Supabase client
    print("Connecting to Supabase...")
    supabase: Client = create_client(url, key)
    print("[OK] Connected to Supabase")
    
    # Read CSV file
    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"[ERROR] CSV file not found: {csv_path}")
        return
    
    print(f"Reading CSV file: {csv_file}")
    
    records_to_upload = []
    skipped_count = 0
    total_rows = 0
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 because row 1 is header
            total_rows += 1
            # Skip rows without listing_link (Url)
            listing_link = clean_value(row.get('Url', ''))
            if not listing_link:
                # Check if row has any data at all
                has_data = any(clean_value(row.get(key, '')) for key in row.keys())
                if has_data:
                    print(f"[WARN] Row {row_num}: Skipping - has data but no URL")
                else:
                    print(f"[WARN] Row {row_num}: Skipping - empty row")
                skipped_count += 1
                continue
            
            # Parse beds and baths from "Beds / Baths" column
            beds_baths_str = clean_value(row.get('Beds / Baths', ''))
            beds, baths = parse_beds_baths(beds_baths_str) if beds_baths_str else (None, None)
            
            # Prepare data for Supabase
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
                # Fields not in CSV - set to None
                'square_feet': None,
                'property_type': None,
                'lot_size': None,
                'description': None,
                'scrape_date': datetime.now().strftime('%Y-%m-%d'),
            }
            
            records_to_upload.append(data)
            print(f"[OK] Row {row_num}: Prepared - {data.get('address', 'N/A')}")
    
    if not records_to_upload:
        print("[ERROR] No records to upload")
        return
    
    print(f"\nUploading {len(records_to_upload)} records to Supabase...")
    
    # Upload in batches (Supabase has limits on batch size)
    batch_size = 100
    total_uploaded = 0
    total_errors = 0
    
    for i in range(0, len(records_to_upload), batch_size):
        batch = records_to_upload[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(records_to_upload) + batch_size - 1) // batch_size
        
        try:
            # Use upsert to handle duplicates based on listing_link
            response = supabase.table("trulia_listings").upsert(
                batch,
                on_conflict="listing_link"
            ).execute()
            
            total_uploaded += len(batch)
            print(f"[OK] Batch {batch_num}/{total_batches}: Uploaded {len(batch)} records")
            
        except Exception as e:
            total_errors += len(batch)
            print(f"[ERROR] Batch {batch_num}/{total_batches}: Error - {e}")
            # Try uploading one by one to identify problematic records
            for record in batch:
                try:
                    supabase.table("trulia_listings").upsert(
                        [record],
                        on_conflict="listing_link"
                    ).execute()
                    total_uploaded += 1
                    total_errors -= 1
                except Exception as single_error:
                    print(f"   [ERROR] Failed record: {record.get('listing_link', 'N/A')} - {single_error}")
    
    print(f"\nUpload Summary:")
    print(f"   Total rows in CSV (excluding header): {total_rows}")
    print(f"   [OK] Successfully uploaded: {total_uploaded}")
    print(f"   [ERROR] Errors: {total_errors}")
    print(f"   [WARN] Skipped (no URL or empty): {skipped_count}")
    print(f"   Total processed: {len(records_to_upload) + skipped_count}")
    
    # Verify count and first ID in Supabase
    try:
        count_response = supabase.table("trulia_listings").select("id", count="exact").execute()
        print(f"\nVerification:")
        print(f"   Total records in Supabase trulia_listings table: {count_response.count}")
        
        # Check first record ID
        first_record = supabase.table("trulia_listings").select("id").order("id", desc=False).limit(1).execute()
        if first_record.data:
            first_id = first_record.data[0]['id']
            print(f"   First record ID: {first_id}")
            if first_id == 1:
                print("   [OK] IDs are starting from 1!")
            else:
                print(f"   [WARN] First ID is {first_id}. Run the SQL to reset sequence:")
                print("   DELETE FROM trulia_listings;")
                print("   ALTER SEQUENCE trulia_listings_id_seq RESTART WITH 1;")
    except Exception as e:
        print(f"\n[WARN] Could not verify count in Supabase: {e}")

if __name__ == "__main__":
    # Path to CSV file
    csv_path = "output/Trulia_Data.csv"
    
    print("=" * 60)
    print("Trulia CSV to Supabase Uploader")
    print("=" * 60)
    
    upload_csv_to_supabase(csv_path)
    
    print("\n[OK] Upload process completed!")

