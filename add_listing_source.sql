-- Add listing_source column to track where the listing originally came from
ALTER TABLE property_owners ADD COLUMN IF NOT EXISTS listing_source TEXT;
ALTER TABLE property_owner_enrichment_state ADD COLUMN IF NOT EXISTS listing_source TEXT;

-- Update existing records if possible (optional, but good for consistency)
-- For example, if we know some are from Zillow FSBO:
-- UPDATE property_owner_enrichment_state SET listing_source = 'Zillow FSBO' WHERE listing_source IS NULL;
