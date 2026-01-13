-- SQL Script to set up automatic cascade delete for enrichment records
-- This creates triggers that automatically delete enrichment records when
-- the last listing with a given address_hash is deleted from any listing table.
--
-- Run this in Supabase SQL Editor (Dashboard > SQL Editor)

-- Function to check if an address_hash exists in any listing table
-- and delete enrichment records if it doesn't
CREATE OR REPLACE FUNCTION cleanup_orphaned_enrichment()
RETURNS TRIGGER AS $$
DECLARE
    hash_exists BOOLEAN := FALSE;
    address_hash_val TEXT;
BEGIN
    -- Get the address_hash from the deleted row
    address_hash_val := OLD.address_hash;
    
    -- Skip if address_hash is NULL
    IF address_hash_val IS NULL THEN
        RETURN OLD;
    END IF;
    
    -- Check if this address_hash exists in ANY listing table
    -- We check all tables to ensure we don't delete enrichment data
    -- if the same address exists in another table
    
    -- Check listings (FSBO)
    SELECT EXISTS(SELECT 1 FROM listings WHERE address_hash = address_hash_val) INTO hash_exists;
    IF hash_exists THEN RETURN OLD; END IF;
    
    -- Check apartments_frbo
    SELECT EXISTS(SELECT 1 FROM apartments_frbo WHERE address_hash = address_hash_val) INTO hash_exists;
    IF hash_exists THEN RETURN OLD; END IF;
    
    -- Check trulia_listings
    SELECT EXISTS(SELECT 1 FROM trulia_listings WHERE address_hash = address_hash_val) INTO hash_exists;
    IF hash_exists THEN RETURN OLD; END IF;
    
    -- Check redfin_listings
    SELECT EXISTS(SELECT 1 FROM redfin_listings WHERE address_hash = address_hash_val) INTO hash_exists;
    IF hash_exists THEN RETURN OLD; END IF;
    
    -- Check zillow_frbo_listings
    SELECT EXISTS(SELECT 1 FROM zillow_frbo_listings WHERE address_hash = address_hash_val) INTO hash_exists;
    IF hash_exists THEN RETURN OLD; END IF;
    
    -- Check zillow_fsbo_listings
    SELECT EXISTS(SELECT 1 FROM zillow_fsbo_listings WHERE address_hash = address_hash_val) INTO hash_exists;
    IF hash_exists THEN RETURN OLD; END IF;
    
    -- Check hotpads_listings
    SELECT EXISTS(SELECT 1 FROM hotpads_listings WHERE address_hash = address_hash_val) INTO hash_exists;
    IF hash_exists THEN RETURN OLD; END IF;
    
    -- Check other_listings
    SELECT EXISTS(SELECT 1 FROM other_listings WHERE address_hash = address_hash_val) INTO hash_exists;
    IF hash_exists THEN RETURN OLD; END IF;
    
    -- If we get here, the address_hash doesn't exist in any listing table
    -- Delete the enrichment record and property_owner record
    DELETE FROM property_owner_enrichment_state WHERE address_hash = address_hash_val;
    DELETE FROM property_owners WHERE address_hash = address_hash_val;
    
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- Create triggers on each listing table
-- These triggers fire AFTER DELETE and clean up orphaned enrichment data

-- Drop existing triggers if they exist (for idempotency)
DROP TRIGGER IF EXISTS cleanup_enrichment_on_listings_delete ON listings;
DROP TRIGGER IF EXISTS cleanup_enrichment_on_apartments_delete ON apartments_frbo;
DROP TRIGGER IF EXISTS cleanup_enrichment_on_trulia_delete ON trulia_listings;
DROP TRIGGER IF EXISTS cleanup_enrichment_on_redfin_delete ON redfin_listings;
DROP TRIGGER IF EXISTS cleanup_enrichment_on_zillow_frbo_delete ON zillow_frbo_listings;
DROP TRIGGER IF EXISTS cleanup_enrichment_on_zillow_fsbo_delete ON zillow_fsbo_listings;
DROP TRIGGER IF EXISTS cleanup_enrichment_on_hotpads_delete ON hotpads_listings;
DROP TRIGGER IF EXISTS cleanup_enrichment_on_other_delete ON other_listings;

-- Create triggers
CREATE TRIGGER cleanup_enrichment_on_listings_delete
    AFTER DELETE ON listings
    FOR EACH ROW
    EXECUTE FUNCTION cleanup_orphaned_enrichment();

CREATE TRIGGER cleanup_enrichment_on_apartments_delete
    AFTER DELETE ON apartments_frbo
    FOR EACH ROW
    EXECUTE FUNCTION cleanup_orphaned_enrichment();

CREATE TRIGGER cleanup_enrichment_on_trulia_delete
    AFTER DELETE ON trulia_listings
    FOR EACH ROW
    EXECUTE FUNCTION cleanup_orphaned_enrichment();

CREATE TRIGGER cleanup_enrichment_on_redfin_delete
    AFTER DELETE ON redfin_listings
    FOR EACH ROW
    EXECUTE FUNCTION cleanup_orphaned_enrichment();

CREATE TRIGGER cleanup_enrichment_on_zillow_frbo_delete
    AFTER DELETE ON zillow_frbo_listings
    FOR EACH ROW
    EXECUTE FUNCTION cleanup_orphaned_enrichment();

CREATE TRIGGER cleanup_enrichment_on_zillow_fsbo_delete
    AFTER DELETE ON zillow_fsbo_listings
    FOR EACH ROW
    EXECUTE FUNCTION cleanup_orphaned_enrichment();

CREATE TRIGGER cleanup_enrichment_on_hotpads_delete
    AFTER DELETE ON hotpads_listings
    FOR EACH ROW
    EXECUTE FUNCTION cleanup_orphaned_enrichment();

CREATE TRIGGER cleanup_enrichment_on_other_delete
    AFTER DELETE ON other_listings
    FOR EACH ROW
    EXECUTE FUNCTION cleanup_orphaned_enrichment();

-- Verify triggers were created
SELECT 
    trigger_name, 
    event_object_table, 
    action_statement,
    action_timing,
    event_manipulation
FROM information_schema.triggers
WHERE trigger_name LIKE 'cleanup_enrichment%'
ORDER BY event_object_table;

