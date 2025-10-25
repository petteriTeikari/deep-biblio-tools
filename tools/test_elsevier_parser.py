#!/usr/bin/env python3
"""Test the updated Elsevier parser on a local HTML file."""

from bs4 import BeautifulSoup
from scraper_standalone import ElsevierScraper

# Test the abstract extraction on a local file
test_file = "/home/petteri/Dropbox/LABs/KusiKasa/github/deep-biblio-tools/data/elsevier_manual_scrape/2D–3D fusion approach for improved point cloud segmentation - ScienceDirect.html"

# Create scraper instance
scraper = ElsevierScraper()

# Read the HTML file
with open(test_file, encoding="utf-8") as f:
    html_content = f.read()

# Parse with BeautifulSoup
soup = BeautifulSoup(html_content, "html.parser")


# Create a mock response object for testing
class MockResponse:
    def __init__(self, text):
        self.text = text


# Monkey patch the _make_request method to return our local content
original_make_request = scraper._make_request
scraper._make_request = lambda url: MockResponse(html_content)

# Test the get_paper_details method with actual file path
details = scraper.get_paper_details(test_file)

# Print results
print("Title:", details.get("title", "NOT FOUND"))
print(
    "\nAuthors:",
    ", ".join(details.get("authors", []))
    if details.get("authors")
    else "NOT FOUND",
)
print(
    "\nAbstract:",
    details.get("abstract", "NOT FOUND")[:200] + "..."
    if details.get("abstract")
    else "NOT FOUND",
)
print("\nDOI:", details.get("doi", "NOT FOUND"))
print("\nPublication Info:", details.get("publication_info", "NOT FOUND"))

# Check for images
if details.get("images"):
    print("\nImages found:", len(details["images"]))
    for img in details["images"]:
        print(f"  - Type: {img['type']}, Path: {img['path']}")
else:
    print("\nNo images found")

# Restore original method
scraper._make_request = original_make_request
