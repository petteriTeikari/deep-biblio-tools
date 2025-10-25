# Bibliography Formatting Rules for Hardcoded LaTeX

This document describes the formatting rules implemented in `scripts/hardcode_bibliography.py` for converting .bib entries to hardcoded LaTeX bibliography entries with hyperlinked authors and years.

## Core Principles

1. **Author names and publication years are hyperlinked** to enable direct access in digital PDFs
2. **HTML entities are converted** (e.g., `&amp;` → `&`)
3. **Different reference types receive specific formatting** based on their classification

## Reference Type Classification

References are classified based on the presence of DOI and arXiv identifiers:

- **Academic references**: Have either a DOI or arXiv ID
- **Non-academic references**: Have neither DOI nor arXiv ID

## Formatting Rules by Type

### 1. Academic Journal Articles (with DOI)

**Rule**: Journal name and volume are italicized together using `{\em Journal Volume}`

**Example Input**:
```bibtex
@article{ahmad2024,
  author = "Ahmad et al.",
  title = "Digital Twin-Enabled Building Information Modeling...",
  journal = "Buildings",
  volume = "15",
  number = "10",
  pages = "1584",
  doi = "10.3390/buildings15101584",
  year = "2024"
}
```

**Example Output**:
```latex
\bibitem{ahmad2024} \href{https://doi.org/10.3390/buildings15101584}{Ahmad et al. (2024)} Digital Twin-Enabled Building Information Modeling... {\em Buildings 15}(10):1584.
```

### 2. arXiv Preprints

**Rule**: Display as `{\em arXiv:ID}` where ID is extracted from the URL or eprint field

**Example Input**:
```bibtex
@article{ahmed2025,
  author = "Manzoor Ahmed and ...",
  title = "Toward a Sustainable Low-Altitude Economy...",
  journal = "arXiv",
  url = "https://arxiv.org/abs/2504.02162",
  year = "2025"
}
```

**Example Output**:
```latex
\bibitem{ahmed2025} \href{https://arxiv.org/abs/2504.02162}{Manzoor Ahmed and ... (2025)} Toward a Sustainable Low-Altitude Economy... {\em arXiv:2504.02162}.
```

### 3. Conference Proceedings

**Rule**: Conference proceedings containing "Proceedings", "Conference", or "Workshop" in the journal field are italicized

**Example Input**:
```bibtex
@inproceedings{abaza2024,
  author = "Hazem Abaza and ...",
  title = "Managing End-to-End Timing Jitters...",
  journal = "Proceedings of the 32nd International Conference on Real-Time Networks and Systems",
  pages = "229-241",
  doi = "10.1145/3696355.3696363",
  year = "2024"
}
```

**Example Output**:
```latex
\bibitem{abaza2024} \href{https://doi.org/10.1145/3696355.3696363}{Hazem Abaza and ... (2024)} Managing End-to-End Timing Jitters... {\em Proceedings of the 32nd International Conference on Real-Time Networks and Systems}:229--241.
```

### 4. Non-Academic References (Web Resources)

**Rule**: Include "(accessed YYYY-MM-DD)" at the end using the urldate field

**Example Input**:
```bibtex
@misc{affairs2025,
  author = "Consumer Affairs",
  title = "Water damage insurance claims statistics",
  journal = "Web page",
  url = "https://www.consumeraffairs.com/...",
  urldate = "2025-08-02",
  year = "2025"
}
```

**Example Output**:
```latex
\bibitem{affairs2025} \href{https://www.consumeraffairs.com/...}{Consumer Affairs (2025)} Water damage insurance claims statistics Web page (accessed 2025-08-02).
```

## Additional Formatting Details

### Page Ranges
- Single dash `-` is converted to double dash `--` for proper LaTeX rendering
- Example: `46-56` → `46--56`

### HTML Entity Conversion
Common conversions include:
- `&amp;` → `&`
- `&lt;` → `<`
- `&gt;` → `>`
- `&quot;` → `"`
- `&nbsp;` → ` ` (space)
- `&ndash;` → `--`
- `&mdash;` → `---`

### Author Formatting
- "and others" is converted to "et al."
- Reversed names (Last, First) are converted to First Last format
- Multiple authors are joined with commas, with "and" before the last author

### URL Priority for Hyperlinking
1. Use provided URL if available
2. Otherwise, construct from DOI: `https://doi.org/{doi}`
3. For arXiv, construct from ID: `https://arxiv.org/abs/{arxiv_id}`

## Usage Example

```bash
python scripts/hardcode_bibliography.py input.tex references.bib -o output.tex
```

This creates:
- `input_hardcoded.bbl` - Just the bibliography entries
- `output.tex` - Complete document with hardcoded bibliography

## Validation Warnings

The script warns about:
- Missing URLs for entries that appear to be web resources
- Malformed author names (e.g., "et al." as the only author)
- Missing essential fields (title, year, authors)
