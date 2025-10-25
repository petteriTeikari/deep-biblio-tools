"""
Content classification utilities.

Classifies content as academic, layperson, press release, blog post, etc.
Helps identify non-academic sources that should be tagged appropriately.
"""

import logging
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ContentClassifier:
    """Classifier for determining content type and academic nature."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Define domain categories
        self.academic_domains = {
            "doi.org",
            "arxiv.org",
            "pubmed.ncbi.nlm.nih.gov",
            "ieee.org",
            "acm.org",
            "springer.com",
            "sciencedirect.com",
            "wiley.com",
            "nature.com",
            "science.org",
            "cambridge.org",
            "oxford.org",
            "oup.com",
            "tandfonline.com",
            "sagepub.com",
            "frontiersin.org",
            "mdpi.com",
            "plos.org",
            "jstor.org",
            "researchgate.net",
        }

        self.news_domains = {
            "bbc.com",
            "cnn.com",
            "reuters.com",
            "bloomberg.com",
            "wsj.com",
            "nytimes.com",
            "washingtonpost.com",
            "theguardian.com",
            "forbes.com",
            "techcrunch.com",
            "wired.com",
            "arstechnica.com",
        }

        self.university_domains = {
            ".edu",
            ".ac.uk",
            ".edu.au",
            ".ac.in",
            ".uni-",
            "university",
            "college",
            "institut",
        }

        self.government_domains = {
            ".gov",
            ".gov.uk",
            ".gov.au",
            ".europa.eu",
            "whitehouse.gov",
        }

        self.press_release_indicators = {
            "press-release",
            "news-release",
            "media-release",
            "announcement",
            "press-center",
            "newsroom",
            "media-center",
            "/news/",
            "/press/",
        }

    def classify_content(self, url: str) -> dict:
        """
        Classify content type from URL and page content.

        Args:
            url: URL to classify

        Returns:
            Dictionary with classification results
        """
        classification = {
            "url": url,
            "content_type": "unknown",
            "is_academic": False,
            "is_layperson": False,
            "is_press_release": False,
            "is_blog": False,
            "is_news": False,
            "confidence": 0.0,
            "tags": [],
        }

        # URL-based classification
        url_classification = self._classify_by_url(url)
        classification.update(url_classification)

        # If already classified with high confidence, return
        if classification["confidence"] > 0.8:
            return classification

        # Content-based classification
        try:
            content_classification = self._classify_by_content(url)
            if content_classification:
                # Merge classifications
                for key, value in content_classification.items():
                    if key in ["confidence"] and value > classification[key]:
                        classification[key] = value
                    elif key in [
                        "is_academic",
                        "is_layperson",
                        "is_press_release",
                        "is_blog",
                        "is_news",
                    ]:
                        classification[key] = classification[key] or value
                    elif key == "tags":
                        classification[key].extend(value)
                    elif (
                        key == "content_type"
                        and classification[key] == "unknown"
                    ):
                        classification[key] = value

        except Exception as e:
            logger.debug(f"Content-based classification failed for {url}: {e}")

        # Final classification logic
        classification = self._finalize_classification(classification)

        return classification

    def _classify_by_url(self, url: str) -> dict:
        """Classify content based on URL patterns."""
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc

            result = {
                "content_type": "unknown",
                "is_academic": False,
                "is_layperson": False,
                "is_press_release": False,
                "is_blog": False,
                "is_news": False,
                "confidence": 0.0,
                "tags": [],
            }

            # Check for academic domains
            if any(
                academic_domain in domain
                for academic_domain in self.academic_domains
            ):
                result["is_academic"] = True
                result["content_type"] = "academic"
                result["confidence"] = 0.9
                return result

            # Check for university domains
            if any(
                uni_pattern in domain for uni_pattern in self.university_domains
            ):
                result["is_academic"] = True
                result["content_type"] = "academic"
                result["confidence"] = 0.8
                return result

            # Check for news domains
            if any(news_domain in domain for news_domain in self.news_domains):
                result["is_news"] = True
                result["is_layperson"] = True
                result["content_type"] = "news"
                result["confidence"] = 0.8
                result["tags"].append("news")
                return result

            # Check for press release indicators
            if any(
                indicator in url.lower()
                for indicator in self.press_release_indicators
            ):
                result["is_press_release"] = True
                result["is_layperson"] = True
                result["content_type"] = "press_release"
                result["confidence"] = 0.9
                result["tags"].append("press_release")
                return result

            # Check for blog indicators
            blog_indicators = [
                "blog",
                "wordpress",
                "medium.com",
                "substack.com",
                "blogspot",
            ]
            if any(indicator in url.lower() for indicator in blog_indicators):
                result["is_blog"] = True
                result["is_layperson"] = True
                result["content_type"] = "blog"
                result["confidence"] = 0.7
                result["tags"].append("blog")
                return result

            # Check for government domains
            if any(
                gov_pattern in domain for gov_pattern in self.government_domains
            ):
                result["content_type"] = "government"
                result["confidence"] = 0.6
                return result

            # Check for PDF files (could be academic or reports)
            if url.lower().endswith(".pdf"):
                result["content_type"] = "pdf"
                result["confidence"] = 0.3  # Need content analysis
                return result

            return result

        except Exception as e:
            logger.debug(f"URL classification failed: {e}")
            return {"content_type": "unknown", "confidence": 0.0, "tags": []}

    def _classify_by_content(self, url: str) -> dict | None:
        """Classify content based on page content."""
        try:
            response = requests.get(
                url, headers=self.headers, timeout=self.timeout
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            result = {
                "content_type": "unknown",
                "is_academic": False,
                "is_layperson": False,
                "is_press_release": False,
                "is_blog": False,
                "is_news": False,
                "confidence": 0.0,
                "tags": [],
            }

            # Extract page text for analysis
            page_text = soup.get_text().lower()

            # Check for academic indicators
            academic_indicators = [
                "abstract",
                "doi:",
                "citation",
                "references",
                "methodology",
                "peer review",
                "journal",
                "arxiv",
                "pubmed",
                "research paper",
            ]
            academic_score = sum(
                1 for indicator in academic_indicators if indicator in page_text
            )

            # Check for press release indicators
            press_indicators = [
                "press release",
                "for immediate release",
                "media contact",
                "press contact",
                "news release",
                "announces",
                "company news",
            ]
            press_score = sum(
                1 for indicator in press_indicators if indicator in page_text
            )

            # Check for news indicators
            news_indicators = [
                "breaking news",
                "reporter",
                "published on",
                "news article",
                "updated:",
                "by staff",
                "correspondent",
            ]
            news_score = sum(
                1 for indicator in news_indicators if indicator in page_text
            )

            # Check for blog indicators
            blog_indicators = [
                "posted by",
                "blog post",
                "author:",
                "comments",
                "share this",
                "tags:",
                "categories:",
            ]
            blog_score = sum(
                1 for indicator in blog_indicators if indicator in page_text
            )

            # Check meta tags
            meta_description = soup.find("meta", attrs={"name": "description"})
            if meta_description:
                desc_text = meta_description.get("content", "").lower()
                if "press release" in desc_text:
                    press_score += 2
                if "news" in desc_text:
                    news_score += 1

            # Determine classification based on scores
            max_score = max(academic_score, press_score, news_score, blog_score)

            if academic_score == max_score and academic_score >= 3:
                result["is_academic"] = True
                result["content_type"] = "academic"
                result["confidence"] = min(0.8, 0.2 + academic_score * 0.1)
            elif press_score == max_score and press_score >= 2:
                result["is_press_release"] = True
                result["is_layperson"] = True
                result["content_type"] = "press_release"
                result["confidence"] = min(0.9, 0.5 + press_score * 0.1)
                result["tags"].append("press_release")
            elif news_score == max_score and news_score >= 2:
                result["is_news"] = True
                result["is_layperson"] = True
                result["content_type"] = "news"
                result["confidence"] = min(0.8, 0.4 + news_score * 0.1)
                result["tags"].append("news")
            elif blog_score == max_score and blog_score >= 2:
                result["is_blog"] = True
                result["is_layperson"] = True
                result["content_type"] = "blog"
                result["confidence"] = min(0.7, 0.3 + blog_score * 0.1)
                result["tags"].append("blog")

            return result

        except Exception as e:
            logger.debug(f"Content classification failed: {e}")
            return None

    def _finalize_classification(self, classification: dict) -> dict:
        """Finalize classification with additional logic."""
        # If it's not academic and has indicators of lay content, mark as layperson
        if not classification["is_academic"] and (
            classification["is_press_release"]
            or classification["is_news"]
            or classification["is_blog"]
        ):
            classification["is_layperson"] = True

        # If content type is still unknown but we have some indicators
        if classification["content_type"] == "unknown":
            if classification["is_layperson"]:
                classification["content_type"] = "layperson"
            elif classification["confidence"] < 0.3:
                classification["content_type"] = "uncertain"

        # Generate appropriate tags
        if classification["is_layperson"] and "LAY" not in [
            tag.upper() for tag in classification["tags"]
        ]:
            classification["tags"].append("LAY")

        return classification

    def is_layperson_content(self, url: str) -> tuple[bool, str]:
        """
        Quick check if content is layperson (non-academic).

        Args:
            url: URL to check

        Returns:
            Tuple of (is_layperson, reason)
        """
        classification = self.classify_content(url)

        if classification["is_layperson"]:
            if classification["is_press_release"]:
                return True, "press_release"
            elif classification["is_news"]:
                return True, "news"
            elif classification["is_blog"]:
                return True, "blog"
            else:
                return True, "layperson"

        return False, ""


def classify_url(url: str) -> dict:
    """
    Convenience function to classify a URL.

    Args:
        url: URL to classify

    Returns:
        Classification dictionary
    """
    classifier = ContentClassifier()
    return classifier.classify_content(url)


def is_layperson_url(url: str) -> tuple[bool, str]:
    """
    Quick check if URL points to layperson content.

    Args:
        url: URL to check

    Returns:
        Tuple of (is_layperson, content_type)
    """
    classifier = ContentClassifier()
    return classifier.is_layperson_content(url)
