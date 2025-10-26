# FINDINGS: Citation Matching in Deep Biblio Tools

## Date: 2025-10-26

## What I Found

### The Converter IS Trying to Fetch Metadata

From the output logs, the converter IS attempting to fetch citation metadata:
```
Fetching metadata for 376 citations:
Fetching: Adisorn et al...
Fetching: Agarwal et al...
...
Fetching: Unknown... (appears 124 times)
```

### The LOCAL_BIBTEX_PATH Problem

1. **Environment variable is being set**: `export LOCAL_BIBTEX_PATH=.../dpp-fashion.bib`
2. **Converter reports**: "✗ Local BibTeX not initialized (path: None)"
3. **The file EXISTS**: `context/dpp-fashion.bib` (found in subdirectory)
4. **Wrong path in env var**: Points to root directory, file is in `context/` subdirectory

### The Fallback Logic (From User)

The user explained the expected fallback:
1. Try local Zotero MCP server
2. If not available, try Zotero API
3. If that fails, try to find local .json (NOT references.bib)

### What's Actually Happening

The converter is:
1. NOT using local BibTeX (path: None - env var not picked up)
2. Fetching from SOMEWHERE (showing "Fetching: ..." progress)
3. Falling back to "Unknown" for 124 citations
4. Successfully resolving others (Adisorn, Agarwal, etc.)

### The Critical Error

```
! Text line contains an invalid character.
l.247 ..., \textbackslash citep\{unknownUnknown^^?
```

There's an invalid character (`^^?`) being written to the LaTeX file, causing compilation to fail at page 9.

## The Real Problem

The issue is NOT that fetching isn't happening - it IS fetching. The problems are:

1. **Local BibTeX file not being used** - need to fix path
2. **124 citations failing to fetch** - need to understand why
3. **Invalid character in LaTeX output** - need to clean up citation keys

## Action Items

1. **Fix LOCAL_BIBTEX_PATH**: Point to correct location (`context/dpp-fashion.bib`)
2. **Verify Zotero MCP server**: Is it running? How to connect?
3. **Check citation fetcher logs**: Why are 124 failing?
4. **Fix invalid character bug**: Clean citation key generation

## Files to Investigate

1. How environment variable is read (converter.py)
2. Where "Fetching..." progress comes from
3. How Zotero MCP connection works
4. Citation key sanitization (the `^^?` character)
