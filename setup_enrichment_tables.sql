-- Create Enrichment State Table
CREATE TABLE IF NOT EXISTS property_owner_enrichment_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    address_hash TEXT UNIQUE NOT NULL,
    normalized_address TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'never_checked',
    missing_fields JSONB DEFAULT '{"owner_name": true, "owner_email": true, "owner_phone": true}'::jsonb,
    locked BOOLEAN DEFAULT FALSE,
    checked_at TIMESTAMPTZ,
    source_used TEXT,
    failure_reason TEXT,
    batchdata_request_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create Unified Property Owners Table
CREATE TABLE IF NOT EXISTS property_owners (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    address_hash TEXT UNIQUE NOT NULL,
    owner_name TEXT,
    owner_email TEXT,
    owner_phone TEXT,
    mailing_address TEXT,
    source TEXT,
    confidence FLOAT,
    raw_response JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Function to handle updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_enrichment_state_modtime
    BEFORE UPDATE ON property_owner_enrichment_state
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_property_owners_modtime
    BEFORE UPDATE ON property_owners
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
