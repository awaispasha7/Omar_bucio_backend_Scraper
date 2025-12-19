"""
Script to merge square feet data from redfin_all_listings CSV
into redfin_listings_rows.csv by matching URLs.
"""
import csv
from pathlib import Path

# File paths
SOURCE_CSV = Path('redfin_all_listings_1766059091400.csv')
TARGET_CSV = Path('outputs/redfin_listings_rows.csv')

def read_square_feet_data(source_file):
    """Read square feet data from source CSV, keyed by listing_link"""
    sqft_data = {}
    
    with open(source_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            listing_link = row.get('listing_link', '').strip()
            square_feet = row.get('square_feet', '').strip()
            
            if listing_link and square_feet:
                # Normalize URL (remove trailing slashes, etc.)
                listing_link = listing_link.rstrip('/')
                sqft_data[listing_link] = square_feet
                print(f"Found: {listing_link} -> {square_feet} sqft")
    
    return sqft_data

def update_target_csv(target_file, sqft_data):
    """Update target CSV with square feet data by matching URLs"""
    rows = []
    fieldnames = []
    updated_count = 0
    
    # Read existing CSV
    with open(target_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            url = row.get('Url', '').strip()
            
            # Normalize URL for matching
            url_normalized = url.rstrip('/')
            
            # Check if we have square feet data for this URL
            if url_normalized in sqft_data:
                row['Square Feet'] = sqft_data[url_normalized]
                updated_count += 1
                print(f"Updated {row.get('Name', 'N/A')}: {sqft_data[url_normalized]} sqft")
            elif url and url_normalized not in sqft_data:
                # Keep existing value (empty string)
                if 'Square Feet' not in row:
                    row['Square Feet'] = ''
            
            rows.append(row)
    
    # Write updated CSV
    with open(target_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n[SUCCESS] Updated {updated_count} listings with square feet data")
    return updated_count

def main():
    """Main function"""
    print("=" * 60)
    print("Square Feet Data Merger")
    print("=" * 60)
    
    # Check if files exist
    if not SOURCE_CSV.exists():
        print(f"Error: Source file not found: {SOURCE_CSV}")
        return
    
    if not TARGET_CSV.exists():
        print(f"Error: Target file not found: {TARGET_CSV}")
        return
    
    # Read square feet data from source
    print(f"\n1. Reading square feet data from {SOURCE_CSV}...")
    sqft_data = read_square_feet_data(SOURCE_CSV)
    print(f"Found {len(sqft_data)} listings with square feet data")
    
    # Update target CSV
    print(f"\n2. Updating {TARGET_CSV}...")
    updated_count = update_target_csv(TARGET_CSV, sqft_data)
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)

if __name__ == '__main__':
    main()

