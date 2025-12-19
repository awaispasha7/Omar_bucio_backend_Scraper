import csv
from pathlib import Path

def add_square_feet_to_csv():
    """Add square_feet data from Supabase CSV to original CSV by matching URLs"""
    
    # File paths
    supabase_csv = Path(r"C:\Users\Admin\Desktop\trulia_listings_rows - Copy.csv")
    original_csv = Path("output/Trulia_Data.csv")
    output_csv = Path("output/Trulia_Data.csv")  # Update in place or create new file
    
    # Step 1: Read Supabase CSV and create mapping of URL -> square_feet
    print("Reading Supabase CSV...")
    url_to_square_feet = {}
    
    if not supabase_csv.exists():
        print(f"[ERROR] Supabase CSV not found: {supabase_csv}")
        return
    
    with open(supabase_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            listing_link = row.get('listing_link', '').strip()
            square_feet = row.get('square_feet', '').strip()
            if listing_link and square_feet:
                url_to_square_feet[listing_link] = square_feet
    
    print(f"Found {len(url_to_square_feet)} listings with square_feet data")
    
    # Step 2: Read original CSV and add square_feet column
    print(f"\nReading original CSV: {original_csv}")
    rows = []
    headers = None
    
    if not original_csv.exists():
        print(f"[ERROR] Original CSV not found: {original_csv}")
        return
    
    with open(original_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames)
        
        # Add Square Feet column if it doesn't exist
        if 'Square Feet' not in headers:
            headers.append('Square Feet')
        
        for row in reader:
            url = row.get('Url', '').strip()
            # Match and add square_feet
            if url in url_to_square_feet:
                row['Square Feet'] = url_to_square_feet[url]
                address = row.get('Address', 'N/A')[:50] if row.get('Address') else 'N/A'
                print(f"[MATCH] {address}... -> {url_to_square_feet[url]} sqft")
            else:
                row['Square Feet'] = ''  # Empty if no match
            rows.append(row)
    
    # Step 3: Write updated CSV
    print(f"\nWriting updated CSV to: {output_csv}")
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    
    # Summary
    matched_count = sum(1 for row in rows if row.get('Square Feet', '').strip())
    print(f"\nSummary:")
    print(f"  Total rows processed: {len(rows)}")
    print(f"  Rows with square_feet added: {matched_count}")
    print(f"  Rows without match: {len(rows) - matched_count}")
    print(f"\n[OK] CSV updated successfully!")

if __name__ == "__main__":
    print("=" * 60)
    print("Add Square Feet to CSV")
    print("=" * 60)
    add_square_feet_to_csv()

