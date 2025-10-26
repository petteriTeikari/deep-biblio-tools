# Recovery Plan: Using Zotero Translation Server

## Current Situation

- Added 28 citations to Zotero
- **10 are garbage** "Added from URL" entries (you see 10, I reported 9 - need to verify)
- Need to clean up and re-add properly using Zotero's translator infrastructure

## The Correct Approach (from OpenAI)

Use **Zotero's translation-server** - this is what the Zotero Connector uses internally. It provides:
- `/web` endpoint: Converts URL → full Zotero JSON with metadata
- `/search` endpoint: Searches for items by identifier
- Proper metadata extraction (titles, authors, dates, publishers)

## Recovery Steps (Conservative)

### Step 1: Manual Cleanup (FASTEST - Recommended)

**Time: 3 minutes**

1. In Zotero, search for: `Added`
2. Select all 10 entries starting with "Added from URL"
3. Right-click → **Delete from Library**

### Step 2: Re-add Using Zotero's Built-in Tool

**Time: 2 minutes**

1. In Zotero: **File → Add Item by Identifier** (Cmd/Ctrl+Shift+A)
2. Paste these 10 URLs (one per line):

```
https://cris.vtt.fi/en/publications/implementing-the-digital-product-passport-a-guidebook-for-busines
https://www.voguebusiness.com/story/technology/how-to-make-digital-product-passports-cool
https://corporate.zalando.com/en/walking-talk
https://dustmagazine.com/comply-or-die-the-future-of-fashion-and-the-industrys-potential-mass-extinction/
https://www.europarl.europa.eu/thinktank/en/document/EPRS_STU(2024)757808
https://urn.fi/URN:NBN:fi:aalto-202506295310
https://www.amazon.de/-/en/Craft-Use-Post-Growth-Kate-Fletcher/dp/1138021016
https://www.sciencedirect.com/science/article/abs/pii/S1084804523000917
https://content.ellenmacarthurfoundation.org/m/54c053dd73f80168/original/France-s-Anti-waste-and-Circular-Economy-Law.pdf
https://www.ellenmacarthurfoundation.org/our-vision-of-a-circular-economy-for-fashion
```

3. Click OK
4. Zotero will fetch proper metadata

### Step 3: Export Updated Collection

1. Right-click 'dpp-fashion' collection
2. **Export Collection → CSL JSON**
3. Save to: `/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/mcp-draft-refined-v3.json`

**Total time: 5 minutes**

## Future: Translation Server Integration (Optional)

### Setup Translation Server

```bash
# Run locally via Docker
docker pull zotero/translation-server
docker run -d -p 1969:1969 --rm --name translation-server zotero/translation-server
```

### Test Translation

```bash
# Test with a URL
curl -d "https://arxiv.org/abs/2509.24272" \
  -H "Content-Type: text/plain" \
  http://localhost:1969/web
```

This returns proper Zotero JSON with full metadata.

### Integration Script (Future)

Once translation-server is running, we can use it for automated additions:

1. Call `/web` endpoint with URL
2. Get back full Zotero JSON
3. POST that JSON to Zotero API
4. No more garbage entries

**Reference**: https://github.com/zotero/translation-server

## Safeguards to Implement

### 1. Dry-Run By Default

```python
def add_citations_to_zotero(
    ...,
    dry_run: bool = True,  # Default to safe mode
    allow_write: bool = False
):
    if not allow_write or dry_run:
        print("DRY RUN - would add:", metadata)
        return
```

### 2. Metadata Quality Check

```python
def validate_metadata(item):
    """Ensure item has minimum required fields."""
    required = ["title", "creators", "itemType"]
    missing = [f for f in required if not item.get(f)]
    if missing:
        raise ValueError(f"Incomplete metadata: missing {missing}")
    if item["title"].startswith("Added from"):
        raise ValueError("Garbage title detected")
```

### 3. Confirmation Prompt

```python
def preview_and_confirm(items):
    """Show what will be added, require confirmation."""
    for item in items:
        print(f"  [{item['itemType']}] {item['title']}")
        print(f"    by: {', '.join(c['lastName'] for c in item.get('creators', []))}")

    if len(items) > 5:
        response = input(f"Add {len(items)} items? [y/N] ")
        return response.lower() == 'y'
    return True
```

### 4. Tagging for Reversibility

```python
metadata["tags"] = [
    {"tag": "auto_added"},
    {"tag": f"added_{datetime.now().date()}"},
    {"tag": "mcp_conversion"}
]
```

## Decision Point

**Do you want me to:**

**A. Help you with manual cleanup now** (5 min, guaranteed safe)
- I'll guide you step-by-step
- Uses Zotero's proven tools
- No risk of more garbage

**B. Create automated cleanup scripts** (30 min to write + test)
- List suspects (dry-run)
- Delete confirmed keys
- Would test on sandbox first

**C. Set up translation-server integration** (1 hour)
- Docker setup
- Integration script
- Proper metadata fetching
- For future use

**My recommendation: A (manual cleanup now)**, then C (translation-server) once things are stable.

## What I've Learned

1. **Never construct metadata manually** - use Zotero's translators
2. **Always dry-run first** - preview before writing
3. **Test on 1 item** - before processing 28
4. **Manual is often faster** - than broken automation
5. **Respect user's tools** - Zotero's UI works perfectly

## References

- [Zotero Translation Server](https://github.com/zotero/translation-server)
- [Zotero Web API](https://www.zotero.org/support/dev/web_api/v3/basics)
- [Translation Server Endpoints](https://github.com/zotero/translation-server#usage)
