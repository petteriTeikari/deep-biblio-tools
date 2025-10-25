# Phase 4: AST Refactoring - Realistic Implementation Plan

## Critical Reality Check

After analyzing the codebase, the current AST implementation is **largely non-functional**:
- Document reconstruction is not implemented (blocking ALL transformations)
- Parsers are created but barely used
- No working end-to-end AST pipeline exists
- Current code falls back to regex on any error

## Revised Phase 4 Breakdown

### Phase 4.0: Foundation Completion (PREREQUISITE)
**Without these, nothing else works**

#### 1. Complete Document Reconstruction (BLOCKER)
**File**: `src/converters/md_to_latex/post_processing_ast.py:277`

The `_reconstruct_document()` method currently just returns the original text with a warning. This makes the entire AST approach pointless.

**Implementation**:
```python
# Need to implement proper visitor pattern:
class LaTeXReconstructor:
    def visit_Command(self, node): ...
    def visit_Environment(self, node): ...
    def visit_Text(self, node): ...
    # etc for all node types
```

**Success Criteria**:
- Round-trip test: `parse(reconstruct(parse(doc))) == parse(doc)`
- All formatting preserved or intentionally normalized

#### 2. Verify Parser Implementations
**Files**: `src/parsers/markdown_parser.py`, `src/parsers/bibtex_parser.py`

**Current State Unknown** - Need to:
1. Check if parsers actually work
2. Add comprehensive test coverage
3. Ensure they handle real-world edge cases

#### 3. Create Integration Tests
**Missing Entirely** - Need tests that prove:
- Full document can be parsed → transformed → reconstructed
- Output is valid LaTeX/Markdown/BibTeX
- Performance is acceptable

### Phase 4.1: Fix Broken Integration

#### 1. AST Post-Processing Actually Works
Currently, any error causes fallback to regex. Need:
- Partial AST usage (use AST where possible, regex for unparseable parts)
- Better error recovery
- Clear logging of what succeeded/failed

#### 2. Real Parser Usage
Only 3 files import parsers. Need to:
- Actually use parsers in `biblio_checker.py` (currently just imports)
- Integrate with main processing pipeline
- Remove regex gradually, not all at once

### Phase 4.2: Address Performance Reality

#### 1. Benchmarking Infrastructure
Before claiming "AST is better", need proof:
```bash
# Benchmark script needed:
python benchmark_parsers.py --compare regex ast
# Should measure: time, memory, accuracy
```

#### 2. Memory Optimization
AST trees can be huge. Need:
- Lazy parsing options
- Streaming for large files
- AST node pooling/reuse

### Phase 4.3: Actual Utility Migration

Only after 4.0-4.2 are complete:

#### 1. Validators Using AST
- Start with simple validators (DOI format)
- Move to complex ones (citation structure)
- Keep regex for truly simple patterns

#### 2. MDPI/ResearchGate Fixes
- Parse → modify AST → reconstruct
- Not possible until reconstruction works!

### Phase 4.4: Advanced Features (Future)

These are nice-to-have, not Phase 4:
- AST diff/merge
- Query language
- Cross-format conversion
- Streaming parsers

## Realistic Timeline

### Week 1-2: Foundation
- [ ] Implement document reconstruction
- [ ] Test parser completeness
- [ ] Create round-trip tests

### Week 3: Integration
- [ ] Fix error handling in post_processing_ast
- [ ] Create benchmarking suite
- [ ] Actually use parsers in real code

### Week 4: Migration
- [ ] Migrate simplest validators first
- [ ] Document what must stay as regex
- [ ] Performance optimization

### Week 5+: Polish
- [ ] MDPI/ResearchGate fixes
- [ ] CLI integration
- [ ] Deprecation plan for regex code

## Critical Questions to Answer First

1. **Do the parsers even work?**
   ```bash
   pytest tests/parsers/ -v
   ```

2. **What's the current AST coverage?**
   ```bash
   # How much of a real document can we parse?
   python -m src.parsers.latex_parser sample.tex
   ```

3. **Is AST actually better?**
   - Need benchmarks before proceeding
   - Might find regex is fine for many cases

4. **What's the minimum viable AST?**
   - Maybe only use AST for specific transformations
   - Keep regex for simple patterns

## Red Flags in Current Plan

1. **"Update validators to use AST"** - Can't do without reconstruction
2. **"Fix MDPI workaround using AST"** - Can't do without reconstruction
3. **"Structured error reporting"** - Parsers may not provide position info
4. **"Performance comparable or better"** - Unproven assumption

## Minimum Viable Phase 4

If time is limited, focus on:

1. **Get ONE working AST pipeline**:
   - LaTeX parser → simple transform → reconstruction
   - With tests proving it works

2. **Benchmark it**:
   - Prove it's not slower
   - Document memory usage

3. **Migrate ONE complex regex**:
   - Pick the ugliest regex
   - Replace with AST
   - Show the code is cleaner

## Stop Conditions

Consider abandoning AST approach if:
- Reconstruction proves too complex
- Performance is significantly worse
- Parsers can't handle real-world documents
- Maintenance burden exceeds regex complexity

## Next Steps

1. **Run existing tests** to see what actually works
2. **Try to parse a real document** with each parser
3. **Implement minimal reconstruction** for proof of concept
4. **Benchmark before proceeding**

---

*This plan acknowledges that the AST migration might not be the right approach. It's better to discover this early than invest weeks in a failed refactoring.*
