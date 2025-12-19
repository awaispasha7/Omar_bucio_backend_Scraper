import csv
from pathlib import Path

# File paths
reference_file = "redfin_listings_rows.csv"
current_file = "outputs/redfin_18_Dec_2025_06_41_42.csv"

# Read reference file (redfin_listings_rows.csv)
reference_urls = {}
reference_data = {}

with open(reference_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if 'listing_link' in row and row['listing_link']:
            url = row['listing_link'].strip()
            reference_urls[url] = True
            reference_data[url] = {
                'address': row.get('address', ''),
                'price': row.get('price', ''),
                'owner_name': row.get('owner_name', ''),
                'listing_link': url
            }

# Read current file (redfin_18_Dec_2025_06_41_42.csv)
current_urls = {}
current_data = {}

with open(current_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if 'Url' in row and row['Url']:
            url = row['Url'].strip()
            current_urls[url] = True
            current_data[url] = {
                'address': row.get('Address', ''),
                'price': row.get('Asking Price', ''),
                'owner_name': row.get('Owner Name', ''),
                'url': url
            }

# Find matches
matches = []
for url in reference_urls:
    if url in current_urls:
        matches.append(url)

# Find missing (in reference but not in current)
missing = []
for url in reference_urls:
    if url not in current_urls:
        missing.append(url)

# Find extra (in current but not in reference)
extra = []
for url in current_urls:
    if url not in reference_urls:
        extra.append(url)

# Print results
print("=" * 80)
print("LISTING COMPARISON REPORT")
print("=" * 80)
print(f"\nReference file: {reference_file}")
print(f"Current file: {current_file}")
print(f"\nTotal listings in reference: {len(reference_urls)}")
print(f"Total listings in current: {len(current_urls)}")
print(f"\n[MATCHES FOUND: {len(matches)}]")
print("-" * 80)

if matches:
    for i, url in enumerate(matches, 1):
        ref_data = reference_data[url]
        curr_data = current_data[url]
        print(f"\n{i}. MATCH FOUND:")
        print(f"   Address: {ref_data['address']}")
        print(f"   URL: {url}")
        print(f"   Reference Price: ${ref_data['price']}")
        print(f"   Current Price: {curr_data['price']}")
        print(f"   Reference Owner: {ref_data['owner_name']}")
        print(f"   Current Owner: {curr_data['owner_name']}")
else:
    print("   No matches found!")

print("\n" + "=" * 80)
print(f"[MISSING FROM CURRENT: {len(missing)}]")
print("-" * 80)

if missing:
    for i, url in enumerate(missing, 1):
        ref_data = reference_data[url]
        print(f"\n{i}. MISSING:")
        print(f"   Address: {ref_data['address']}")
        print(f"   URL: {url}")
        print(f"   Price: ${ref_data['price']}")
        print(f"   Owner: {ref_data['owner_name']}")
else:
    print("   All reference listings found in current file!")

print("\n" + "=" * 80)
print(f"[EXTRA IN CURRENT (not in reference): {len(extra)}]")
print("-" * 80)

if extra:
    for i, url in enumerate(extra, 1):
        curr_data = current_data[url]
        print(f"\n{i}. EXTRA:")
        print(f"   Address: {curr_data['address']}")
        print(f"   URL: {url}")
        print(f"   Price: {curr_data['price']}")
else:
    print("   No extra listings!")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
if len(reference_urls) > 0:
    match_percentage = (len(matches) / len(reference_urls)) * 100
    print(f"Matches: {len(matches)}/{len(reference_urls)} ({match_percentage:.1f}%)")
else:
    print(f"Matches: {len(matches)}/0 (N/A)")
print(f"Missing: {len(missing)}")
print(f"Extra: {len(extra)}")
print("=" * 80)

