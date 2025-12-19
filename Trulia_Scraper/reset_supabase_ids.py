"""
Script to reset the ID sequence in Supabase trulia_listings table to start from 1.
This will delete all existing records and reset the sequence.
"""
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

def reset_sequence():
    """Reset the ID sequence to start from 1"""
    print("Connecting to Supabase...")
    supabase: Client = create_client(url, key)
    print("[OK] Connected to Supabase")
    
    # Get current count
    try:
        count_response = supabase.table("trulia_listings").select("id", count="exact").execute()
        current_count = count_response.count
        print(f"Current records in table: {current_count}")
    except Exception as e:
        print(f"[ERROR] Could not get count: {e}")
        return
    
    if current_count == 0:
        print("[INFO] Table is already empty. Resetting sequence...")
    else:
        print(f"\n[WARNING] This will DELETE all {current_count} existing records!")
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Operation cancelled.")
            return
        
        # Delete all records
        print("\nDeleting all records...")
        try:
            # Get all IDs first
            all_records = supabase.table("trulia_listings").select("id").execute()
            if all_records.data:
                # Delete in batches
                ids_to_delete = [str(record['id']) for record in all_records.data]
                for record_id in ids_to_delete:
                    supabase.table("trulia_listings").delete().eq("id", record_id).execute()
            print("[OK] All records deleted")
        except Exception as e:
            print(f"[ERROR] Failed to delete records: {e}")
            return
    
    # Reset sequence using SQL
    print("\nResetting ID sequence to start from 1...")
    try:
        # Use RPC call or direct SQL execution
        # Note: Supabase Python client doesn't directly support ALTER SEQUENCE
        # So we'll use a workaround by inserting and deleting a dummy record
        # Or we can use the SQL editor in Supabase dashboard
        
        print("[INFO] To reset the sequence, please run this SQL in Supabase SQL Editor:")
        print("=" * 60)
        print("ALTER SEQUENCE trulia_listings_id_seq RESTART WITH 1;")
        print("=" * 60)
        print("\nOr use the reset_sequence.sql file provided.")
        
        # Alternative: Try to reset by checking current max and setting sequence
        # This requires the sequence to exist and be accessible
        result = supabase.rpc('exec_sql', {
            'sql': 'ALTER SEQUENCE trulia_listings_id_seq RESTART WITH 1;'
        }).execute()
        print("[OK] Sequence reset successfully")
        
    except Exception as e:
        # If RPC doesn't work, provide manual instructions
        print(f"[INFO] Automatic sequence reset not available: {e}")
        print("\nPlease run this SQL command in Supabase SQL Editor:")
        print("ALTER SEQUENCE trulia_listings_id_seq RESTART WITH 1;")
        print("\nOr use the reset_sequence.sql file provided.")
    
    print("\n[OK] Process completed!")
    print("You can now re-upload your CSV data and IDs will start from 1.")

if __name__ == "__main__":
    print("=" * 60)
    print("Supabase ID Sequence Reset Tool")
    print("=" * 60)
    reset_sequence()

