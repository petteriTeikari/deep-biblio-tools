# Emergency Mode: Hard-Coded Bans Plan
**Date**: 2025-10-31
**Problem**: Flags-based approach failed - fetching still happening
**User insight**: "Hard-code the BANS temporarily, fix flags later"
**Status**: Shallow flag-based fixes didn't work - need GUARANTEED solution

---

## User's Critical Feedback

> "are you just getting the first hit that your search gives and be happy to fix that without doing any comprehensive / systematic testing of the issues, are you comprehensively search for all occurrences, coming up with multiple hypotheses where the problems come from. Your fixing seems awfully shallow without actually fixing the issue.. and especially you should realize during the conversion that you are violating the rules! Like how come you have zero guardrails there that ban the fetching!"

**Translation**: I'm doing shallow, reactive fixes instead of systematic, comprehensive solutions.

---

## Why Flags-Based Approach Failed

###

 My Attempted Fixes
1. Added `emergency_mode` flag to classes
2. Added `if not self.emergency_mode:` checks
3. Claimed success without verification

### What Actually Happened
- ✅ Flag was set ("🚨 Emergency Mode active" appeared)
- ❌ Fetching still happened ("Fetching citation metadata: 0/227")
- ❌ Auto-add attempts still happened
- ❌ No runtime guardrails to detect violations

### Why It Failed
1. **Incomplete coverage**: Didn't find ALL fetching locations
2. **No verification**: Didn't test before committing
3. **No guardrails**: Code didn't CRASH when rules violated
4. **Shallow search**: Found first hit, didn't search comprehensively

---

## User's Better Approach: Hard-Coded Bans

### The Idea
Instead of trying to thread flags through complex codepaths:
1. **HARD-CODE the bans** in deterministic_convert.py
2. **Comment out** ALL fetching code
3. **Raise exceptions** if forbidden code paths are reached
4. **GUARANTEE** zero fetching by removing the code entirely

