-- 1. Clear all existing data to remove duplicates and old bad data
TRUNCATE TABLE hotpads_listings;

-- 2. Add missing columns if they don't exist
ALTER TABLE hotpads_listings 
ADD COLUMN IF NOT EXISTS price TEXT,
ADD COLUMN IF NOT EXISTS image_url TEXT,
ADD COLUMN IF NOT EXISTS bedrooms TEXT,
ADD COLUMN IF NOT EXISTS bathrooms TEXT,
ADD COLUMN IF NOT EXISTS sqft TEXT;

-- 3. Verify the table is empty and ready
SELECT count(*) as listing_count FROM hotpads_listings;
