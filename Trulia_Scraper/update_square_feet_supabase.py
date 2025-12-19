import os
import csv
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

def clean_value(value):
    """Clean CSV values"""
    if not value or value.strip() == '' or value.strip().lower() == 'no data':
        return None
    return value.strip()

def update_square_feet_in_supabase(csv_path):
    """Update square_feet in Supabase from CSV data"""
    
    print("=" * 60)
    print("Update Square Feet in Supabase")
    print("=" * 60)
    
    print("\nConnecting to Supabase...")
    supabase: Client = create_client(url, key)
    print("[OK] Connected to Supabase")
    
    # Read CSV file
    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"[ERROR] CSV file not found: {csv_path}")
        return
    
    print(f"\nReading CSV file: {csv_file}")
    
    updates = []
    no_square_feet = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, start=2):
            listing_link = clean_value(row.get('Url', ''))
            square_feet = clean_value(row.get('Square Feet', ''))
            
            if not listing_link:
                continue
            
            if square_feet:
                updates.append({
                    'listing_link': listing_link,
                    'square_feet': square_feet
                })
            else:
                no_square_feet.append(listing_link)
    
    print(f"\nFound {len(updates)} records with square_feet data")
    print(f"Found {len(no_square_feet)} records without square_feet data")
    
    if not updates:
        print("[WARN] No records with square_feet data to update")
        return
    
    # Update Supabase records
    print(f"\nUpdating {len(updates)} records in Supabase...")
    updated_count = 0
    error_count = 0
    
    for update in updates:
        try:
            # Use upsert to update by listing_link
            response = supabase.table("trulia_listings").update({
                'square_feet': update['square_feet']
            }).eq('listing_link', update['listing_link']).execute()
            
            updated_count += 1
            address = update.get('address', 'N/A')
            print(f"[OK] Updated: {update['listing_link'][:60]}... -> {update['square_feet']} sqft")
            
        except Exception as e:
            error_count += 1
            print(f"[ERROR] Failed to update {update['listing_link'][:60]}... - {e}")
    
    # Summary
    print(f"\nUpdate Summary:")
    print(f"  [OK] Successfully updated: {updated_count}")
    print(f"  [ERROR] Failed updates: {error_count}")
    print(f"  [INFO] Records without square_feet: {len(no_square_feet)}")
    
    # Verify
    print("\nVerifying updates...")
    try:
        # Get count of records with square_feet
        count_with_sqft = supabase.table("trulia_listings").select("id", count="exact").not_.is_("square_feet", "null").execute()
        print(f"  Records in Supabase with square_feet: {count_with_sqft.count}")
    except Exception as e:
        print(f"  [WARN] Could not verify: {e}")
    
    print("\n[OK] Update process completed!")

if __name__ == "__main__":
    csv_path = "output/Trulia_Data.csv"
    update_square_feet_in_supabase(csv_path)

