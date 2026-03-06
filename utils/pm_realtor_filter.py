"""
Shared PM/realtor filter for all scrapers (Option 1: hide — do not save these listings).
Used by api_server.py and by each scraper's Supabase pipeline so PM/realtor listings
are never saved and never returned.
"""
# Keywords that indicate property management or realtor
PM_REALTOR_KEYWORDS = (
    "property management", "property manager", "property mgmt", "property management company",
    "property management llc", "rental agency", "rental management",
    "realtor", "real estate agent", "real estate broker", "broker",
    "leasing agent", "leasing office", "leasing manager",
    "listing agent", "management company", "mgmt co", "pm company",
    "hotpads support",
)


def is_pm_or_realtor(item_or_row):
    """
    Return True if the listing looks like PM/realtor (should be hidden / not saved).
    Accepts a dict with any of: owner_name, Name, agent_name, Agent Name, Agent_Name,
    description, contact_name, property_name, Owner Name (scrapy items may use different keys).
    """
    if not item_or_row or not isinstance(item_or_row, dict):
        return False
    text_parts = []
    for key in ("owner_name", "Name", "agent_name", "Agent Name", "Agent_Name", "description",
                "contact_name", "property_name", "Owner Name", "Contact Name"):
        val = item_or_row.get(key)
        if val is not None and isinstance(val, str) and val.strip():
            text_parts.append(val.strip())
    combined = " ".join(text_parts).lower()
    if not combined:
        return False
    return any(kw in combined for kw in PM_REALTOR_KEYWORDS)
