-- Create hotpads_listings table
CREATE TABLE hotpads_listings (
  id BIGSERIAL PRIMARY KEY,
  name TEXT,
  contact_name TEXT,
  listing_time TEXT,
  beds_baths TEXT,
  phone_number TEXT,
  address TEXT,
  url TEXT UNIQUE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for faster searches
CREATE INDEX idx_hotpads_listings_address ON hotpads_listings(address);
CREATE INDEX idx_hotpads_listings_created_at ON hotpads_listings(created_at DESC);
CREATE INDEX idx_hotpads_listings_url ON hotpads_listings(url);

-- Enable Row Level Security (RLS)
ALTER TABLE hotpads_listings ENABLE ROW LEVEL SECURITY;

-- Create policy to allow public read access
CREATE POLICY "Allow public read access" ON hotpads_listings
  FOR SELECT
  USING (true);

-- Create policy to allow service role to insert/update
CREATE POLICY "Allow service role full access" ON hotpads_listings
  FOR ALL
  USING (auth.role() = 'service_role');
