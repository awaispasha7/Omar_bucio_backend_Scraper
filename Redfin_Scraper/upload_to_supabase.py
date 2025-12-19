"""
Script to upload redfin_listings_rows.csv data to Supabase redfin_listings table
"""
import csv
import os
import re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Try to import supabase
try:
    from supabase import create_client, Client
except ImportError:
    print("Error: supabase-py library not installed.")
    print("Please install it with: pip install supabase")
    exit(1)

# Load environment variables - check both root and redfin_FSBO_backend directories
project_root = Path(__file__).resolve().parent
env_paths = [
    project_root / '.env',
    project_root / 'redfin_FSBO_backend' / '.env',
]

# Try loading from each location
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print(f"Loaded .env from: {env_path}")
        break
else:
    # If no .env found, try default location
    load_dotenv()

# Supabase configuration - try SERVICE_KEY first, then ANON_KEY
SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY', '') or os.getenv('SUPABASE_ANON_KEY', '') or os.getenv('SUPABASE_KEY', '')

# CSV file path
CSV_FILE = Path('outputs/redfin_listings_rows.csv')

def extract_beds_baths(beds_baths_str):
    """Extract beds and baths from 'Beds / Baths' format like '2 / 1' or '4 / 2.5'"""
    beds = ""
    baths = ""
    
    if beds_baths_str:
        # Match pattern like "2 / 1" or "4 / 2.5"
        match = re.search(r'(\d+)\s*/\s*(\d+\.?\d*)', beds_baths_str)
        if match:
            beds = match.group(1)
            baths = match.group(2)
    
    return beds, baths

def clean_price(price_str):
    """Clean price string, remove $ and commas"""
    if not price_str:
        return ""
    
    # Remove $ and commas, keep only digits
    cleaned = re.sub(r'[^\d]', '', price_str)
    return cleaned if cleaned else price_str

def read_csv_data():
    """Read data from CSV file"""
    data = []
    
    if not CSV_FILE.exists():
        print(f"Error: CSV file not found: {CSV_FILE}")
        return data
    
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Extract beds and baths
            beds, baths = extract_beds_baths(row.get('Beds / Baths', ''))
            
            # Prepare data for Supabase
            record = {
                'address': row.get('Address', '').strip() or None,
                'price': clean_price(row.get('Asking Price', '')) or None,
                'beds': beds or None,
                'baths': baths or None,
                'square_feet': row.get('Square Feet', '').strip() or None,
                'listing_link': row.get('Url', '').strip() or None,
                'property_type': None,  # Not in CSV
                'county': None,  # Not in CSV
                'lot_acres': None,  # Not in CSV
                'owner_name': row.get('Owner Name', '').strip() or None,
                'mailing_address': row.get('Mailing Address', '').strip() or None,
                'scrape_date': datetime.now().strftime('%Y-%m-%d'),
                'emails': row.get('Email', '').strip() or None,
                'phones': row.get('Phone Number', '').strip() or None,
            }
            
            # Only add if we have at least address or listing_link
            if record['address'] or record['listing_link']:
                data.append(record)
    
    return data

def upload_to_supabase(data):
    """Upload data to Supabase"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        print("Please add the following to your .env file:")
        print("SUPABASE_URL=your_supabase_url")
        print("SUPABASE_KEY=your_supabase_key")
        return False
    
    try:
        # Create Supabase client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        print(f"\nUploading {len(data)} records to Supabase...")
        
        # Insert data in batches (Supabase allows up to 1000 rows per insert)
        batch_size = 100
        total_inserted = 0
        
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            
            try:
                # Insert batch
                result = supabase.table('redfin_listings').insert(batch).execute()
                total_inserted += len(batch)
                print(f"Inserted batch {i//batch_size + 1}: {len(batch)} records")
            except Exception as e:
                print(f"Error inserting batch {i//batch_size + 1}: {e}")
                # Try inserting one by one to identify problematic records
                for record in batch:
                    try:
                        supabase.table('redfin_listings').insert(record).execute()
                        total_inserted += 1
                    except Exception as single_error:
                        print(f"  Failed to insert: {record.get('address', 'N/A')} - {single_error}")
        
        print(f"\n[SUCCESS] Uploaded {total_inserted} records to Supabase!")
        return True
        
    except Exception as e:
        print(f"Error connecting to Supabase: {e}")
        return False

def main():
    """Main function"""
    print("=" * 60)
    print("Upload Redfin Listings to Supabase")
    print("=" * 60)
    
    # Check Supabase credentials
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("\nError: Supabase credentials not found!")
        print(f"\nSUPABASE_URL: {'Found' if SUPABASE_URL else 'NOT FOUND'}")
        print(f"SUPABASE_KEY: {'Found' if SUPABASE_KEY else 'NOT FOUND'}")
        print("\nPlease make sure your .env file (in redfin_FSBO_backend/.env or root) contains:")
        print("SUPABASE_URL=https://your-project.supabase.co")
        print("SUPABASE_SERVICE_KEY=your-service-role-key")
        print("OR")
        print("SUPABASE_ANON_KEY=your-anon-key")
        return
    
    # Read CSV data
    print(f"\n1. Reading data from {CSV_FILE}...")
    data = read_csv_data()
    
    if not data:
        print("No data found in CSV file!")
        return
    
    print(f"Found {len(data)} records to upload")
    
    # Show sample record
    if data:
        print("\nSample record:")
        sample = data[0]
        for key, value in sample.items():
            print(f"  {key}: {value}")
    
    # Upload to Supabase
    print(f"\n2. Uploading to Supabase...")
    success = upload_to_supabase(data)
    
    if success:
        print("\n" + "=" * 60)
        print("Done!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("Upload failed. Please check the errors above.")
        print("=" * 60)

if __name__ == '__main__':
    main()

