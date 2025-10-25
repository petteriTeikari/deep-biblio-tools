#!/usr/bin/env python3
"""
Analyze the scraped papers to provide insights about BIM/scan-to-BIM research.
"""

import argparse
import json
from collections import Counter


def analyze_papers(json_file: str):
    """Analyze scraped papers for trends and insights."""
    with open(json_file) as f:
        papers = json.load(f)

    print(f"Total papers analyzed: {len(papers)}\n")

    # Extract years
    years = [p.get("year") for p in papers if p.get("year")]
    year_counts = Counter(years)

    print("Papers by year:")
    for year in sorted(year_counts.keys(), reverse=True):
        print(f"  {year}: {year_counts[year]} papers")

    # Analyze keywords
    all_keywords = []
    for paper in papers:
        all_keywords.extend(paper.get("keywords", []))

    keyword_counts = Counter(all_keywords)
    print("\nTop 20 keywords:")
    for keyword, count in keyword_counts.most_common(20):
        print(f"  {keyword}: {count}")

    # BIM-related papers
    bim_papers = [
        p
        for p in papers
        if "BIM" in p.get("title", "")
        or any("BIM" in kw for kw in p.get("keywords", []))
    ]
    print(
        f"\nBIM-related papers: {len(bim_papers)} ({len(bim_papers) / len(papers) * 100:.1f}%)"
    )

    # Scan-to-BIM papers
    scan_bim_papers = [
        p
        for p in papers
        if "scan" in p.get("title", "").lower() and "BIM" in p.get("title", "")
    ]
    print(f"Scan-to-BIM papers: {len(scan_bim_papers)}")

    # Point cloud papers
    point_cloud_papers = [
        p
        for p in papers
        if "point cloud" in p.get("title", "").lower()
        or any("point cloud" in kw.lower() for kw in p.get("keywords", []))
    ]
    print(f"Point cloud papers: {len(point_cloud_papers)}")

    # Deep learning papers
    dl_papers = [
        p
        for p in papers
        if any(
            term in p.get("title", "").lower()
            for term in ["deep learning", "neural", "AI", "machine learning"]
        )
    ]
    print(f"AI/Deep learning papers: {len(dl_papers)}")

    # Robot papers
    robot_papers = [p for p in papers if "robot" in p.get("title", "").lower()]
    print(f"Robotics papers: {len(robot_papers)}")

    # UAV/Drone papers
    uav_papers = [
        p
        for p in papers
        if any(term in p.get("title", "").lower() for term in ["uav", "drone"])
    ]
    print(f"UAV/Drone papers: {len(uav_papers)}")

    # Digital twin papers
    dt_papers = [
        p for p in papers if "digital twin" in p.get("title", "").lower()
    ]
    print(f"Digital twin papers: {len(dt_papers)}")

    # Author analysis
    all_authors = []
    for paper in papers:
        all_authors.extend(paper.get("authors", []))

    author_counts = Counter(all_authors)
    print("\n\nTop 10 most prolific authors:")
    for author, count in author_counts.most_common(10):
        print(f"  {author}: {count} papers")

    # Papers with abstracts
    with_abstracts = [p for p in papers if p.get("abstract")]
    print(
        f"\n\nPapers with abstracts: {len(with_abstracts)} ({len(with_abstracts) / len(papers) * 100:.1f}%)"
    )

    # Average abstract length
    if with_abstracts:
        avg_abstract_len = sum(
            len(p["abstract"]) for p in with_abstracts
        ) / len(with_abstracts)
        print(f"Average abstract length: {avg_abstract_len:.0f} characters")

    # Print scan-to-BIM paper titles
    if scan_bim_papers:
        print("\n\nScan-to-BIM paper titles:")
        for i, paper in enumerate(scan_bim_papers, 1):
            print(f"{i}. {paper['title']}")


def main():
    parser = argparse.ArgumentParser(description="Analyze scraped papers")
    parser.add_argument("json_file", help="JSON file with scraped papers")
    args = parser.parse_args()

    analyze_papers(args.json_file)


if __name__ == "__main__":
    main()