### Why This Works
- ✅ Simple and verifiable
- ✅ Impossible to bypass (code doesn't exist)
- ✅ Easy to test (just run conversion)
- ✅ Can refactor to flags later once working

### Implementation Strategy
1. Fork scripts/deterministic_convert.py → scripts/deterministic_convert_emergency.py
2. In emergency version: Comment out ALL fetching code
3. Add runtime guardrails that CRASH if forbidden paths reached
4. Test thoroughly
5. Later: Refactor to use flags (once we understand ALL code paths)

---

## Comprehensive Search Strategy (Before Any Fixes)

### Step 1: Find ALL Fetching Locations

```bash
# Search for fetch function definitions
grep -rn "def.*fetch" src/converters/md_to_latex/*.py

# Search for fetch function calls
grep -rn "\.fetch" src/converters/md_to_latex/*.py | grep -v "def "

# Search for API calls
grep -rn "requests\." src/converters/md_to_latex/*.py
grep -rn "http" src/converters/md_to_latex/*.py | grep -i "get\|post"

# Search for CrossRef/arXiv specific calls
grep -rn "crossref\|arxiv" src/converters/md_to_latex/*.py -i

# Search for auto-add
grep -rn "auto.add\|auto_add" src/converters/md_to_latex/*.py -i

# Search for temp key generation
grep -rn "failedAutoAdd\|temp.*key" src/converters/md_to_latex/*.py -i
```

### Step 2: Document ALL Locations Found

Create a table of EVERY location:

| File | Line | Function | What It Does | How to Disable |
|------|------|----------|--------------|----------------|
| ... | ... | ... | ... | ... |

### Step 3: Multiple Hypotheses for Each

For each location, ask:
1. Why is this being called in emergency mode?
2. What flag should prevent this?
3. Where is that flag checked?
4. Is the check working?
5. If not, why not?

---

## Hard-Coded Ban Implementation

### Option A: Fork the Script (Recommended)

Create `scripts/deterministic_convert_emergency.py`:

```python
"""
EMERGENCY MODE ONLY - ZERO NETWORK CALLS

This is a hard-coded emergency version that GUARANTEES
zero network calls by removing all fetching code.

DO NOT use for normal conversions - this is read-only mode.
"""

# At top of file - HARD-CODED configuration
EMERGENCY_MODE = True  # Cannot be changed
ALLOW_FETCHING = False  # Hard-coded ban
ALLOW_AUTO_ADD = False  # Hard-coded ban
ALLOW_TEMP_KEYS = True  # We need these for missing citations

# Runtime guardrail function
def _verify_no_network_calls():
    """Runtime check to ensure no network calls happen."""
    import sys
    import os

    # Override requests library to crash on any HTTP call
    import requests as _original_requests

    class BannedRequestsModule:
        def get(self, *args, **kwargs):
            raise RuntimeError(
                "❌ EMERGENCY MODE VIOLATION: HTTP GET attempted!\n"
                f"URL: {args[0] if args else 'unknown'}\n"
                "Emergency mode MUST NOT make network calls."
            )

        def post(self, *args, **kwargs):
            raise RuntimeError(
                "❌ EMERGENCY MODE VIOLATION: HTTP POST attempted!\n"
                "Emergency mode MUST NOT make network calls."
            )

        # Add other HTTP methods as needed

    # Replace requests module
    sys.modules['requests'] = BannedRequestsModule()

    print("🛡️  Runtime guardrails activated - network calls will crash the process")

# Call guardrails at script startup
_verify_no_network_calls()

# Rest of script...
```

### Option B: Comment Out Fetching Code

In citation_manager.py, temporarily hard-code:

```python
def fetch_citation_metadata(self, citation: Citation) -> None:
    """Fetch additional metadata for a citation.

    EMERGENCY MODE: This function is DISABLED.
    """
    # HARD-CODED BAN for emergency mode testing
    raise RuntimeError(
        "❌ fetch_citation_metadata() called in emergency mode!\n"
        "This should NEVER happen. Emergency mode must use RDF data only.\n"
        f"Citation URL: {citation.url}"
    )

    # Original code commented out:
    # cached_citation = self._load_from_cache(citation.url)
    # ...
```

### Option C: Runtime Assertion Checks

Add assertions at key points:

```python
def convert(self, markdown_file: Path, output_dir: Path | None = None):
    """Convert markdown to LaTeX."""

    # EMERGENCY MODE GUARDRAIL
    if self.emergency_mode:
        # Verify auto-add is disabled
        assert self.citation_manager.zotero_auto_add is None, \
            "Emergency mode violation: auto-add should be None"

        # Verify cache is disabled
        assert not self.use_cache, \
            "Emergency mode violation: cache should be disabled"

        # Verify no fetching will happen
        original_fetch = self.citation_manager.fetch_citation_metadata
        def banned_fetch(*args, **kwargs):
            raise RuntimeError("Emergency mode violation: fetch_citation_metadata called!")
        self.citation_manager.fetch_citation_metadata = banned_fetch

    # Continue with conversion...
```

---

## Updated Testing Plan with Runtime Guardrails

### Phase 0: Developer Pre-Flight (MANDATORY)

#### Step 0.1: Comprehensive Search
```bash
# Find ALL fetching locations
bash scripts/find_all_fetch_locations.sh > fetch_locations.txt

# Review EVERY location
cat fetch_locations.txt

# Verify understanding of each location
# Document in table format
```

#### Step 0.2: Implement Hard-Coded Bans
```python
# Choose ONE approach:
# - Option A: Fork script (cleanest)
# - Option B: Comment out code (fastest)
# - Option C: Runtime assertions (most defensive)

# Implement chosen approach
```

#### Step 0.3: Add Runtime Guardrails
```python
# Add crash-on-violation checks
# Add logging for verification
# Add performance timing
```

#### Step 0.4: Developer Smoke Test
```bash
# Run conversion
time uv run python scripts/deterministic_convert_emergency.py \
  test.md \
  --rdf test.rdf \
  --output-dir /tmp/test \
  2>&1 | tee dev-test.log

# Verify guardrails
grep -c "Fetching" dev-test.log  # Should be 0
grep -c "auto-add" dev-test.log  # Should be 0
grep -c "guardrails activated" dev-test.log  # Should be > 0

# Check performance
# Should be <30 seconds

# If ANY check fails → fix and repeat
# DO NOT proceed until ALL pass
```

#### Step 0.5: Create Evidence Document
```markdown
# Developer Verification Evidence

## Comprehensive Search Results
- Found X fetch locations
- Found Y auto-add locations
- Found Z temp key locations

## Implementation Approach
- Used Option [A/B/C]
- Reasoning: [why]

## Smoke Test Results
- Time: X seconds
- Fetching count: 0 ✅
- Auto-add count: 0 ✅
- Guardrails triggered: 0 ✅
- PDF generated: Yes ✅

## Evidence Files
- dev-test.log (conversion log)
- fetch_locations.txt (comprehensive search)
- test-output.pdf (generated PDF)
```

### Phase 1: User Testing (Only After Phase 0 Passes)

Same as before, but with confidence that basic functionality works.

---

## Multiple Hypotheses for Current Failures

### Hypothesis 1: generate_bibtex_file() Still Fetching

**Evidence**: Progress bar shows "Fetching citation metadata: 0/227"

**Location**: citation_manager.py:1770-1795

**Current code**:
```python
for key, citation in citation_pbar:
    if not self.emergency_mode:
        self.fetch_citation_metadata(citation)
    bibtex_entries.append(citation.to_bibtex())
```

**Why it might be failing**:
1. Flag not set properly
2. Code not reloaded
3. Different code path being used
4. Progress bar created before check

**Test**:
```python
# Add logging
logger.info(f"Emergency mode flag: {self.emergency_mode}")
if not self.emergency_mode:
    logger.info("Calling fetch_citation_metadata()")
    self.fetch_citation_metadata(citation)
else:
    logger.info("Skipping fetch_citation_metadata() - emergency mode")
```

### Hypothesis 2: Progress Bar Misleading

**Evidence**: Progress bar says "Fetching" but maybe not actually fetching?

**Test**: Check if actual HTTP calls are made (use tcpdump or mitmproxy)

```bash
# Monitor network activity
sudo tcpdump -i any port 80 or port 443 -w /tmp/conversion-traffic.pcap &
TCPDUMP_PID=$!

# Run conversion
uv run python scripts/deterministic_convert.py ...

# Stop monitoring
sudo kill $TCPDUMP_PID

# Check if any traffic
tcpdump -r /tmp/conversion-traffic.pcap | wc -l
# Should be 0
```

### Hypothesis 3: Multiple Code Paths

**Evidence**: Maybe converter.py uses different method?

**Locations to check**:
1. converter.py:1103 - Pre-fetch loop (already fixed?)
2. citation_manager.py:1780+ - generate_bibtex_file loop
3. citation_manager.py:713 - fetch_citation_metadata definition
4. Other?

**Test**: Add unique logging to EACH location

```python
# converter.py:1103
logger.info("[CONVERTER] About to call fetch_citation_metadata")

# citation_manager.py:1780
logger.info("[CITMAN-GENERATE] About to call fetch_citation_metadata")

# citation_manager.py:713
logger.info("[CITMAN-FETCH] fetch_citation_metadata() called!")
```

Then grep logs to see which path is taken.

### Hypothesis 4: Caching Makes It Look Like Fetching

**Evidence**: Maybe it's loading from cache, not actually fetching?

**Test**: Disable cache entirely in emergency mode

```python
if self.emergency_mode:
    self.cache = None
    self.use_cache = False
```

---

## Implementation Order

### Immediate (Next 30 Minutes)

1. **Stop** trying to fix with flags
2. **Search** comprehensively for ALL fetch locations
3. **Document** findings in table
4. **Choose** hard-coded ban approach (A, B, or C)
5. **Implement** chosen approach
6. **Add** runtime guardrails
7. **Test** with developer smoke test
8. **Create** evidence document
9. **THEN** commit

### Short Term (Next Session)

1. Review evidence with user
2. Run user acceptance testing
3. Fix any issues found
4. Generate missing citations list

### Long Term (Future)

1. Refactor hard-coded bans to use flags properly
2. Understand WHY flags didn't work
3. Add integration tests for emergency mode
4. Document lessons learned

---

## Success Criteria

### Developer Pre-Flight Must Show:
- ✅ Comprehensive search completed (all locations documented)
- ✅ Chosen approach implemented
- ✅ Runtime guardrails added
- ✅ Dev smoke test passed (0 fetching, 0 auto-add)
- ✅ Performance <30 seconds
- ✅ Evidence document created
- ✅ NO claims of success - just "ready for user testing"

### User Testing Must Show:
- ✅ ZERO network calls (verify with tcpdump)
- ✅ ZERO fetching messages in logs
- ✅ ZERO auto-add attempts
- ✅ Missing citations list generated
- ✅ PDF compiles successfully
- ✅ Performance <30 seconds

---

## Next Steps

**Waiting for user approval of this approach before proceeding.**

Questions for user:
1. Which hard-coded ban option do you prefer (A/B/C)?
2. Should I implement comprehensive search first, or jump to hard-coded bans?
3. Any other guardrails you want added?

**I will NOT proceed with shallow fixes - only systematic, comprehensive implementation.**
