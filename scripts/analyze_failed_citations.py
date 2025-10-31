#!/usr/bin/env python3
"""
Analyze Failed Citations from Conversion Log

This script categorizes all failed citations from a conversion log into:
- Academic sources (should be in Zotero)
- Web sources (should be footnotes)
- Broken URLs (should be fixed/removed)

Usage:
    python scripts/analyze_failed_citations.py /tmp/final_conversion.log --output failed-analysis.json
"""

import sys
import re
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, List
import json


class FailedCitationAnalyzer:
    """Analyzes failed citations and categorizes them."""

    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.failed_urls = []
        self.categorized = {
            "academic_journal": [],
            "academic_conference": [],
            "academic_preprint": [],
            "academic_book": [],
            "web_organization": [],
            "web_blog": [],
            "web_news": [],
            "web_video": [],
            "web_documentation": [],
            "web_government": [],
            "web_general": []
        }

    def extract_failed_urls(self):
        """Extract all failed URLs from conversion log."""
        pattern = r"Citation not found in Zotero collection: (https?://[^\s]+)"
        with open(self.log_file) as f:
            for line in f:
                match = re.search(pattern, line)
                if match:
                    url = match.group(1)
                    if url not in self.failed_urls:
                        self.failed_urls.append(url)

    def categorize_url(self, url: str) -> str:
        """Categorize a URL into citation type."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()

        # Academic sources (should be in Zotero)
        if "doi.org" in domain:
            return "academic_journal"
        if "arxiv.org" in domain:
            return "academic_preprint"
        if "biorxiv.org" in domain or "medrxiv.org" in domain:
            return "academic_preprint"
        if "ssrn.com" in domain:
            return "academic_preprint"
        if "amazon" in domain and ("/dp/" in path or "/gp/product/" in path):
            return "academic_book"
        if "oreilly.com" in domain and "/library/" in path:
            return "academic_book"
        if "springer.com" in domain or "ieeexplore.ieee.org" in domain:
            return "academic_conference"
        if "acm.org" in domain and "/doi/" in path:
            return "academic_conference"
        if "openreview.net" in domain:
            return "academic_preprint"
        if "proceedings.mlr.press" in domain:
            return "academic_conference"
        if "aclanthology.org" in domain:
            return "academic_conference"

        # Government/EU/Standards organizations
        if any(x in domain for x in ["europa.eu", "europarl.europa.eu", "eur-lex.europa.eu"]):
            return "web_government"
        if "oecd.org" in domain:
            return "web_organization"
        if "nist.gov" in domain:
            return "web_government"
        if any(x in domain for x in ["fda.gov", "sec.gov", "epa.gov"]):
            return "web_government"
        if "commission.europa.eu" in domain:
            return "web_government"
        if "federalregister.gov" in domain:
            return "web_government"

        # Industry organizations/standards bodies
        if any(x in domain for x in ["wbcsd.org", "gs1", "standardsmap.org"]):
            return "web_organization"
        if "ellenmacarthurfoundation.org" in domain:
            return "web_organization"
        if "spec-untp" in domain or "un/" in domain:
            return "web_organization"

        # Tech company blogs/documentation
        if any(x in domain for x in ["anthropic.com", "openai.com", "deepmind.com"]):
            return "web_blog"
        if "developers.google" in domain or "googleblog.com" in domain:
            return "web_documentation"
        if "modelcontextprotocol.io" in domain:
            return "web_documentation"
        if any(x in domain for x in ["developer.okta.com", "docs.github.com", "developer.mozilla.org"]):
            return "web_documentation"

        # News/media
        if any(x in domain for x in ["bbc.com", "bloomberg.com", "axios.com", "reuters.com"]):
            return "web_news"
        if "fashionunited.com" in domain:
            return "web_news"
        if "darkreading.com" in domain:
            return "web_news"
        if "venturebeat.com" in domain:
            return "web_news"

        # Video
        if "youtube.com" in domain or "vimeo.com" in domain:
            return "web_video"

        # Company/project pages
        if any(x in domain for x in ["fibretrace.io", "circularise.com", "cirpassproject.eu"]):
            return "web_organization"
        if "hmfoundation.com" in domain:
            return "web_organization"
        if "fashionrevolution.org" in domain:
            return "web_organization"
        if "asiagarmenthub.net" in domain:
            return "web_organization"
        if "bhr.stern.nyu.edu" in domain:
            return "web_organization"

        # Technical/research platforms
        if "researchgate.net" in domain:
            return "academic_preprint"
        if "interpret.ml" in domain or "github.com" in domain:
            return "web_documentation"

        # Company websites
        if any(x in domain for x in ["ibm.com", "amazon.de", "rigaku.com", "sigmatechnology.com"]):
            return "web_organization"

        # Default
        return "web_general"

    def categorize_all(self):
        """Categorize all failed URLs."""
        for url in self.failed_urls:
            category = self.categorize_url(url)
            self.categorized[category].append(url)

    def generate_report(self) -> Dict:
        """Generate categorized report with recommendations."""
        report = {
            "summary": {
                "total_failed": len(self.failed_urls),
                "academic_sources": 0,
                "web_sources": 0
            },
            "categories": {},
            "recommendations": {
                "add_to_zotero": [],
                "convert_to_footnote": [],
                "review_required": []
            }
        }

        # Count by category
        for category, urls in self.categorized.items():
            if urls:
                report["categories"][category] = {
                    "count": len(urls),
                    "urls": urls
                }

                # Academic sources should be added to Zotero
                if category.startswith("academic_"):
                    report["summary"]["academic_sources"] += len(urls)
                    for url in urls:
                        report["recommendations"]["add_to_zotero"].append({
                            "url": url,
                            "type": category,
                            "action": "Add to Zotero manually"
                        })

                # Web sources should be footnotes
                elif category.startswith("web_"):
                    report["summary"]["web_sources"] += len(urls)
                    for url in urls:
                        report["recommendations"]["convert_to_footnote"].append({
                            "url": url,
                            "type": category,
                            "action": "Convert to footnote (not bibliography)"
                        })

        return report

    def save_report(self, output_path: Path):
        """Save report to JSON file."""
        report = self.generate_report()
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        return report


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_failed_citations.py <conversion.log> [--output report.json]")
        sys.exit(1)

    log_file = Path(sys.argv[1])
    output_file = Path("failed-citations-analysis.json")

    if "--output" in sys.argv:
        output_file = Path(sys.argv[sys.argv.index("--output") + 1])

    if not log_file.exists():
        print(f"ERROR: Log file not found: {log_file}")
        sys.exit(1)

    print(f"Analyzing failed citations from: {log_file}")
    analyzer = FailedCitationAnalyzer(log_file)

    print("Extracting failed URLs...")
    analyzer.extract_failed_urls()
    print(f"  Found {len(analyzer.failed_urls)} unique failed citations")

    print("Categorizing URLs...")
    analyzer.categorize_all()

    print("Generating report...")
    report = analyzer.save_report(output_file)

    print(f"\n{'='*80}")
    print("FAILED CITATIONS ANALYSIS")
    print(f"{'='*80}")
    print(f"Total Failed: {report['summary']['total_failed']}")
    print(f"  Academic Sources (add to Zotero): {report['summary']['academic_sources']}")
    print(f"  Web Sources (convert to footnotes): {report['summary']['web_sources']}")
    print()
    print("Categories:")
    for category, data in report["categories"].items():
        print(f"  {category}: {data['count']}")
    print()
    print(f"Report saved to: {output_file}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
