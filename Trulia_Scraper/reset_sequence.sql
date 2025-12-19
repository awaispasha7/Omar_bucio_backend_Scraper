-- Reset the sequence for trulia_listings table to start from 1
-- Run this in Supabase SQL Editor

-- Step 1: Delete all existing records
DELETE FROM trulia_listings;

-- Step 2: Reset the sequence to start from 1
ALTER SEQUENCE trulia_listings_id_seq RESTART WITH 1;

-- After running these commands, re-run upload_csv_to_supabase.py
-- The new records will have IDs starting from 1

