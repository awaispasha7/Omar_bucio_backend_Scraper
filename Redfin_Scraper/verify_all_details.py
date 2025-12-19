import csv
import re

# File paths
reference_file = "redfin_listings_rows.csv"
current_file = "outputs/redfin_18_Dec_2025_06_41_42.csv"

# Read reference file
reference_data = {}
with open(reference_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if 'listing_link' in row and row['listing_link']:
            url = row['listing_link'].strip()
            reference_data[url] = {
                'address': row.get('address', '').strip(),
                'owner_name': row.get('owner_name', '').strip(),
                'emails': row.get('emails', '').strip(),
                'phones': row.get('phones', '').strip(),
                'mailing_address': row.get('mailing_address', '').strip(),
            }

# Read current file
current_data = {}
with open(current_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        url = row.get('Url', '').strip()
        if url:
            current_data[url] = {
                'address': row.get('Address', '').strip(),
                'owner_name': row.get('Owner Name', '').strip(),
                'emails': row.get('Email', '').strip(),
                'phones': row.get('Phone Number', '').strip(),
                'mailing_address': row.get('Mailing Address', '').strip(),
            }

print("=" * 80)
print("VERIFICATION REPORT - Checking all listings from reference file")
print("=" * 80)
print(f"\nTotal listings in reference: {len(reference_data)}")
print(f"Total listings in current: {len(current_data)}")

# Check each reference listing
all_present = True
missing_details = []

for url, ref_data in reference_data.items():
    print(f"\n{'='*80}")
    print(f"Checking: {ref_data['address']}")
    print(f"URL: {url}")
    
    if url in current_data:
        curr = current_data[url]
        print("[FOUND] Listing is in current file")
        
        # Check owner name
        if ref_data['owner_name']:
            if curr['owner_name'] == ref_data['owner_name']:
                print(f"  [OK] Owner Name: {curr['owner_name']}")
            else:
                print(f"  [MISMATCH] Owner Name - Reference: {ref_data['owner_name']}, Current: {curr['owner_name']}")
                all_present = False
        
        # Check emails
        ref_emails = set(re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', ref_data['emails']))
        curr_emails = set(re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', curr['emails']))
        if ref_emails:
            if ref_emails.issubset(curr_emails) or curr_emails == ref_emails:
                print(f"  [OK] Emails: {len(curr_emails)} email(s) found")
            else:
                missing_emails = ref_emails - curr_emails
                if missing_emails:
                    print(f"  [MISSING] Emails not found: {missing_emails}")
                    all_present = False
                else:
                    print(f"  [OK] Emails: {len(curr_emails)} email(s)")
        
        # Check phones
        ref_phones = set(re.findall(r'\d{10,}', ref_data['phones'].replace(' ', '').replace('-', '')))
        curr_phones = set(re.findall(r'\d{10,}', curr['phones'].replace(' ', '').replace('-', '')))
        if ref_phones:
            if ref_phones.issubset(curr_phones) or curr_phones == ref_phones:
                print(f"  [OK] Phones: {len(curr_phones)} phone(s) found")
            else:
                missing_phones = ref_phones - curr_phones
                if missing_phones:
                    print(f"  [MISSING] Phones not found: {missing_phones}")
                    all_present = False
                else:
                    print(f"  [OK] Phones: {len(curr_phones)} phone(s)")
        
        # Check mailing address
        if ref_data['mailing_address']:
            if curr['mailing_address'] == ref_data['mailing_address']:
                print(f"  [OK] Mailing Address: {curr['mailing_address']}")
            else:
                print(f"  [MISMATCH] Mailing Address - Reference: {ref_data['mailing_address']}, Current: {curr['mailing_address']}")
                all_present = False
    else:
        print("[NOT FOUND] Listing is missing from current file!")
        all_present = False
        missing_details.append(ref_data['address'])

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
if all_present and len(reference_data) == len([u for u in reference_data.keys() if u in current_data]):
    print("[SUCCESS] All listings from reference file are present with complete details!")
else:
    print("[ISSUES FOUND] Some listings or details are missing")
    if missing_details:
        print(f"\nMissing listings: {len(missing_details)}")
        for addr in missing_details:
            print(f"  - {addr}")

print("=" * 80)


