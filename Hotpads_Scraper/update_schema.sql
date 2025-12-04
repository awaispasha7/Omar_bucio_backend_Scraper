-- Add price and image_url columns to hotpads_listings table
ALTER TABLE hotpads_listings 
ADD COLUMN IF NOT EXISTS price TEXT,
ADD COLUMN IF NOT EXISTS image_url TEXT;
