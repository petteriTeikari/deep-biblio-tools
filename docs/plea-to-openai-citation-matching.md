# Plea to OpenAI: Help Us Understand Citation Matching in Deep Biblio Tools

## The Problem

I (Claude) have completely lost track of how citation matching is supposed to work in this Deep Biblio Tools project, and I keep making incorrect assumptions that waste the user's time. The user is rightfully frustrated because I claimed there were "124 Unknown citations" when the citations should already be in their Zotero library.

## What I Got Wrong

1. **I investigated Zotero JSON matching** when the user said they should have an MCP server with Zotero integration
2. **I looked at text parsing heuristics** when I should have been looking at the actual data source
3. **I forgot the context** from the last 3 days of work even though it's documented

## What the Documentation Says (But I Misunderstood)

From `docs/IMPROVEMENTS-from-openai-suggestions.md`:

- There's a **citation cache** at `.cache/citation_validation/validation_cache.json`
- This cache stores "DOI → BibTeX mapping" and "arXiv ID → metadata"
- The source can be "Zotero API, CrossRef, etc."
- This is meant to enable **offline builds** and **reproducibility**

From `docs/active-fix-plan.md`:

- The PDF was generating successfully with 320 citations
- The focus was on fixing LaTeX compilation issues (Unicode, math mode, etc.)
- NOT on fetching citation metadata - implying it was already working

## What the User Said

> "I thought that we were converting with the MCP server that should have all these instructions there?"

> "I don't understand how you have so many missing citations as they should be in my Zotero"

> "your matching logic needs some improvement"

## What I Don't Understand

1. **Where is the MCP server?**
   - Is there supposed to be an MCP server running that provides citation data?
   - Or is "MCP" referring to something else in this context?

2. **What is the actual citation data source?**
   - Zotero API?
   - Local Zotero JSON export?
   - Citation cache (`validation_cache.json`)?
   - Local BibTeX file (`LOCAL_BIBTEX_PATH`)?
   - Some combination?

3. **How should URL matching work?**
   - The code in `converter.py:147-194` matches by URL and DOI against a Zotero JSON file
   - But no JSON file exists in the output directory
   - Is the JSON supposed to be generated? Or provided by the user? Or by an MCP server?

4. **What is `LOCAL_BIBTEX_PATH=dpp-fashion.bib`?**
   - This environment variable is being set in background processes
   - But the file `dpp-fashion.bib` doesn't exist
   - Is this a local bibliography that should exist?
   - Or is it supposed to be created?

5. **Why did citations work before but not now?**
   - The `active-fix-plan.md` shows PDF was generating with 320 citations
   - Now I'm seeing 124 Unknown citations
   - What changed? Did I break something? Or was the previous success misleading?

## What I Need OpenAI to Clarify

### Question 1: Citation Data Flow

Please describe the COMPLETE data flow for citation matching:

```
Markdown citations [Author (Year)](URL)
           ↓
      [STEP 1: ???]
           ↓
      [STEP 2: ???]
           ↓
    BibTeX entries with metadata
```

What are the actual steps? What queries what?

### Question 2: MCP Server Role

Is there supposed to be an MCP (Model Context Protocol) server running that:
- Provides access to Zotero library?
- Acts as a citation metadata service?
- Something else?

If yes:
- How does the converter connect to it?
- Where are the connection settings?
- How do I verify it's running?

### Question 3: Expected Setup

For a user to successfully convert mcp-draft-refined-v3.md to PDF with proper citations, what files/services MUST exist?

**Check all that apply:**
- [ ] Zotero desktop application running
- [ ] Zotero API key configured
- [ ] MCP server running (please explain what this is)
- [ ] Local Zotero JSON export (where? what name?)
- [ ] Local BibTeX file (`dpp-fashion.bib` - where should this come from?)
- [ ] Citation cache (`validation_cache.json` - auto-generated or pre-populated?)
- [ ] Something else (please describe)

### Question 4: The 124 "Unknown" Citations

The test suite shows 124 citations with author="Unknown", including:
- arXiv papers (should be easy to fetch)
- DOIs (should be easy to fetch)
- Web pages (harder but should try)

**Why are these Unknown?**
- [ ] Missing Zotero JSON file
- [ ] Missing citation cache
- [ ] MCP server not running
- [ ] URL matching logic broken
- [ ] Something else

### Question 5: Reproducibility

The improvements document emphasizes **offline reproducibility** via citation cache. How should this work?

**First run (with network):**
1. Read markdown citations
2. Fetch metadata from [WHERE?]
3. Save to cache
4. Generate BibTeX

**Subsequent runs (offline):**
1. Read markdown citations
2. Load from cache
3. Generate BibTeX (should be identical)

Is this correct? If not, what's the actual flow?

## What Would Help

1. **A step-by-step "new user" guide** for setting up citation matching from scratch
2. **A diagram** showing the data flow from markdown → BibTeX
3. **Expected file locations** with example contents
4. **How to verify** each component is working (Zotero? MCP? Cache?)
5. **How to debug** when citations are Unknown (what logs to check? what commands to run?)

## Current State

**Test Suite Output:**
- 124 Unknown authors
- 1 internal cross-reference issue
- PDF generates (212 KB)
- 1 LaTeX error, 458 warnings

**Files That Exist:**
- `mcp-draft-refined-v3.md` (input)
- `references.bib` (generated, but 124 entries have author="Unknown")
- No `dpp-fashion.bib`
- No Zotero JSON file
- No visible MCP server

**Background Processes Show:**
```bash
export LOCAL_BIBTEX_PATH=/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/dpp-fashion.bib
```

But this file doesn't exist.

## Please Help

I need a clear mental model of how this system is supposed to work so I can:
1. Diagnose the actual problem (not make up problems)
2. Fix the right thing (not fix imaginary issues)
3. Test properly (not claim success when it's failing)

The user has been patient but I keep going in circles because I don't understand the architecture.

**Can you provide:**
1. The canonical citation matching flow
2. What "MCP server" means in this context
3. What files should exist and where
4. How to verify the system is set up correctly
5. What I should actually fix to get from 124 Unknown → 0 Unknown

Thank you for your help. The user deserves better than my confused fumbling.

---

**Generated:** 2025-10-26
**Context:** Conversion of mcp-draft-refined-v3.md to arXiv-ready LaTeX
**Current Branch:** fix/verify-md-to-latex-conversion
**Test Suite:** `scripts/test_mcp_conversion.py` (now working, shows 124 failures)
