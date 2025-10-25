## **Python Script Request: LaTeX Manual Bibliography Author-Year Converter with Hyperlink Preservation**

I need a robust, production-ready Python script that converts numbered citations in a manually-created LaTeX bibliography to author-year format while preserving all hyperlinks and handling complex edge cases. The script should be saved as `scripts/fix-manual-biblio-to-authornames.py`.

### **Current Situation:**

* I have a LaTeX document using `natbib` package with `[authoryear,round]` option
* The bibliography is manually created using `\begin{thebibliography}{99}` environment
  * **Important**: The `{99}` is NOT the count of entries but a WIDTH PARAMETER for label formatting
  * The actual bibliography contains 607 entries
  * This width parameter should be `{999}` for 3-digit reference numbers (100-999)
  * With `{99}`, LaTeX only allocates space for 2-digit labels, causing misalignment
* Current `\bibitem` entries are formatted as: `\bibitem{key} \href{url}{Author names (Year)} Title...`
* Citations appear as numbers \[1\], \[2\], ... \[607\] instead of (Author, Year) format
* Document uses `\citep` and `\citet` commands throughout
* Some journals require this manual bibliography format for submission (won't accept .bib files)

### **Understanding the Width Parameter:**

latex

```
\begin{thebibliography}{9}    % For 1-9 references
\begin{thebibliography}{99}   % For 1-99 references
\begin{thebibliography}{999}  % For 1-999 references
\begin{thebibliography}{ABC}  % Custom width based on "ABC" string width
```

### **Required Transformation:**

Convert each `\bibitem` entry from:

latex

```
\bibitem{altawaitan2025} \href{https://arxiv.org/abs/2505.06748}{Abdullah Altawaitan, Jason Stanley, Sambaran Ghosal, Thai Duong, Nikolay Atanasov (2025)} Learned IMU Bias Prediction...
```

To:

latex

```
\bibitem[Altawaitan et al.(2025)]{altawaitan2025} \href{https://arxiv.org/abs/2505.06748}{Abdullah Altawaitan, Jason Stanley, Sambaran Ghosal, Thai Duong, Nikolay Atanasov (2025)} Learned IMU Bias Prediction...
```

### **Comprehensive Rules for Author-Year Format:**

#### **Basic Rules:**

1. **Single author**: `\bibitem[Smith(2025)]{key}`
2. **Two authors**: `\bibitem[Smith and Jones(2025)]{key}`
3. **Three or more authors**: `\bibitem[Smith et al.(2025)]{key}`
4. **No space before parentheses**: `Smith(2025)` not `Smith (2025)`

#### **Name Parsing Complexities:**

1. **Prefixes and particles**:
   * `given=João, prefix=de, useprefix=true family=Sousa` → `de Sousa`
   * `given=Bart, prefix=de, useprefix=true family=Koning` → `de Koning`
   * `given=Guido C. H. E., prefix=de, useprefix=true family=Croon` → `de Croon`
   * Handle: van, von, de, da, della, del, van der, von der, de la, etc.
   * Capitalization: "Van" at sentence start, "van" otherwise
2. **Special name formats**:
   * Middle initials: `John A. Smith` → extract as `Smith`
   * Hyphenated names: `Mary Smith-Jones` → keep as `Smith-Jones`
   * Asian names: Be careful with `Xiaoming Wang` vs `Wang Xiaoming`
   * Names with Jr., Sr., III: `Martin Luther King Jr.` → `King`
3. **Organization/Corporate authors**:
   * Single org: `\bibitem[IEEE(2025)]{key}`
   * Multiple orgs: `\bibitem[IEEE and ACM(2025)]{key}`
   * Gov agencies: `\bibitem[U.S. Department of Energy(2025)]{key}`
   * Websites: `\bibitem[rerun.io(2025)]{key}` for URLs as authors

### **Self-Reflection: What Can Go Wrong in This Conversion?**

#### **1\. Ambiguous Author-Title Boundaries**

latex

```
# Where do authors end and title begin?
\bibitem{prob1} \href{...}{Smith (2025) Machine Learning (2025) Applications}
# Is it "Smith" or "Smith (2025) Machine"?

\bibitem{prob2} \href{...}{IEEE Computer Society (2025) IEEE Conference on...}
# Organization name contains "IEEE" twice

\bibitem{prob3} \href{...}{von Neumann and Turing (1950) and McCarthy (1960)}
# Multiple papers? Parsing nightmare!
```

#### **2\. Year Extraction Disasters**

latex

```
# Multiple years in entry
\bibitem{prob4} \href{.../2024/...}{Smith (2023, revised 2024, published 2025)}

# Year in title but not in author section
\bibitem{prob5} \href{...}{Smith} The 2025 Conference Proceedings

# No year at all
\bibitem{prob6} \href{...}{Ancient Manuscript} Undated text

# Year embedded in author name
\bibitem{prob7} \href{...}{Smith2025Conference Proceedings}
```

#### **3\. Author Parsing Failures**

latex

```
# "and" is part of organization name
\bibitem{prob8} \href{...}{Procter and Gamble (2025)}
# Should be [Procter and Gamble(2025)] not [Procter and Gamble(2025)]

# Comma in organization name
\bibitem{prob9} \href{...}{Microsoft, Inc. (2025)}

# Mixed format in same entry
\bibitem{prob10} \href{...}{J. Smith, IBM Corporation, K. Jones (2025)}

# Already formatted with et al.
\bibitem{prob11} \href{...}{Smith et al. (2025)}
# Don't want [Smith et al. et al.(2025)]!

# Unicode nightmares
\bibitem{prob12} \href{...}{李明, José García, Müller (2025)}
```

#### **4\. LaTeX Command Interference**

latex

```
# LaTeX commands in names
\bibitem{prob13} \href{...}{Sm\"{i}th, O'Re\~{i}lly, \v{C}ech (2025)}

# Nested braces
\bibitem{prob14} \href{...}{{\em Smith}, \textbf{Jones} (2025)}

# Math mode in author names (yes, it happens!)
\bibitem{prob15} \href{...}{Smith$^{*}$, Jones$^{\dagger}$ (2025)}
# * = corresponding author, † = equal contribution
```

#### **5\. Hyperlink Preservation Issues**

latex

```
# Multiple hyperlinks
\bibitem{prob16} \href{url1}{Smith (2025)} Also available at \href{url2}{here}

# Hyperlink contains braces
\bibitem{prob17} \href{https://example.com/\{id\}}{Smith (2025)}

# No hyperlink at all
\bibitem{prob18} Smith (2025) Local document

# Hyperlink in wrong place
\bibitem{prob19} Smith \href{...}{(2025)} Title
```

#### **6\. Multi-line Entry Chaos**

latex

```
# Line breaks in unexpected places
\bibitem{prob20} \href{https://
example.com}{Smith,
Jones,
Williams (
2025)} Title

# Comments breaking up entry
\bibitem{prob21} \href{...}{Smith % TODO: verify
(2025)} Title

# Escaped line endings
\bibitem{prob22} \href{...}{Smith,\\
Jones (2025)} Title
```

#### **7\. Edge Cases from Hell**

latex

```
# Empty author field
\bibitem{prob23} \href{...}{(2025)} Anonymous work

# Looks like code/data
\bibitem{prob24} \href{...}{10.1038/nature.2025.12345 (2025)}

# Conference name that looks like authors
\bibitem{prob25} \href{...}{Smith and Jones Conference (2025)}

# Author is a URL
\bibitem{prob26} \href{https://github.com}{https://github.com (2025)}

# Circular reference
\bibitem{prob27} \href{...}{See \cite{prob28} (2025)}

# Non-standard year format
\bibitem{prob28} \href{...}{Smith (2025/2026)}
\bibitem{prob29} \href{...}{Jones (forthcoming)}
\bibitem{prob30} \href{...}{Williams (in press)}
```

#### **8\. Width Parameter Complications**

latex

```
# What if someone used a custom width?
\begin{thebibliography}{Smith2025}  % Using longest label as width

# What if there are multiple bibliographies?
\begin{thebibliography}{99}
...
\end{thebibliography}
\begin{thebibliography}{AAA}  % Different width parameter
...
\end{thebibliography}
```

### **Script Requirements:**

#### **Core Functionality:**

1. **Input/Output**:
   * Save to `scripts/fix-manual-biblio-to-authornames.py`
   * Accept file path or stdin
   * Output to file, stdout, or in-place editing
   * UTF-8 encoding support with BOM detection
   * Handle large files (600+ bibliography entries efficiently)
2. **Width Parameter Detection**:
    python

```py
# Detect current width parameter
# Count actual entries
# Suggest correct width: {9}, {99}, {999}, or {9999}
# Optionally auto-fix the width parameter
# Warn if custom width string is used
```

4.

5. **Parsing Strategy**:
   * State machine for robust multi-line parsing
   * Heuristics for author-title boundary detection
   * Confidence scoring for ambiguous cases
   * Fallback strategies when parsing fails
6. **Error Recovery**:
    python

```py
# When parsing fails, options:
# 1. Skip entry (log it)
# 2. Use fallback pattern
# 3. Mark for manual review
# 4. Interactive mode: ask user
```

8.

### **Documentation Requirements:**

Create a comprehensive `manual-bibiliography-knowledge.md` file containing:

1. **Why Manual Bibliographies Exist**:
   * Journal requirements
   * Legacy document maintenance
   * Special formatting needs
   * Legal/archival requirements
2. **The Width Parameter Mystery**:
   * Full explanation of `\begin{thebibliography}{width}`
   * Common mistakes and misconceptions
   * How to choose correct width
   * Examples of problems from wrong width
3. **Author-Year Format Patterns**:
   * Complete specification
   * Edge cases and exceptions
   * International name handling
   * Organization naming conventions
4. **Common Failure Modes**:
   * Categorized list of what breaks
   * How to identify each type
   * Manual fix strategies
   * Prevention tips
5. **Integration with natbib**:
   * How `\bibitem[label]{key}` works
   * Interaction with `\citep` and `\citet`
   * Sorting considerations
   * Multiple citation handling
6. **Best Practices**:
   * When to use manual vs .bib files
   * Formatting guidelines
   * Version control considerations
   * Validation strategies
7. **Troubleshooting Guide**:
   * Error messages and meanings
   * Common fixes
   * When to give up and use .bib
   * Getting help

### **Command Line Interface:**

bash

```shell
# Basic usage
python scripts/fix-manual-biblio-to-authornames.py input.tex -o output.tex

# Fix width parameter too
python scripts/fix-manual-biblio-to-authornames.py input.tex \
    --fix-width \
    --in-place \
    --backup

# Interactive mode for ambiguous entries
python scripts/fix-manual-biblio-to-authornames.py input.tex \
    --interactive \
    --confidence-threshold 0.8

# Generate report only (no changes)
python scripts/fix-manual-biblio-to-authornames.py input.tex \
    --analyze-only \
    --report analysis.txt

# Batch processing with custom rules
python scripts/fix-manual-biblio-to-authornames.py *.tex \
    --config custom_rules.yaml \
    --parallel \
    --continue-on-error
```

### **Test Suite Requirements:**

python

```py
# Test categories:
# 1. Normal cases (80% of entries should be these)
# 2. Edge cases (15% - weird but handleable)
# 3. Pathological cases (5% - might need manual intervention)
# 4. Width parameter tests
# 5. Large file performance (1000+ entries)
# 6. Character encoding tests
# 7. Regression tests for each bug found
```

### **Success Metrics:**

1. **Accuracy**: 95%+ entries correctly converted on typical academic papers
2. **Speed**: Process 1000 entries in \< 1 second
3. **Robustness**: Never corrupt the input file
4. **Transparency**: Clear reporting of what was changed and why
5. **Recoverability**: Always able to undo changes

### **Fallback Strategy:**

When the script encounters truly ambiguous cases, it should:

1. Mark the entry with a comment: `% NEEDS_REVIEW: reason`
2. Attempt a best-guess conversion
3. Log to a review file
4. Optionally prompt for user input
5. Never silently fail

### **Example Problem Cases from Real Document:**

latex

```
# These actual cases need special attention:

\bibitem{given=PR, given-i=PR family=Newswire (2025)} \href{...}{...}
# Complex parsing needed

\bibitem{wang2024} \href{...}{Wang et al. (2024)} UAV-enabled...
# Already has "et al." - don't duplicate

\bibitem{httpsrerunio2025} \href{https://rerun.io/}{https://rerun.io/ (2025)} Rerun...
# URL as author

\bibitem{buildingsmart2025} \href{...}{buildingSMART (2025)} Learn IFC 5...
# Organization with unusual capitalization

# Entry with 607 should work with corrected width:
\bibitem{lastentry2025} \href{...}{Final Author (2025)} ...
# This is entry 607, needs {999} width parameter
```

### **Deliverables:**

1. Main script: `scripts/fix-manual-biblio-to-authornames.py`
2. Knowledge base: `manual-bibiliography-knowledge.md`
3. Test file: `scripts/test_fix_manual_biblio.py`
4. Sample files: `samples/input_bibliography.tex`, `samples/output_expected.tex`
5. Configuration template: `config/default_rules.yaml`
6. README.md with quick start guide
7. CHANGELOG.md for version tracking

Please create a well-architected, robust solution that handles all these cases gracefully, provides clear feedback to the user, and includes comprehensive documentation about the intricacies of manual bibliography handling in LaTeX. The code should be production-ready, maintainable, and include extensive comments explaining the reasoning behind complex parsing decisions.

---

This comprehensive prompt now includes extensive self-reflection on failure cases, proper explanation of the width parameter, and requests for institutional knowledge documentation that will help future users understand the complexities of manual bibliography handling.
