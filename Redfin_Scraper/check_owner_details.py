import csv

# File paths
reference_file = "redfin_listings_rows.csv"
current_file = "outputs/redfin_18_Dec_2025_06_41_42.csv"

print("=" * 80)
print("CHECKING OWNER NAME AND MAILING ADDRESS IN FINAL CSV")
print("=" * 80)

# Read reference file to get expected values
reference_data = {}
with open(reference_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if 'listing_link' in row and row['listing_link']:
            url = row['listing_link'].strip()
            reference_data[url] = {
                'address': row.get('address', '').strip(),
                'owner_name': row.get('owner_name', '').strip(),
                'mailing_address': row.get('mailing_address', '').strip(),
            }

# Read current file and check
print(f"\nReading: {current_file}\n")
with open(current_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    
    print(f"Total listings in CSV: {len(rows)}\n")
    print("=" * 80)
    
    # Check each row
    all_have_owner = True
    all_have_mailing = True
    
    for idx, row in enumerate(rows, 1):
        url = row.get('Url', '').strip()
        owner_name = row.get('Owner Name', '').strip()
        mailing_address = row.get('Mailing Address', '').strip()
        address = row.get('Address', '').strip()
        
        print(f"\n[{idx}] {address}")
        print(f"    URL: {url}")
        
        # Check owner name
        if owner_name:
            print(f"    [OK] Owner Name: {owner_name}")
            # If this is a reference listing, verify it matches
            if url in reference_data:
                ref_owner = reference_data[url]['owner_name']
                if owner_name == ref_owner:
                    print(f"         [VERIFIED] Matches reference: {ref_owner}")
                else:
                    print(f"         [WARNING] Reference has: {ref_owner}")
        else:
            print(f"    [MISSING] Owner Name: (empty)")
            all_have_owner = False
        
        # Check mailing address
        if mailing_address:
            print(f"    [OK] Mailing Address: {mailing_address}")
            # If this is a reference listing, verify it matches
            if url in reference_data:
                ref_mailing = reference_data[url]['mailing_address']
                if mailing_address == ref_mailing:
                    print(f"         [VERIFIED] Matches reference: {ref_mailing}")
                else:
                    print(f"         [WARNING] Reference has: {ref_mailing}")
        else:
            print(f"    [MISSING] Mailing Address: (empty)")
            all_have_mailing = False
        
        print("-" * 80)

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

# Count statistics
owner_count = sum(1 for row in rows if row.get('Owner Name', '').strip())
mailing_count = sum(1 for row in rows if row.get('Mailing Address', '').strip())
reference_matches = sum(1 for row in rows if row.get('Url', '').strip() in reference_data)

print(f"Total listings: {len(rows)}")
print(f"Listings with Owner Name: {owner_count}/{len(rows)} ({owner_count*100//len(rows) if len(rows) > 0 else 0}%)")
print(f"Listings with Mailing Address: {mailing_count}/{len(rows)} ({mailing_count*100//len(rows) if len(rows) > 0 else 0}%)")
print(f"Reference listings (from redfin_listings_rows.csv): {reference_matches}")

if owner_count == len(rows) and mailing_count == len(rows):
    print("\n[SUCCESS] All listings have both Owner Name and Mailing Address!")
elif owner_count == len(rows):
    print("\n[PARTIAL] All listings have Owner Name, but some are missing Mailing Address")
elif mailing_count == len(rows):
    print("\n[PARTIAL] All listings have Mailing Address, but some are missing Owner Name")
else:
    print("\n[ISSUES] Some listings are missing Owner Name and/or Mailing Address")

print("=" * 80)


