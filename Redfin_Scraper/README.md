# Zillow FSBO Scraper

A Scrapy-based web scraper for extracting "For Sale By Owner" (FSBO) listings from Zillow for specified locations.

## Features
- Scrapes FSBO listings from multiple locations
- Extracts property details: address, price, bedrooms, bathrooms, home type, etc.
- Captures owner contact information (phone numbers)
- Outputs data to timestamped CSV files
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
miami dade county fl
broward county fl
palm beach county fl
```

## Usage

### Option 1: Windows Batch Script
Double-click `runner.bat`

### Option 2: Command Line
```bash
python -m scrapy crawl zillow_spider
```

## Output
Results are saved in the `outputs/` folder as CSV files with timestamps:
- Format: `zillow_DD_MMM_YYYY_HH_MM_SS.csv`
- Contains: Detail URL, Address, Bedrooms, Bathrooms, Price, Home Type, Year Built, HOA, Days on Zillow, Page Views, Favorites, Phone Number

## Project Structure
```
zillow_scraper/
├── input/
│   └── locations.csv          # Input locations to scrape
├── outputs/                   # Generated CSV files
├── zillow_scraper/
│   ├── spiders/
│   │   └── zillow_spider.py  # Main spider logic
│   ├── items.py              # Data structure definitions
│   ├── settings.py           # Scrapy settings
│   └── pipelines.py          # Data processing pipelines
├── .env                      # API keys (DO NOT COMMIT)
├── .gitignore               # Git ignore rules
├── requirements.txt         # Python dependencies
├── runner.bat              # Windows run script
└── Documentation.txt       # Detailed setup guide
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
python -m scrapy crawl zillow_spider
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
This project is for educational and research purposes only. Please respect Zillow's Terms of Service and robots.txt when scraping.
