-- SQL Script to fix Hotpads sequence
-- For GENERATED ALWAYS AS IDENTITY columns, use ALTER TABLE ... RESTART
-- Run this in Supabase SQL Editor

DO $$
DECLARE
    max_id_val INTEGER;
BEGIN
    -- hotpads_listings
    SELECT COALESCE(MAX(id), 0) INTO max_id_val FROM hotpads_listings;
    EXECUTE format('ALTER TABLE hotpads_listings ALTER COLUMN id RESTART WITH %s', max_id_val + 1);
    RAISE NOTICE 'Fixed hotpads_listings sequence to start from %', max_id_val + 1;
END $$;

