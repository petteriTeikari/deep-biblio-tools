# User's Original Prompt - Matching Issues Analysis Request
**Date**: 2025-10-31 Early Morning
**Context**: After discovering RDF has 1,751 entries but converter reports hundreds missing

---

## Original User Prompt

I don't know obviously the exact number of missing citations but my initial hunch is that the RDF should be rather complete, with the max of 5 missing citations being a realistic guestimate, and would like to add those few glitches then manually to my Zotero.. but definitely no hundreds of missing citations can exist, so my bet is heavily on your matching logic that should be made then more robust.

Could you again read all our older documents on this as this is not the first time that you fail to match. Remember to reference the old documents in the newly created matching logic paper, and then synthesize these old documents with new insights on your analysis, on what you think are the hypotheses for matching issues, and what you think are the possible solutions (do not go with the first issue that you encounter, but do a comprehensive analysis) could exist to make this robust, what tests, precommit checks we could need to verify these quality.

And how do we verify in real-time that there are some fallback strategies and that matching logic is solid, match arxiv identifiers, pubmed identifiers and doi codes instead of full hyperlinks. How to match the Amazon books, articles, NEVER USE any KEY MATCHING (which you should remember) as there is no such things as local reference key! Keys come from Zotero as they are either as basic (non-better bibtex) keys that are regenerated every time during the conversion.

So along with the --no-cache flag, we should delete all old .aux, .tex, .pdf, .bbl, and references.bib files from the output folder to avoid the possible glitch that you are using some stale data for whatever (this I have asked you to do before, can you verify that you have done this).

And could you first improve this initial prompt an improve it for Claude's code prompting as something very comprehensive! Save my initial prompt and the refined prompt along with the newly created report on these matching issues.

After developing the plan, commit, and start executing all the phases of it commits+pushes between phases and you work until the end of the plan without breaks. If you feel like pausing and printing me summary, write rather a markdown file to disk about the status and continue with the work. I go to sleep now, so hopefully have some improvements when I wake up. Address all those issues that you just identified with these thoughts that I gave you

---

## Key Requirements Extracted

### Analysis Requirements
1. **Read ALL old matching failure documents** - this is recurring issue
2. **Synthesize old + new insights** into comprehensive analysis
3. **Multiple hypotheses** for matching issues (not just first one encountered)
4. **Comprehensive solutions** with tests and pre-commit checks
5. **Real-time verification strategies** with fallback mechanisms

### Matching Strategy Requirements
1. **Match by identifiers FIRST** (DOI, arXiv ID, PubMed ID) - NOT full hyperlinks
2. **Handle Amazon books** properly
3. **NEVER match by keys** - keys are generated fresh each time, not stable
4. **URL normalization** - handle variations

### Implementation Requirements
1. **--no-cache flag** - disable all caching
2. **Clean output directory** - delete .aux, .tex, .pdf, .bbl, references.bib before conversion
   - User has requested this before - verify if implemented
3. **Commit after each phase** with push
4. **Work continuously** - write markdown status files instead of printing summaries
5. **Complete all phases** without breaks

### Success Criteria
- RDF has 1,751 entries
- Expected missing: ~5 citations max
- Current failure: Hundreds reported missing
- Root cause: Matching logic, NOT missing data

---

## User Context
- User is going to sleep
- Wants improvements ready when they wake up
- This is a recurring problem ("not the first time that you fail to match")
- User has high confidence RDF is complete
- User expects systematic, comprehensive approach

---

## Next Steps (Per User Request)
1. ✅ Save this original prompt
2. ⏭️ Create refined/improved version of prompt
3. ⏭️ Read all old matching failure documents
4. ⏭️ Create comprehensive matching analysis report
5. ⏭️ Develop comprehensive plan
6. ⏭️ Execute all phases with commits/pushes
7. ⏭️ Work until completion
