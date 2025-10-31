#!/usr/bin/env python3
"""bib_sanitizer.py
----------------
Sanitize and validate .bib files before LaTeX/BibTeX compilation.

SAFETY-MODIFIED VERSION based on OpenAI feedback with:
- Emergency mode with RDF validation (HARD CRASH if file missing)
- Output list of citations not found in RDF (for manual assessment)
- FLAG duplicates, don't auto-merge (too risky)
- Exact organization matching (not fuzzy)
- Optional RapidFuzz dependency (fallback to difflib)

Usage:
    python bib_sanitizer.py references.bib --rdf zotero.rdf --emergency-mode
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any

# Optional RapidFuzz (faster), fallback to difflib
try:
    from rapidfuzz import fuzz

    HAS_RAPIDFUZZ = True
except ImportError:
    import difflib

    HAS_RAPIDFUZZ = False

import bibtexparser

# --------------------------------------------------------------------
# --- Configuration --------------------------------------------------
# --------------------------------------------------------------------

KNOWN_ORGS = [
    "European Commission",
    "Ellen MacArthur Foundation",
    "Fashion Revolution",
    "World Bank",
    "OECD",
    "United Nations",
    "NASA",
    "World Economic Forum",
    "European Parliament",
    "United Fashion",
    "Sigma Technology",
    "GS1",
    "ITC",
    "CIRPASS",
]

DOMAIN_PATTERN = re.compile(
    r"\b(?:[a-z0-9-]+\.)+(?:com|org|net|edu|gov|io|co|uk|de|fr|it|jp|cn)\b",
    re.I,
)

STUB_TITLE_PATTERNS = [
    r"^Web page by ",
    r"^Web article by ",
    r"^Web site by ",
    r"^Added from URL:",
]

LEGIT_SHORT_TITLES = {"Nature", "Science", "Cell", "PLOS", "Wired"}

# --------------------------------------------------------------------
# --- Helpers --------------------------------------------------------
# --------------------------------------------------------------------


def normalize_text(s: str) -> str:
    """Simplify for fuzzy comparison."""
    return re.sub(r"[\W_]+", " ", s or "").lower().strip()


def fuzzy_ratio(a: str, b: str) -> float:
    """Fuzzy string similarity (0-100)."""
    if HAS_RAPIDFUZZ:
        return fuzz.token_sort_ratio(a, b)
    else:
        # Fallback to difflib
        return difflib.SequenceMatcher(None, a, b).ratio() * 100


def is_domain_title(title: str) -> bool:
    """Detects when the title looks like a domain."""
    if not title:
        return False
    if title.strip() in LEGIT_SHORT_TITLES:
        return False
    return bool(DOMAIN_PATTERN.search(title))


def is_stub_title(title: str) -> bool:
    """Detects stub titles like 'Web page by X'."""
    if not title:
        return False
    for pattern in STUB_TITLE_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return True
    return False


def author_jaccard(a: str, b: str) -> float:
    """Jaccard similarity on last names."""

    def extract_lastnames(s):
        return {
            x.strip().split()[-1].lower()
            for x in re.split(r"[,;]| and ", s)
            if x.strip()
        }

    lastnames_a, lastnames_b = extract_lastnames(a), extract_lastnames(b)
    if not lastnames_a or not lastnames_b:
        return 0
    return len(lastnames_a & lastnames_b) / len(lastnames_a | lastnames_b)


def is_duplicate(a: dict[str, str], b: dict[str, str]) -> bool:
    """Check if two entries are likely duplicates (fuzzy match)."""
    title_score = fuzzy_ratio(
        normalize_text(a.get("title", "")), normalize_text(b.get("title", ""))
    )
    auth_overlap = author_jaccard(a.get("author", ""), b.get("author", ""))

    return title_score >= 92 and auth_overlap >= 0.8


def normalize_url(url: str) -> str:
    """Drop protocol, params, trailing slashes, www."""
    if not url:
        return ""

    # Remove protocol and www
    url = re.sub(r"^https?://(www\.)?", "", url)

    # Drop query/fragment
    url = re.sub(r"[?#].*$", "", url)

    # Remove trailing slashes
    url = url.rstrip("/")

    # Amazon-specific: normalize by ASIN/ISBN
    if "amazon." in url.lower():
        m = re.search(r"/dp/([A-Z0-9]{10})", url, re.I)
        if m:
            return f"amazon.com/dp/{m.group(1)}"

    # arXiv-specific: normalize by ID
    if "arxiv.org" in url.lower():
        m = re.search(
            r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5})", url, re.I
        )
        if m:
            return f"arxiv.org/abs/{m.group(1)}"

    return url.lower()


# --------------------------------------------------------------------
# --- RDF matching ---------------------------------------------------
# --------------------------------------------------------------------


def load_zotero_rdf(path: Path) -> list[dict[str, Any]]:
    """Simple RDF parser for Zotero RDF exports.

    Handles multiple URL/identifier formats:
    1. rdf:about attribute
    2. Nested dcterms:URI/rdf:value
    3. Simple dc:identifier text
    """
    try:
        text = path.read_text(encoding="utf8", errors="ignore")
    except Exception as e:
        raise RuntimeError(f"Failed to read RDF file: {e}")

    entries = []

    # Find all RDF items with resource URI
    pattern = r'<bib:(?:Book|Article|ArticleJournal|Webpage|Document)[^>]*rdf:about="([^"]*)"[^>]*>(.*?)</(?:bib:Book|bib:Article|bib:ArticleJournal|bib:Webpage|bib:Document)>'

    for match in re.finditer(pattern, text, re.DOTALL):
        rdf_about = match.group(1)  # Get rdf:about URL
        item = match.group(2)  # Get item content

        # Extract title
        title_match = re.search(r"<dc:title>([^<]+)</dc:title>", item)
        title = title_match.group(1).strip() if title_match else ""

        # Extract URL/identifier (try multiple formats)
        url = ""

        # 1. Try nested dcterms:URI/rdf:value structure (most common in Zotero)
        url_match = re.search(
            r"<dcterms:URI>\s*<rdf:value>([^<]+)</rdf:value>", item, re.DOTALL
        )
        if url_match:
            url = url_match.group(1).strip()

        # 2. Try simple dc:identifier
        if not url:
            url_match = re.search(
                r"<dc:identifier>([^<]+)</dc:identifier>", item
            )
            if url_match:
                identifier = url_match.group(1).strip()
                # Skip DOI-only format (like "DOI 10.1234/5678")
                if not identifier.startswith("DOI "):
                    url = identifier

        # 3. Fallback to rdf:about if it looks like a URL
        if not url and (
            rdf_about.startswith("http://") or rdf_about.startswith("https://")
        ):
            url = rdf_about

        # Extract author (may be in <dc:creator> or <bib:authors>)
        creator_match = re.search(
            r"<(?:dc:creator|bib:authors)>.*?<rdf:li>([^<]+)</rdf:li>",
            item,
            re.DOTALL,
        )
        author = creator_match.group(1).strip() if creator_match else ""

        # Extract year
        date_match = re.search(r"<dc:date>([^<]+)</dc:date>", item)
        year = date_match.group(1)[:4] if date_match else ""

        if url:  # Only add entries with URLs
            entries.append(
                {
                    "url": url,
                    "title": title,
                    "author": author,
                    "year": year,
                }
            )

    return entries


def find_in_rdf(
    url: str, rdf_entries: list[dict[str, Any]]
) -> dict[str, str] | None:
    """Find RDF entry by normalized URL."""
    if not url:
        return None

    norm_url = normalize_url(url)

    for entry in rdf_entries:
        entry_url = normalize_url(entry.get("url", ""))
        if entry_url == norm_url:
            return entry

    return None


# --------------------------------------------------------------------
# --- Sanitization ---------------------------------------------------
# --------------------------------------------------------------------


def double_brace_orgs(entry: dict[str, str]) -> dict[str, str]:
    """Wrap known organization names in double braces (exact match)."""
    author = entry.get("author", "")

    for org in KNOWN_ORGS:
        # Exact match with word boundaries, case-insensitive
        pattern = re.compile(r"\b" + re.escape(org) + r"\b", re.IGNORECASE)
        if pattern.search(author):
            # Replace with double-braced version
            author = pattern.sub(f"{{{{{org}}}}}", author)

    entry["author"] = author
    return entry


def ensure_arxiv(entry: dict[str, str]) -> dict[str, str]:
    """Ensure arXiv entries have eprint field."""
    content = " ".join(entry.get(k, "") for k in ["journal", "note", "url"])

    if "arxiv" in content.lower():
        if not entry.get("eprint"):
            # Try to extract from URL
            m = re.search(
                r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5})", content, re.I
            )
            if m:
                entry["eprint"] = m.group(1)
            else:
                entry["needs_manual_review"] = True

    return entry


def sanitize_entry(
    entry: dict[str, str], rdf_entries: list[dict[str, Any]]
) -> dict[str, Any]:
    """Sanitize a single BibTeX entry."""
    # Fix organization names
    entry = double_brace_orgs(entry)

    # Fix arXiv entries
    entry = ensure_arxiv(entry)

    # Check title quality
    title = entry.get("title", "").strip()
    url = entry.get("url", "").strip()

    # Domain-as-title or stub title
    if not title or is_domain_title(title) or is_stub_title(title):
        # Try to recover from RDF
        rdf_match = find_in_rdf(url, rdf_entries)
        if rdf_match:
            entry["title"] = rdf_match.get("title", title)
            entry["author"] = rdf_match.get("author", entry.get("author", ""))
            entry["year"] = rdf_match.get("year", entry.get("year", ""))
        else:
            # Flag for manual review
            entry["needs_manual_review"] = True

    return entry


# --------------------------------------------------------------------
# --- Main sanitize routine ------------------------------------------
# --------------------------------------------------------------------


def sanitize_bib(
    input_bib: Path,
    output_bib: Path,
    rdf_path: Path | None = None,
    emergency_mode: bool = False,
) -> dict[str, Any]:
    """
    Sanitize a .bib file before LaTeX compilation.

    Args:
        input_bib: Input .bib file
        output_bib: Output sanitized .bib file
        rdf_path: Optional Zotero RDF file for metadata recovery
        emergency_mode: If True, enforce strict RDF requirements

    Returns:
        Report dictionary with sanitization results
    """

    # EMERGENCY MODE: Validate RDF
    if emergency_mode:
        if not rdf_path:
            raise RuntimeError(
                "EMERGENCY MODE: RDF file path is REQUIRED.\n"
                "Use --rdf flag to provide local Zotero RDF export.\n"
                "Online fetching is DISABLED in emergency mode."
            )

        if not rdf_path.exists():
            raise FileNotFoundError(
                f"EMERGENCY MODE: RDF file not found at: {rdf_path}\n"
                f"Export from Zotero: File → Export Library → Zotero RDF"
            )

    # Load RDF entries
    if rdf_path and rdf_path.exists():
        rdf_entries = load_zotero_rdf(rdf_path)

        if emergency_mode and not rdf_entries:
            raise RuntimeError(
                f"EMERGENCY MODE: RDF file contains no entries: {rdf_path}\n"
                f"File exists but appears to be empty or corrupt."
            )
    else:
        rdf_entries = []

    # Parse input .bib file
    parser = bibtexparser.bparser.BibTexParser(common_strings=True)
    with open(input_bib, encoding="utf8") as f:
        bib_data = bibtexparser.load(f, parser=parser)

    # Initialize report
    report = {
        "fixed_orgs": 0,
        "fixed_arxiv": 0,
        "domain_titles": 0,
        "stub_titles": 0,
        "manual_review": [],
        "duplicates": [],
        "not_found_in_rdf": [],
    }

    # Sanitize each entry
    sanitized = []
    for entry in bib_data.entries:
        original = entry.copy()
        entry = sanitize_entry(entry, rdf_entries)

        # Track changes
        if entry.get("needs_manual_review"):
            report["manual_review"].append(entry.get("ID"))

        if entry.get("eprint") and not original.get("eprint"):
            report["fixed_arxiv"] += 1

        if any(
            f"{{{{{org}}}}}" in entry.get("author", "") for org in KNOWN_ORGS
        ):
            report["fixed_orgs"] += 1

        if is_domain_title(original.get("title", "")):
            report["domain_titles"] += 1

        if is_stub_title(original.get("title", "")):
            report["stub_titles"] += 1

        sanitized.append(entry)

    # Detect duplicates (FLAG only, don't merge)
    seen = set()
    for i, a in enumerate(sanitized):
        for j, b in enumerate(sanitized):
            if j <= i:
                continue
            if is_duplicate(a, b):
                keypair = tuple(sorted((a["ID"], b["ID"])))
                if keypair not in seen:
                    seen.add(keypair)
                    report["duplicates"].append(
                        {
                            "a": a["ID"],
                            "b": b["ID"],
                            "title_a": a.get("title", ""),
                            "title_b": b.get("title", ""),
                            "action": "MANUAL_REVIEW_REQUIRED",
                        }
                    )

    # Check for citations not in RDF (EMERGENCY MODE)
    if emergency_mode and rdf_entries:
        for entry in sanitized:
            url = entry.get("url", "").strip()
            if url:
                match = find_in_rdf(url, rdf_entries)
                if not match:
                    report["not_found_in_rdf"].append(
                        {
                            "key": entry["ID"],
                            "url": url,
                            "normalized_url": normalize_url(url),
                            "title": entry.get("title", "Unknown"),
                        }
                    )

    # Output list of missing citations (if any)
    if report["not_found_in_rdf"]:
        print("\n" + "=" * 70)
        print(
            f"=== Citations NOT found in RDF ({len(report['not_found_in_rdf'])} total) ==="
        )
        print("=" * 70)
        for item in report["not_found_in_rdf"]:
            print(f"\nKey: {item['key']}")
            print(f"  Title: {item['title']}")
            print(f"  URL: {item['url']}")
            print(f"  Normalized: {item['normalized_url']}")

        print("\n" + "=" * 70)
        print("MANUAL REVIEW REQUIRED:")
        print("  1. Check if URL matching is broken (normalization issue)")
        print("  2. Or if these genuinely need to be added to Zotero")
        print("=" * 70)

        if len(report["not_found_in_rdf"]) > 5:
            print(
                f"\n⚠️  WARNING: More than 5 missing ({len(report['not_found_in_rdf'])})"
            )
            print(
                "    This likely indicates a URL matching bug, not missing data."
            )
            print(
                "    Expected: Maximum 5 missing citations in emergency mode.\n"
            )

    # Clean entries before writing (remove internal flags)
    for entry in sanitized:
        # Remove internal tracking fields
        entry.pop("needs_manual_review", None)

    # Write sanitized file
    bib_data.entries = sanitized
    with open(output_bib, "w", encoding="utf8") as f:
        bibtexparser.dump(bib_data, f)

    return report


# --------------------------------------------------------------------
# --- CLI -------------------------------------------------------------
# --------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sanitize a .bib file before LaTeX compilation"
    )
    parser.add_argument("bibfile", type=Path, help="Input .bib file")
    parser.add_argument(
        "--rdf", type=Path, help="Zotero RDF file (required in emergency mode)"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("references.clean.bib"),
        help="Output sanitized file",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("bib_sanitizer_report.json"),
        help="Report JSON file",
    )
    parser.add_argument(
        "--emergency-mode",
        action="store_true",
        help="Enable emergency mode (strict RDF validation, no web fetching)",
    )

    args = parser.parse_args()

    try:
        report = sanitize_bib(
            args.bibfile, args.out, args.rdf, args.emergency_mode
        )

        # Write report
        with open(args.report, "w", encoding="utf8") as f:
            json.dump(report, f, indent=2)

        print(f"\n✅ Sanitized .bib written to {args.out}")
        print(f"✅ Report written to {args.report}")

        if report["manual_review"]:
            print(
                f"\n⚠️  Manual review needed for {len(report['manual_review'])} entries:"
            )
            for key in report["manual_review"][:10]:  # Show first 10
                print(f"    - {key}")

        if report["duplicates"]:
            print(
                f"\n⚠️  Found {len(report['duplicates'])} potential duplicates:"
            )
            for dup in report["duplicates"][:5]:  # Show first 5
                print(f"    - {dup['a']} vs {dup['b']}")

    except (RuntimeError, FileNotFoundError) as e:
        print(f"\n❌ ERROR: {e}")
        exit(1)
