#!/usr/bin/env python3
"""
Deterministic Markdown to LaTeX Converter with Explicit Fallback Chain

This script provides a deterministic, reproducible conversion workflow with:
1. Explicit citation source fallbacks (MCP  RDF  JSON)
2. URL/DOI normalization for reliable matching
3. Citation key sanitization to prevent LaTeX compilation errors
4. Pre-indexed sources for deterministic behavior
5. Hash-based reproducibility verification
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.converters.md_to_latex.converter import MarkdownToLatexConverter


def normalize_identifier(url: str) -> str:
    """
    Normalize URLs and DOIs for reliable matching.

    Handles:
    - http vs https
    - Trailing slashes
    - URL encoding
    - DOI normalization
    - Case normalization
    """
    if not url:
        return ""

    url = url.strip()

    # DOI normalization
    url = url.replace("dx.doi.org", "doi.org")
    url = url.replace("http://doi.org", "https://doi.org")

    # Protocol normalization
    if url.startswith("http://"):
        url = url.replace("http://", "https://", 1)

    # Remove trailing slashes
    url = url.rstrip("/")

    # Case normalization for domains (but not paths)
    if "://" in url:
        protocol, rest = url.split("://", 1)
        if "/" in rest:
            domain, path = rest.split("/", 1)
            url = f"{protocol}://{domain.lower()}/{path}"
        else:
            url = f"{protocol}://{rest.lower()}"

    return url


def sanitize_citation_key(key: str) -> str:
    """
    Sanitize citation keys for LaTeX compatibility.

    Removes:
    - Control characters (like ^^?)
    - Non-ASCII characters
    - LaTeX special characters
    """
    if not key:
        return "unknownUnknown"

    # Remove control characters
    key = "".join(char for char in key if ord(char) >= 32)

    # Remove non-ASCII characters
    key = key.encode("ascii", errors="ignore").decode("ascii")

    # Remove LaTeX special characters
    key = key.replace("$", "")
    key = key.replace("{", "")
    key = key.replace("}", "")
    key = key.replace("\\", "")
    key = key.replace("^", "")
    key = key.replace("_", "")
    key = key.replace("%", "")
    key = key.replace("#", "")
    key = key.replace("&", "")
    key = key.replace("~", "")

    # Replace spaces with hyphens
    key = key.replace(" ", "-")

    # Ensure not empty after sanitization
    if not key:
        return "unknownUnknown"

    return key


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file for reproducibility verification."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def find_local_sources(markdown_path: Path) -> dict[str, Path]:
    """
    Find local citation sources based on markdown filename.

    Expected naming convention:
    - Input: {basename}.md
    - RDF: {basename}.rdf
    - JSON: {basename}.json
    """
    basename = markdown_path.stem
    directory = markdown_path.parent

    sources = {}

    # Check for RDF file
    rdf_path = directory / f"{basename}.rdf"
    if rdf_path.exists():
        sources["rdf"] = rdf_path

    # Check for CSL JSON file
    json_path = directory / f"{basename}.json"
    if json_path.exists():
        sources["json"] = json_path

    return sources


def convert_with_fallbacks(
    markdown_path: Path,
    output_dir: Path | None = None,
    mcp_server: str | None = None,
    rdf_path: Path | None = None,
    json_path: Path | None = None,
    verify_reproducibility: bool = True,
    allow_failures: bool = False,
) -> dict[str, Any]:
    """
    Convert markdown to LaTeX with explicit fallback chain.

    Fallback order:
    1. MCP server (if URL provided)
    2. Local RDF file (if path provided or auto-detected)
    3. Local CSL JSON file (if path provided or auto-detected)
    4. references.bib (last resort, likely to have failures)

    Returns:
        dict with conversion results and statistics
    """
    if not markdown_path.exists():
        return {
            "success": False,
            "error": f"Markdown file not found: {markdown_path}",
        }

    # Auto-detect local sources if not explicitly provided
    if not rdf_path and not json_path:
        auto_sources = find_local_sources(markdown_path)
        if "rdf" in auto_sources:
            rdf_path = auto_sources["rdf"]
        if "json" in auto_sources:
            json_path = auto_sources["json"]

    # Build source list in fallback order
    sources = []
    if mcp_server:
        sources.append({"type": "mcp", "location": mcp_server})
    if rdf_path and rdf_path.exists():
        sources.append({"type": "rdf", "location": str(rdf_path)})
    if json_path and json_path.exists():
        sources.append({"type": "json", "location": str(json_path)})

    # Set output directory
    if output_dir is None:
        output_dir = markdown_path.parent

    # EMERGENCY MODE - RDF ONLY (rdf_path is guaranteed to exist by argument parser)
    # Create converter with RDF source
    converter = MarkdownToLatexConverter(
        bibliography_rdf_file_path=rdf_path,  # RDF ONLY - .bib forbidden
        output_dir=output_dir,  # Pass output_dir to constructor
        allow_failures=allow_failures,  # Allow partial success
    )

    # Perform conversion
    try:
        converter.convert(
            markdown_file=markdown_path,
            # output_dir is set in constructor, not here
        )

        # Compute hashes for reproducibility verification
        tex_path = output_dir / f"{markdown_path.stem}.tex"
        bib_path = output_dir / "references.bib"

        result = {
            "success": True,
            "markdown_path": str(markdown_path),
            "output_dir": str(output_dir),
            "sources_used": sources,
            "files_generated": {
                "tex": str(tex_path) if tex_path.exists() else None,
                "bib": str(bib_path) if bib_path.exists() else None,
            },
        }

        if verify_reproducibility:
            result["hashes"] = {
                "tex": compute_file_hash(tex_path)
                if tex_path.exists()
                else None,
                "bib": compute_file_hash(bib_path)
                if bib_path.exists()
                else None,
            }

        return result

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "markdown_path": str(markdown_path),
            "sources_attempted": sources,
        }


def main():
    """Main entry point for deterministic conversion."""
    parser = argparse.ArgumentParser(
        description="Deterministic Markdown to LaTeX converter with explicit fallbacks"
    )

    parser.add_argument(
        "markdown_file",
        type=Path,
        help="Input markdown file to convert",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory (defaults to same as input file)",
    )

    parser.add_argument(
        "--rdf",
        type=Path,
        required=True,
        help="Local RDF file exported from Zotero (REQUIRED - this is emergency mode, RDF ONLY)",
    )

    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Disable reproducibility hash verification",
    )

    parser.add_argument(
        "--json-output",
        type=Path,
        help="Save conversion results as JSON to this file",
    )

    parser.add_argument(
        "--allow-failures",
        action="store_true",
        help="Continue conversion even if some citations fail to match",
    )

    args = parser.parse_args()

    # Verify RDF file exists
    if not args.rdf.exists():
        print(f"ERROR: RDF file not found: {args.rdf}")
        print("EMERGENCY MODE REQUIRES RDF FILE - export from Zotero as RDF")
        sys.exit(1)

    # Perform conversion (EMERGENCY MODE - RDF ONLY)
    result = convert_with_fallbacks(
        markdown_path=args.markdown_file,
        output_dir=args.output_dir,
        mcp_server=None,  # Emergency mode - no MCP
        rdf_path=args.rdf,  # RDF REQUIRED
        json_path=None,  # No JSON in emergency mode
        verify_reproducibility=not args.no_verify,
        allow_failures=args.allow_failures,
    )

    # Output results
    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

    # Print summary
    print("\n" + "=" * 80)
    print("DETERMINISTIC CONVERSION RESULTS")
    print("=" * 80)

    if result["success"]:
        print(" SUCCESS")
        print(f"\nInput: {result['markdown_path']}")
        print(f"Output: {result['output_dir']}")

        print("\nSources Used:")
        for source in result.get("sources_used", []):
            print(f"  - {source['type']}: {source['location']}")

        print("\nFiles Generated:")
        for file_type, path in result.get("files_generated", {}).items():
            if path:
                print(f"  - {file_type}: {path}")

        if "hashes" in result:
            print("\nReproducibility Hashes (SHA256):")
            for file_type, hash_val in result["hashes"].items():
                if hash_val:
                    print(f"  - {file_type}: {hash_val}")

        sys.exit(0)
    else:
        print(" FAILED")
        print(f"\nError: {result['error']}")
        print(f"Input: {result.get('markdown_path', 'unknown')}")

        if "sources_attempted" in result:
            print("\nSources Attempted:")
            for source in result["sources_attempted"]:
                print(f"  - {source['type']}: {source['location']}")

        sys.exit(1)


if __name__ == "__main__":
    main()
