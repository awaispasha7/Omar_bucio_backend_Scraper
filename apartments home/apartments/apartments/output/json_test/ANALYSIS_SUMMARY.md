# Apartments.com JSON Data Analysis - Final Verdict

## ✅ CONCLUSION: YES - Apartments.com DOES Provide Bulk JSON Data!

### Key Finding
Apartments.com **DOES expose bulk listing data** via **JSON-LD structured data** (Schema.org format), but the current scraper is **not extracting it correctly**.

### What Was Found

1. **JSON-LD Structured Data** ✅
   - Location: `<script type="application/ld+json">` tag
   - Contains: **40 listings per search page** in a structured format
   - Data available for each listing:
     - ✅ URL (100% coverage)
     - ✅ Phone number (80% coverage - 32/40 listings)
     - ✅ Full address (100% coverage)
     - ✅ Price range (100% coverage)
     - ✅ Name/Title (100% coverage)
     - ✅ Description (100% coverage)
     - ✅ Amenities (partial)

2. **What Was NOT Found** ❌
   - `__NEXT_DATA__` (Zillow's pattern) - Apartments.com doesn't use this
   - `window.__INITIAL_STATE__` or similar React/Redux state
   - Other JSON structures with listings

### Current Scraper Problem

The current `_extract_from_json()` method in `apartments_frbo.py`:
- ❌ Only checks for `__NEXT_DATA__` (which doesn't exist on Apartments.com)
- ❌ Uses simple regex that won't match nested JSON-LD structures
- ❌ Doesn't check for `application/ld+json` script tags
- ❌ Always returns empty list, forcing the scraper to visit each detail page

### Performance Impact

**Current Method (visiting each detail page):**
- 1200 listings = 1200 detail page visits
- Each visit = ~20-40 seconds via Zyte API
- Total time: **5-6 hours**

**JSON-LD Method (extract from search pages):**
- 1200 listings = ~30 search pages (40 listings per page)
- Each search page = ~20-40 seconds via Zyte API
- Total time: **~30-60 minutes**
- **Speed improvement: ~10x faster!**

### What Needs to Be Fixed

The scraper needs to be updated to:

1. **Extract JSON-LD data** from `<script type="application/ld+json">` tags
2. **Parse the ItemList structure** at path: `@graph[CollectionPage].mainEntity.itemListElement`
3. **Extract listing data** from each item in the array
4. **Only visit detail pages** for listings that need additional data (like email, full description, etc.)

### Sample JSON-LD Structure

```json
{
  "@graph": [
    {
      "@type": "CollectionPage",
      "mainEntity": {
        "@type": "ItemList",
        "numberOfItems": 40,
        "itemListElement": [
          {
            "@type": "ListItem",
            "position": 1,
            "item": {
              "@type": ["Product", "RealEstateListing"],
              "url": "https://www.apartments.com/...",
              "telephone": "708-797-6733",
              "name": "Lake Meadows Apartments",
              "description": "...",
              "mainEntity": {
                "@type": "ApartmentComplex",
                "address": {
                  "streetAddress": "3233 S King",
                  "addressLocality": "Chicago",
                  "addressRegion": "IL",
                  "postalCode": "60616"
                }
              },
              "offers": {
                "lowPrice": 995,
                "highPrice": 3960
              }
            }
          }
          // ... 39 more listings
        ]
      }
    }
  ]
}
```

### Next Steps

1. Update `_extract_from_json()` method to parse JSON-LD
2. Extract listings from `itemListElement` array
3. Map JSON-LD fields to scraper item fields
4. Only visit detail pages for missing data (email, full description)
5. Test with a few pages to verify it works
6. Run full scrape - should complete in 30-60 minutes instead of 5-6 hours!

---

**Analysis Date:** December 3, 2025  
**Test URL:** https://www.apartments.com/chicago-il/for-rent-by-owner/  
**Listings Found in JSON-LD:** 40 per page  
**Phone Number Coverage:** 80% (32/40 listings)

