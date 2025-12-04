# Hotpads Apartment Scraper

A Scrapy-based web scraper for extracting apartment rental listings from Hotpads for specified locations.

## Features
- Scrapes apartment listings from multiple locations
- Extracts property details: address, beds/baths, contact information
- Captures landlord contact information (names and phone numbers)
- Outputs data to CSV files and Supabase database
- Uses Zyte API for reliable scraping

## Prerequisites
- Python 3.10+
- Zyte API Key (required for scraping)

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/awaispasha7/apartments_Zilow_Hotpads_Scraper.git
   cd apartments_Zilow_Hotpads_Scraper
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**:
   - **Windows**:
     ```bash
     .\venv\Scripts\activate
     ```
   - **Mac/Linux**:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### 1. Set up your Zyte API Key
Create a `.env` file in the project root directory:
```env
ZYTE_API_KEY=your_api_key_here
```

**⚠️ IMPORTANT**: Never commit the `.env` file to version control. It's already included in `.gitignore`.

### 2. Configure locations to scrape
Edit `input/locations.csv` to specify the locations you want to scrape:
```csv
location
chicago il
miami fl
new york ny
```

## Usage

### Option 1: Windows Batch Script
Double-click `runner.bat`

### Option 2: Command Line
```bash
python -m scrapy crawl hotpads_scraper
```

## Output
Results are saved in:
- CSV file: `output/Hotpads_Data.csv`
- Supabase database: `hotpads_listings` table
- Contains: Name, Contact Name, Listing Time, Beds/Baths, Phone Number, Address, URL

## Project Structure
```
Hotpads_Scraper/
├── input/
│   └── locations.csv          # Input locations to scrape
├── output/                    # Generated CSV files
├── hotpads/
│   ├── spiders/
│   │   └── hotpads_scraper.py  # Main spider logic
│   ├── items.py               # Data structure definitions
│   ├── settings.py            # Scrapy settings
│   └── pipelines.py           # Data processing pipelines
├── .env                       # API keys (DO NOT COMMIT)
├── .gitignore                 # Git ignore rules
├── requirements.txt           # Python dependencies
├── runner.bat                 # Windows run script
├── scheduler.py               # Automated scheduling
└── supabase_hotpads_setup.sql # Database setup
```

## Team Collaboration

### For New Team Members
1. Clone the repository
2. Ask the team lead for the Zyte API key
3. Create your `.env` file with the API key
4. Follow the installation steps above

### Before Committing
- Never commit the `.env` file
- Never commit files in the `outputs/` folder
- Test your changes locally before pushing

## Troubleshooting

### `scrapy` command not found
Use the Python module syntax instead:
```bash
python -m scrapy crawl hotpads_scraper
```

### Missing dependencies
Reinstall requirements:
```bash
pip install -r requirements.txt
```

### No data scraped
- Check that your Zyte API key is valid
- Verify the locations in `input/locations.csv` are correct
- Check the Scrapy logs for errors

## License
This project is for educational and research purposes only. Please respect Hotpads' Terms of Service and robots.txt when scraping.
