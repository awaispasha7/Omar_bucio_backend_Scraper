import csv
import re

# File paths
reference_file = r"c:\Users\Admin\Desktop\redfin_all_listings_1766059091400.csv"
current_file = "outputs/redfin_18_Dec_2025_06_41_42.csv"
output_file = "outputs/redfin_18_Dec_2025_06_41_42.csv"

# Read reference file and create lookup by URL
reference_data = {}
with open(reference_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if 'listing_link' in row and row['listing_link']:
            url = row['listing_link'].strip()
            
            # Extract all emails (handle multi-line and comma-separated)
            emails = row.get('emails', '').strip()
            # Clean emails - remove tabs, split by comma and newline
            email_list = []
            if emails:
                # Split by comma and newline, then clean each
                for email in re.split(r'[,\n]+', emails):
                    email = email.strip().replace('\t', '')
                    if email and '@' in email:
                        email_list.append(email)
            # Join all emails with comma
            all_emails = ', '.join(email_list) if email_list else ''
            
            # Extract all phones (handle multi-line and comma-separated)
            phones = row.get('phones', '').strip()
            # Clean phones - remove tabs, "Landline:", split by comma and newline
            phone_list = []
            if phones:
                # Split by comma and newline, then clean each
                for phone in re.split(r'[,\n]+', phones):
                    phone = phone.strip().replace('\t', '').replace('Landline:', '').strip()
                    # Clean phone number - keep only digits, dashes, parentheses, spaces
                    phone = re.sub(r'[^\d\-\(\)\s]', '', phone).strip()
                    if phone and len(phone) >= 10:  # Valid phone number
                        phone_list.append(phone)
            # Join all phones with comma
            all_phones = ', '.join(phone_list) if phone_list else ''
            
            reference_data[url] = {
                'owner_name': row.get('owner_name', '').strip(),
                'email': all_emails,  # All emails
                'mailing_address': row.get('mailing_address', '').strip(),
                'phone': all_phones,  # All phones
                'address': row.get('address', '').strip(),
                'price': row.get('price', '').strip(),
                'beds': row.get('beds', '').strip(),
                'baths': row.get('baths', '').strip(),
            }

print(f"Loaded {len(reference_data)} listings from reference file")

# Read current file
current_rows = []
current_urls = set()
fieldnames = None

with open(current_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    
    for row in reader:
        url = row.get('Url', '').strip()
        if url:
            current_urls.add(url)
            
            # Update owner details if match found in reference
            if url in reference_data:
                ref = reference_data[url]
                # Update all owner details
                row['Owner Name'] = ref['owner_name'] if ref['owner_name'] else row.get('Owner Name', '')
                row['Email'] = ref['email'] if ref['email'] else row.get('Email', '')
                row['Mailing Address'] = ref['mailing_address'] if ref['mailing_address'] else row.get('Mailing Address', '')
                # Update phone with all phone numbers
                if ref['phone']:
                    row['Phone Number'] = ref['phone']
                print(f"Updated: {row.get('Address', url)} - Owner: {ref['owner_name']}")
            
            current_rows.append(row)

# Add missing listings from reference file
for url, ref_data in reference_data.items():
    if url not in current_urls:
        # Create new row for missing listing
        # Extract address parts
        address = ref_data['address']
        name = address.split(',')[0].strip() if address else ''
        
        # Format price
        price = ref_data['price']
        if price and not price.startswith('$'):
            try:
                price_num = int(price)
                price = f"${price_num:,}"
            except:
                price = f"${price}" if price else ""
        
        # Format beds/baths
        beds = ref_data['beds'] or '—'
        baths = ref_data['baths'] or '—'
        beds_baths = f"{beds} / {baths}"
        
        new_row = {
            'Name': name,
            'Beds / Baths': beds_baths,
            'Phone Number': ref_data['phone'],
            'Asking Price': price,
            'Days On Redfin': '',
            'Address': address,
            'YearBuilt': '',
            'Agent Name': '',
            'Url': url,
            'Owner Name': ref_data['owner_name'],
            'Email': ref_data['email'],
            'Mailing Address': ref_data['mailing_address'],
        }
        current_rows.append(new_row)
        print(f"Added missing listing: {address}")

# Write updated CSV
with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(current_rows)

print(f"\nUpdated file: {output_file}")
print(f"Total listings: {len(current_rows)}")
matched_count = len([r for r in current_rows if r.get('Url', '') in reference_data])
print(f"Updated owner details for {matched_count} matching listings")

