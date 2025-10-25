# Script Inventory and Consolidation Plan

## Script Analysis Table

| Script Name | Category | Primary Function | Dependencies | Duplicate Of | Decision | Target Module |
|-------------|----------|------------------|--------------|--------------|----------|---------------|
| **Bibliography Processing** |
| `bib_key_fixes.py` | BibTeX | Fix citation keys | bibtexparser | - | Merge | `src.bibliography.key_formatter` |
| `fix_bibliography.py` | BibTeX | General fixes | bibtexparser | - | Merge | `src.bibliography.fixer` |
| `fix_bibliography_errors.py` | BibTeX | Error correction | bibtexparser | - | Merge | `src.bibliography.fixer` |
| `sort_bibliography.py` | BibTeX | Sort entries | bibtexparser | - | Merge | `src.bibliography.sorter` |
| `debug_bibliography_sorting.py` | Debug | Debug sorting | - | sort_bibliography | Archive | - |
| `convert_bib_keys_to_authoryear.py` | BibTeX | Convert key format | bibtexparser | - | Merge | `src.bibliography.key_formatter` |
| `convert_arxiv_citekey_authoryear.py` | BibTeX | ArXiv key format | bibtexparser | convert_bib_keys | Merge | `src.bibliography.key_formatter` |
| `merge_bibliographies.py` | BibTeX | Merge .bib files | bibtexparser | - | Merge | `src.bibliography.merger` |
| `unique_bibentries.py` | BibTeX | Remove duplicates | bibtexparser | - | Merge | `src.bibliography.deduplicator` |
| `check_bibliography_duplicates.py` | BibTeX | Find duplicates | bibtexparser | unique_bibentries | Merge | `src.bibliography.deduplicator` |
| **Citation Processing** |
| `extract_citations.py` | Citation | Extract from text | - | - | Merge | `src.bibliography.citation_extractor` |
| `extract_drone_citations.py` | Citation | Domain extraction | - | extract_citations | Keep | Script (domain-specific) |
| `extract_refs_from_tex.py` | Citation | Extract from LaTeX | pylatexenc | - | Merge | `src.bibliography.citation_extractor` |
| `extract_missing_citations.py` | Citation | Find missing | - | - | Merge | `src.bibliography.validator` |
| `validate_citations.py` | Citation | Validate format | - | - | Merge | `src.bibliography.validator` |
| `validate_llm_citations.py` | Citation | Validate LLM output | requests | - | Merge | `src.bibliography.llm_validator` |
| `validate_bibliography_entries.py` | Citation | Validate entries | bibtexparser | - | Merge | `src.bibliography.validator` |
| `fix_unknown_authors.py` | Citation | Fix author data | requests | - | Merge | `src.bibliography.author_resolver` |
| `fix_unknown_refs.py` | Citation | Fix references | requests | - | Merge | `src.bibliography.reference_resolver` |
| **LaTeX Bibliography** |
| `convert_latex_hardcoded_bibliography.py` | LaTeX | Convert hardcoded | pylatexenc | - | Merge | `src.converters.latex_to_bibtex` |
| `extract_hardcoded_bibliography.py` | LaTeX | Extract hardcoded | pylatexenc | - | Merge | `src.converters.latex_to_bibtex` |
| `hardcode_biblio_authoryear_hyperlinks.py` | LaTeX | Add hyperlinks | - | - | Merge | `src.converters.latex_to_bibtex` |
| **Document Conversion** |
| `convert_markdown_to_latex.py` | Convert | MD to LaTeX | pypandoc | - | Merge | `src.converters.md_to_latex` |
| `md_to_latex.py` | Convert | MD to LaTeX | - | convert_markdown | Archive | - |
| `convert_markdown_to_latex_full.py` | Convert | Full pipeline | - | - | Merge | `src.converters.md_to_latex` |
| `run_pipeline.py` | Pipeline | Run conversion | - | - | Keep | CLI script |
| `run_complete_pipeline.py` | Pipeline | Full pipeline | - | run_pipeline | Merge | CLI script |
| `clean_markdown_before_conversion.py` | Convert | Pre-process MD | - | - | Merge | `src.converters.preprocessor` |
| **Drone-Specific** |
| `convert_drone_validated.py` | Domain | Convert drone docs | - | - | Keep | Script (active) |
| `archive/convert_drone_*.py` | Domain | Various versions | - | - | Archive | Already archived |
| **Utilities** |
| `remove_unresolved_links.py` | Utils | Clean links | - | - | Merge | `src.utils.link_cleaner` |
| `test_thinking_tag_removal.py` | Utils | Remove AI tags | - | - | Merge | `src.utils.ai_artifact_cleaner` |
| `test_abbreviation_checker.py` | Utils | Check abbrevs | - | - | Delete | Use pytest |
| `test_citation_style_fixer.py` | Utils | Fix styles | - | - | Delete | Use pytest |
| **Development Tools** |
| `fix_imports.py` | Dev | Fix imports | - | - | Delete | One-time use |
| `install-git-hooks.sh` | Dev | Install hooks | - | - | Keep | Shell script |
| `validate_claude_constraints.py` | Dev | Validate rules | - | - | Keep | Dev tool |

## Consolidation Summary

### Scripts to Consolidate: 35
- Bibliography Processing: 19 scripts → 8 modules
- Document Conversion: 8 scripts → 3 modules
- Utilities: 4 scripts → 2 modules
- Testing: 4 scripts → Delete (use pytest)

### Scripts to Keep: 6
- `extract_drone_citations.py` - Domain-specific
- `convert_drone_validated.py` - Active domain converter
- `run_pipeline.py` - CLI runner
- `install-git-hooks.sh` - Shell script
- `validate_claude_constraints.py` - Dev tool
- Merged `run_complete_pipeline.py` - Enhanced CLI runner

### Scripts to Archive/Delete: 49
- All 26 scripts already in `archive/`
- 19 redundant/duplicate scripts
- 4 test scripts (replaced by pytest)
