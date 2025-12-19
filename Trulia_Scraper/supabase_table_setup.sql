-- SQL Query to create trulia_FRBO_listings table in Supabase
-- Copy and paste this into Supabase SQL Editor

CREATE TABLE IF NOT EXISTS trulia_FRBO_listings (
    id BIGSERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    zpid TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zipcode TEXT,
    asking_price TEXT,
    beds_baths TEXT,
    year_built INTEGER,
    name TEXT,
    phone_number TEXT,
    agent_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on ZPID for faster lookups
CREATE INDEX IF NOT EXISTS idx_trulia_zpid ON trulia_FRBO_listings(zpid);

-- Create index on created_at for sorting by newest
CREATE INDEX IF NOT EXISTS idx_trulia_created_at ON trulia_FRBO_listings(created_at DESC);

-- Optional: Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update updated_at on row changes
CREATE TRIGGER update_trulia_listings_updated_at
    BEFORE UPDATE ON trulia_FRBO_listings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS) - IMPORTANT for security
ALTER TABLE trulia_FRBO_listings ENABLE ROW LEVEL SECURITY;

-- Create policy to allow service_role to do everything (for your scraper)
CREATE POLICY "Enable all access for service role"
    ON trulia_FRBO_listings
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Create policy to allow anon users to read (for your frontend)
CREATE POLICY "Enable read access for anon users"
    ON trulia_FRBO_listings
    FOR SELECT
    TO anon
    USING (true);

-- Grant permissions
GRANT ALL ON trulia_FRBO_listings TO service_role;
GRANT SELECT ON trulia_FRBO_listings TO anon;