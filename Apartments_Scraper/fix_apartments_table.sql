-- Migration script to add address_hash column to apartments_frbo table
-- Run this in Supabase SQL Editor (Dashboard > SQL Editor)

-- Add address_hash column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'apartments_frbo' 
        AND column_name = 'address_hash'
    ) THEN
        ALTER TABLE apartments_frbo ADD COLUMN address_hash TEXT;
        RAISE NOTICE 'Added address_hash column to apartments_frbo table';
    ELSE
        RAISE NOTICE 'address_hash column already exists in apartments_frbo table';
    END IF;
END $$;

-- Create index on address_hash for faster lookups
CREATE INDEX IF NOT EXISTS idx_apartments_address_hash ON apartments_frbo(address_hash);

-- Generate address_hash for existing records that don't have one
UPDATE apartments_frbo
SET address_hash = md5(LOWER(TRIM(COALESCE(full_address, ''))))
WHERE address_hash IS NULL AND full_address IS NOT NULL AND full_address != '';

-- Verify the changes
SELECT 
    COUNT(*) as total_records,
    COUNT(address_hash) as records_with_hash,
    COUNT(*) - COUNT(address_hash) as records_without_hash
FROM apartments_frbo;
