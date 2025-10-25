#!/usr/bin/env python3
"""Generate comprehensive missing citations report with context."""

import re
import sys
from pathlib import Path

# Add module to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from deep_biblio.arxiv_converter import ZoteroCitationMatcher

# Paths
MANUSCRIPT_PATH = "/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/paper-manuscripts/mcp-review/mcp-draft-refined-v3.md"
ZOTERO_JSON_PATH = "/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/paper-manuscripts/mcp-review/dpp-fashion.json"
OUTPUT_FILE = "/Users/petteri/Dropbox/LABs/open-mode/github/dpp-fashion/mcp-servers/deep-biblio/missing-citations-report.md"

print("Generating missing citations report with context...\n")

# Load matcher and extract citations
matcher = ZoteroCitationMatcher(ZOTERO_JSON_PATH)
citations = matcher.extract_citations_from_markdown(MANUSCRIPT_PATH)

# Load manuscript content
manuscript = Path(MANUSCRIPT_PATH).read_text(encoding="utf-8")
lines = manuscript.split("\n")

# Find missing citations with context
missing_with_context = []

for cite in citations:
    entry = matcher.match_citation(cite)
    if not entry:  # Missing!
        line_idx = cite["line_number"] - 1

        # Get context: the full sentence containing the citation
        # Go backwards to find sentence start
        sentence_start = line_idx
        for i in range(line_idx, max(0, line_idx - 5), -1):
            line = lines[i]
            # Look for sentence boundaries
            if re.search(r"[.!?]\s*$", line) and i < line_idx:
                sentence_start = i + 1
                break
            if i == max(0, line_idx - 5):
                sentence_start = i

        # Go forwards to find sentence end
        sentence_end = line_idx
        for i in range(line_idx, min(len(lines), line_idx + 5)):
            line = lines[i]
            # Look for sentence boundaries
            if re.search(r"[.!?]\s*$", line):
                sentence_end = i
                break
            if i == min(len(lines) - 1, line_idx + 5):
                sentence_end = i

        # Extract context
        context_lines = lines[sentence_start : sentence_end + 1]
        context = " ".join(line.strip() for line in context_lines if line.strip())

        # Truncate if too long
        if len(context) > 500:
            context = context[:500] + "..."

        missing_with_context.append(
            {
                "author": cite["author"],
                "year": cite["year"],
                "url": cite["url"],
                "line": cite["line_number"],
                "context": context,
                "original": cite["original"],
            }
        )

# Sort by line number
missing_with_context.sort(key=lambda x: x["line"])

# Generate report
report = []
report.append("# Missing Citations Report")
report.append(f"\n**Manuscript**: {Path(MANUSCRIPT_PATH).name}")
report.append(f"**Total citations**: {len(citations)}")
report.append(f"**Missing from Zotero**: {len(missing_with_context)}")
report.append(
    f"**Match rate**: {(len(citations) - len(missing_with_context)) / len(citations) * 100:.1f}%"
)
report.append("\n---\n")
report.append("## Missing Citations (Clickable URLs)\n")
report.append(
    "**Instructions**: Click each URL to verify it's correct, then add to Zotero.\n"
)

# Group by unique URL to remove duplicates
url_to_cites = {}
for cite in missing_with_context:
    url = cite["url"]
    if url not in url_to_cites:
        url_to_cites[url] = []
    url_to_cites[url].append(cite)

# Generate report
for i, (url, cites) in enumerate(
    sorted(url_to_cites.items(), key=lambda x: x[1][0]["line"]), 1
):
    first_cite = cites[0]

    report.append(f"### {i}. {first_cite['author']}, {first_cite['year']}")
    report.append(f"\n**URL**: <{url}>")

    # Show how many times this citation appears
    if len(cites) > 1:
        report.append(
            f"\n**Appears**: {len(cites)} times (lines: {', '.join(str(c['line']) for c in cites)})"
        )
    else:
        report.append(f"\n**Line**: {first_cite['line']}")

    report.append("\n**Context**:")
    report.append(f"> {first_cite['context']}")

    # Suggest what type of source this might be
    if "doi.org" in url:
        report.append("\n[FILE] *Type: Journal article (DOI)*")
    elif "arxiv.org" in url:
        report.append("\n[FILE] *Type: arXiv preprint*")
    elif any(x in url.lower() for x in ["europa.eu", "commission.europa"]):
        report.append("\n *Type: EU official document*")
    elif any(x in url.lower() for x in ["github.com"]):
        report.append("\n[CODE] *Type: Software/code repository*")
    elif any(x in url.lower() for x in [".pdf"]):
        report.append("\n *Type: PDF document*")
    elif any(x in url.lower() for x in ["springer", "ieee", "acm"]):
        report.append("\n[FILE] *Type: Conference/journal article*")
    else:
        report.append("\n[GLOBAL] *Type: Website/webpage*")

    report.append("\n")

report.append("\n---\n")
report.append("## Summary by Type\n")

# Count by type
types = {
    "DOI (Journal/Conference)": 0,
    "arXiv preprints": 0,
    "EU/Official documents": 0,
    "Websites/Webpages": 0,
    "PDF documents": 0,
    "Other": 0,
}

for url in url_to_cites.keys():
    if "doi.org" in url or any(x in url.lower() for x in ["springer", "ieee", "acm"]):
        types["DOI (Journal/Conference)"] += 1
    elif "arxiv.org" in url:
        types["arXiv preprints"] += 1
    elif any(x in url.lower() for x in ["europa.eu", "commission.europa", ".gov"]):
        types["EU/Official documents"] += 1
    elif ".pdf" in url.lower():
        types["PDF documents"] += 1
    elif any(x in url.lower() for x in ["http://", "https://"]):
        types["Websites/Webpages"] += 1
    else:
        types["Other"] += 1

for type_name, count in types.items():
    if count > 0:
        report.append(f"- **{type_name}**: {count}")

report.append("\n---\n")
report.append("\n*Report generated by deep-biblio MCP server*")

# Write report
output_path = Path(OUTPUT_FILE)
output_path.write_text("\n".join(report), encoding="utf-8")

print(f"[PASS] Report generated: {output_path}")
print("\n[STATS] Statistics:")
print(f"  - Unique missing citations: {len(url_to_cites)}")
print(f"  - Total missing occurrences: {len(missing_with_context)}")
print(f"  - DOI articles: {types['DOI (Journal/Conference)']}")
print(f"  - arXiv preprints: {types['arXiv preprints']}")
print(f"  - EU/Official docs: {types['EU/Official documents']}")
print(f"  - Websites: {types['Websites/Webpages']}")
print(f"  - PDF documents: {types['PDF documents']}")
print("\n[INFO] Open the report in your editor to click the URLs!")
