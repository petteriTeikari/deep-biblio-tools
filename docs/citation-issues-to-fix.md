# Citation Issues to Fix in Markdown Source

## Summary

After implementing multi-strategy citation matching and adding genuinely missing citations to Zotero, there are still issues in the markdown source that need manual correction.

## 1. Invalid arXiv IDs (CRITICAL - Must Fix Before Submission)

These citations reference non-existent arXiv papers. The arXiv ID format is wrong (should be YYMM.NNNNN, e.g., 2410.10762).

### Invalid Citations:
1. **`[Zhao et al., 2025](https://arxiv.org/abs/2025.mcp.taxonomy)`**
   - Location: Multiple places in security/taxonomy sections
   - Issue: arXiv ID `2025.mcp.taxonomy` is invalid format
   - Action: Find correct arXiv paper or remove citation

2. **`[Li et al., 2025](https://arxiv.org/abs/2025.mcp.privilege)`**
   - Location: Security sections about privilege escalation
   - Issue: arXiv ID `2025.mcp.privilege` is invalid format
   - Action: Find correct arXiv paper or remove citation

3. **`[Unknown, 2025](https://arxiv.org/abs/2025.mpma)`**
   - Location: Multi-agent sections
   - Issue: arXiv ID `2025.mpma` is invalid format
   - Action: Find correct arXiv paper or remove citation

## 2. Non-Citations Being Treated as Citations (Extract Issue)

These are regular hyperlinks (no year in citation) but got extracted as citations:

### Regular Hyperlinks (Not Citations):
1. **`[EON](https://www.eon.xyz/)`** - Product mentioned in text
2. **`[github.com/rednote-hilab/dots.ocr](https://github.com/rednote-hilab/dots.ocr)`** - Code repository reference
3. **`[out of these](https://docs.google.com/presentation/d/...)`** - TODO note with Google Slides link

**Root Cause**: The citation extractor needs to distinguish:
- **Citations**: `[Author, Year](URL)` - Has year in brackets
- **Hyperlinks**: `[Text](URL)` - No year, just descriptive text

**Status**: These were removed from Zotero. No action needed in markdown.

## 3. Valid Citations Successfully Added (13 total)

These were genuinely missing from Zotero and have been added:

### arXiv Preprints (7):
1. AFlow: Automating Agentic Workflow Generation (2410.10762)
2. Generative Agents: Interactive Simulacra (2304.03442)
3. Debate or Vote: Multi-Agent Decisions (2508.17536)
4. Analytics-Driven Supply Chain Visibility (2503.07231v1)
5. Microservice Architecture Insights (2408.10434)
6. AI and Software Security (2507.06323)
7. Secure Agentic AI Application (2504.16902)

### DOI Journal Articles (4):
1. Sustainable value in fashion industry (10.1002/sd.2474)
2. Blockchain in supply chains (10.1108/SCM-03-2024-0192)
3. Web3 Decentralization Illusion (10.2139/ssrn.5227972)
4. Transparency and value chain sustainability (10.1016/j.jclepro.2013.11.012)

### Still Unmatched (2):
1. Ellen MacArthur Foundation - circular economy page
2. Kate Fletcher book on Amazon

## 4. Remaining Work

### Immediate Action Required:
1. **Fix invalid arXiv IDs** - Search for correct papers or remove citations
2. **Verify all cited content** - Ensure URLs actually support the claims
3. **Export updated Zotero JSON** after fixing above issues
4. **Re-run conversion** to verify Unknown count drops significantly

### Citation Extractor Improvements Needed:
- Distinguish `[Author, Year](URL)` from `[Text](URL)`
- Only extract citations with year in brackets
- Validate arXiv ID format (YYMM.NNNNN) before accepting

## Current Status

- **Total citations**: 376
- **Unknown before fixes**: 34
- **Valid citations added to Zotero**: 13
- **Non-citations removed**: 6
- **Invalid arXiv IDs to fix**: 3
- **Expected Unknown after fixes**: ~18 (mostly Ellen MacArthur, Fletcher, and invalid arXiv IDs)

## Next Steps

1. Manually fix the 3 invalid arXiv citations in markdown source
2. Export updated Zotero JSON with the 13 newly added citations
3. Re-run conversion to verify improvements
4. Address remaining Unknown citations (Ellen MacArthur organizational author, Fletcher book without ISBN)
