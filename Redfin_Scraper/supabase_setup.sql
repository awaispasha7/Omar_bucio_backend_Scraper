-- Create redfin_FSBO_listings table
CREATE TABLE redfin_FSBO_listings (
  id BIGSERIAL PRIMARY KEY,
  detail_url TEXT UNIQUE NOT NULL,
  address TEXT,
  bedrooms TEXT,
  bathrooms TEXT,
  price TEXT,
  home_type TEXT,
  year_build TEXT,
  hoa TEXT,
  days_on_redfin TEXT,
  page_view_count TEXT,
  favorite_count TEXT,
  phone_number TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for faster searches
CREATE INDEX idx_redfin_FSBO_listings_address ON redfin_FSBO_listings(address);
CREATE INDEX idx_redfin_FSBO_listings_created_at ON redfin_FSBO_listings(created_at DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE redfin_FSBO_listings ENABLE ROW LEVEL SECURITY;

-- Create policy to allow public read access
CREATE POLICY "Allow public read access" ON redfin_FSBO_listings
  FOR SELECT
  USING (true);

-- Create policy to allow service role to insert/update
CREATE POLICY "Allow service role full access" ON redfin_FSBO_listings
  FOR ALL
  USING (auth.role() = 'service_role');
