"""
Script to delete all records, reset sequence to 1, and re-upload CSV data
"""
import csv
import os
import re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
project_root = Path(__file__).resolve().parent
env_paths = [
    project_root / '.env',
    project_root / 'redfin_FSBO_backend' / '.env',
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        break
else:
    load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY', '') or os.getenv('SUPABASE_ANON_KEY', '') or os.getenv('SUPABASE_KEY', '')

CSV_FILE = Path('outputs/redfin_listings_rows.csv')

def extract_beds_baths(beds_baths_str):
    """Extract beds and baths from 'Beds / Baths' format"""
    beds = ""
    baths = ""
    
    if beds_baths_str:
        match = re.search(r'(\d+)\s*/\s*(\d+\.?\d*)', beds_baths_str)
        if match:
            beds = match.group(1)
            baths = match.group(2)
    
    return beds, baths

def clean_price(price_str):
    """Clean price string, remove $ and commas"""
    if not price_str:
        return ""
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
            beds, baths = extract_beds_baths(row.get('Beds / Baths', ''))
            
            record = {
                'address': row.get('Address', '').strip() or None,
                'price': clean_price(row.get('Asking Price', '')) or None,
                'beds': beds or None,
                'baths': baths or None,
                'square_feet': row.get('Square Feet', '').strip() or None,
                'listing_link': row.get('Url', '').strip() or None,
                'property_type': None,
                'county': None,
                'lot_acres': None,
                'owner_name': row.get('Owner Name', '').strip() or None,
                'mailing_address': row.get('Mailing Address', '').strip() or None,
                'scrape_date': datetime.now().strftime('%Y-%m-%d'),
                'emails': row.get('Email', '').strip() or None,
                'phones': row.get('Phone Number', '').strip() or None,
            }
            
            if record['address'] or record['listing_link']:
                data.append(record)
    
    return data

def delete_all_records(supabase: Client):
    """Delete all records from the table"""
    try:
        print("Deleting all existing records...")
        # Get all IDs first
        result = supabase.table('redfin_listings').select('id').execute()
        
        if result.data:
            ids = [row['id'] for row in result.data]
            print(f"Found {len(ids)} records to delete")
            
            # Delete in batches
            batch_size = 100
            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i:i + batch_size]
                supabase.table('redfin_listings').delete().in_('id', batch_ids).execute()
                print(f"Deleted batch {i//batch_size + 1}: {len(batch_ids)} records")
            
            print("All records deleted successfully!")
        else:
            print("No records to delete")
        
        return True
    except Exception as e:
        print(f"Error deleting records: {e}")
        return False

def reset_sequence(supabase: Client):
    """Reset the sequence to start from 1 using RPC"""
    try:
        print("\nResetting ID sequence to start from 1...")
        # Use Supabase RPC to execute SQL
        # Note: This requires a function in Supabase, or we can try direct SQL
        result = supabase.rpc('exec_sql', {
            'sql': 'ALTER SEQUENCE redfin_listings_id_seq RESTART WITH 1;'
        }).execute()
        print("Sequence reset successfully!")
        return True
    except Exception as e:
        # If RPC doesn't work, we'll provide manual instructions
        print(f"Could not reset sequence automatically: {e}")
        print("\nPlease run this SQL in Supabase SQL Editor:")
        print("ALTER SEQUENCE redfin_listings_id_seq RESTART WITH 1;")
        return False

def upload_data(supabase: Client, data):
    """Upload data to Supabase"""
    try:
        print(f"\nUploading {len(data)} records...")
        
        batch_size = 100
        total_inserted = 0
        
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            result = supabase.table('redfin_listings').insert(batch).execute()
            total_inserted += len(batch)
            print(f"Inserted batch {i//batch_size + 1}: {len(batch)} records (IDs: {[r['id'] for r in result.data]})")
        
        print(f"\n[SUCCESS] Uploaded {total_inserted} records!")
        return True
    except Exception as e:
        print(f"Error uploading data: {e}")
        return False

def main():
    """Main function"""
    print("=" * 60)
    print("Re-upload Data Starting from ID 1")
    print("=" * 60)
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("\nError: Supabase credentials not found!")
        return
    
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Step 1: Delete all existing records
        print("\n1. Deleting existing records...")
        if not delete_all_records(supabase):
            print("Failed to delete records. Aborting.")
            return
        
        # Step 2: Reset sequence (try automatic, fallback to manual instructions)
        print("\n2. Resetting sequence...")
        reset_sequence(supabase)
        
        # Step 3: Read CSV data
        print("\n3. Reading CSV data...")
        data = read_csv_data()
        
        if not data:
            print("No data found in CSV file!")
            return
        
        print(f"Found {len(data)} records to upload")
        
        # Step 4: Upload data
        print("\n4. Uploading data...")
        if upload_data(supabase, data):
            print("\n" + "=" * 60)
            print("Done! Data uploaded starting from ID 1")
            print("=" * 60)
        else:
            print("\nUpload failed!")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()

