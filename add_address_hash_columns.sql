-- Add address_hash to ALL listings tables and set up Foreign Keys for joining with enrichment tables

-- 1. FSBO (listings)
ALTER TABLE listings ADD COLUMN IF NOT EXISTS address_hash TEXT;
CREATE INDEX IF NOT EXISTS idx_listings_address_hash ON listings(address_hash);
ALTER TABLE listings 
    ADD CONSTRAINT fk_listings_property_owners 
    FOREIGN KEY (address_hash) 
    REFERENCES property_owners(address_hash) 
    ON DELETE SET NULL;

-- 2. Hotpads
ALTER TABLE hotpads_listings ADD COLUMN IF NOT EXISTS address_hash TEXT;
CREATE INDEX IF NOT EXISTS idx_hotpads_address_hash ON hotpads_listings(address_hash);
ALTER TABLE hotpads_listings 
    ADD CONSTRAINT fk_hotpads_property_owners 
    FOREIGN KEY (address_hash) 
    REFERENCES property_owners(address_hash) 
    ON DELETE SET NULL;

-- 3. Redfin
ALTER TABLE redfin_listings ADD COLUMN IF NOT EXISTS address_hash TEXT;
CREATE INDEX IF NOT EXISTS idx_redfin_address_hash ON redfin_listings(address_hash);
ALTER TABLE redfin_listings 
    ADD CONSTRAINT fk_redfin_property_owners 
    FOREIGN KEY (address_hash) 
    REFERENCES property_owners(address_hash) 
    ON DELETE SET NULL;

-- 4. Trulia
ALTER TABLE trulia_listings ADD COLUMN IF NOT EXISTS address_hash TEXT;
CREATE INDEX IF NOT EXISTS idx_trulia_address_hash ON trulia_listings(address_hash);
ALTER TABLE trulia_listings 
    ADD CONSTRAINT fk_trulia_property_owners 
    FOREIGN KEY (address_hash) 
    REFERENCES property_owners(address_hash) 
    ON DELETE SET NULL;

-- 5. Zillow FSBO
ALTER TABLE zillow_fsbo_listings ADD COLUMN IF NOT EXISTS address_hash TEXT;
CREATE INDEX IF NOT EXISTS idx_zillow_fsbo_address_hash ON zillow_fsbo_listings(address_hash);
ALTER TABLE zillow_fsbo_listings 
    ADD CONSTRAINT fk_zillow_fsbo_property_owners 
    FOREIGN KEY (address_hash) 
    REFERENCES property_owners(address_hash) 
    ON DELETE SET NULL;

-- 6. Zillow FRBO
ALTER TABLE zillow_frbo_listings ADD COLUMN IF NOT EXISTS address_hash TEXT;
CREATE INDEX IF NOT EXISTS idx_zillow_frbo_address_hash ON zillow_frbo_listings(address_hash);
ALTER TABLE zillow_frbo_listings 
    ADD CONSTRAINT fk_zillow_frbo_property_owners 
    FOREIGN KEY (address_hash) 
    REFERENCES property_owners(address_hash) 
    ON DELETE SET NULL;

-- 7. Apartments
ALTER TABLE apartments_frbo_chicago ADD COLUMN IF NOT EXISTS address_hash TEXT;
CREATE INDEX IF NOT EXISTS idx_apartments_address_hash ON apartments_frbo_chicago(address_hash);
ALTER TABLE apartments_frbo_chicago 
    ADD CONSTRAINT fk_apartments_property_owners 
    FOREIGN KEY (address_hash) 
    REFERENCES property_owners(address_hash) 
    ON DELETE SET NULL;

-- 8. Add Foreign Keys for Enrichment State too
ALTER TABLE listings ADD CONSTRAINT fk_listings_enrichment_state FOREIGN KEY (address_hash) REFERENCES property_owner_enrichment_state(address_hash);
ALTER TABLE hotpads_listings ADD CONSTRAINT fk_hotpads_enrichment_state FOREIGN KEY (address_hash) REFERENCES property_owner_enrichment_state(address_hash);
ALTER TABLE redfin_listings ADD CONSTRAINT fk_redfin_enrichment_state FOREIGN KEY (address_hash) REFERENCES property_owner_enrichment_state(address_hash);
ALTER TABLE trulia_listings ADD CONSTRAINT fk_trulia_enrichment_state FOREIGN KEY (address_hash) REFERENCES property_owner_enrichment_state(address_hash);
ALTER TABLE zillow_fsbo_listings ADD CONSTRAINT fk_zillow_fsbo_enrichment_state FOREIGN KEY (address_hash) REFERENCES property_owner_enrichment_state(address_hash);
ALTER TABLE zillow_frbo_listings ADD CONSTRAINT fk_zillow_frbo_enrichment_state FOREIGN KEY (address_hash) REFERENCES property_owner_enrichment_state(address_hash);
ALTER TABLE apartments_frbo_chicago ADD CONSTRAINT fk_apartments_enrichment_state FOREIGN KEY (address_hash) REFERENCES property_owner_enrichment_state(address_hash);
