-- Create hotpads_listings table
CREATE TABLE hotpads_listings (
  id BIGSERIAL PRIMARY KEY,
  
  -- Property Information
  property_name TEXT,
  property_type TEXT,
  price TEXT,
  bedrooms TEXT,
  bathrooms TEXT,
  square_feet TEXT,
  address TEXT,
  city TEXT,
  state TEXT,
  zip_code TEXT,
  
  -- Listing Details
  description TEXT,
  amenities TEXT,
  pet_policy TEXT,
  parking TEXT,
  available_date TEXT,
  lease_term TEXT,
  listing_date TEXT,
  
  -- Contact Information
  contact_name TEXT,
  contact_company TEXT,
  phone_number TEXT,
  email TEXT,
  
  -- Metadata
  url TEXT UNIQUE NOT NULL,
  listing_id TEXT,
  photos TEXT[], -- Array of photo URLs
  
  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for faster searches
CREATE INDEX idx_hotpads_listings_city ON hotpads_listings(city);
CREATE INDEX idx_hotpads_listings_state ON hotpads_listings(state);
CREATE INDEX idx_hotpads_listings_price ON hotpads_listings(price);
CREATE INDEX idx_hotpads_listings_bedrooms ON hotpads_listings(bedrooms);
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
