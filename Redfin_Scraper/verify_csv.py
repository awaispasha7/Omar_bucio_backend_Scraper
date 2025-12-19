import csv

# Read the final CSV file
with open('outputs/redfin_18_Dec_2025_06_41_42.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Reference URLs
ref_urls = {
    'https://www.redfin.com/IL/Downers-Grove/4330-Prospect-Ave-60515/home/18028647',
    'https://www.redfin.com/IL/Aurora/3066-Timber-Hill-Ln-60504/home/18065034',
    'https://www.redfin.com/IL/Downers-Grove/6121-Woodward-Ave-60516/home/192576474',
    'https://www.redfin.com/IL/Winfield/0N071-Stanley-St-60190/home/199142747',
    'https://www.redfin.com/IL/Glendale-Heights/1117-Kingston-Ct-60139/home/18141860',
    'https://www.redfin.com/IL/Villa-Park/114-E-Riordan-Rd-60181/home/21733739',
    'https://www.redfin.com/IL/Willowbrook/6536-S-Quincy-St-60527/home/14177222',
    'https://www.redfin.com/IL/Downers-Grove/5400-Walnut-Ave-60515/unit-402/home/18056278',
}

matches = [r for r in rows if r.get('Url', '').strip() in ref_urls]

print(f'Total listings in CSV: {len(rows)}')
print(f'Matching listings with owner details: {len(matches)}')
print('\nMatching listings with complete owner information:')
print('-' * 80)

for r in matches:
    if r.get('Owner Name'):
        print(f"\n{r['Address']}")
        print(f"  Owner: {r['Owner Name']}")
        print(f"  Email: {r.get('Email', 'N/A')}")
        print(f"  Phone: {r.get('Phone Number', 'N/A')}")
        print(f"  Mailing Address: {r.get('Mailing Address', 'N/A')}")


