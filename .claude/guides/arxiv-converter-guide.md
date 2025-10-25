# Complete Implementation Guide: Markdown to arXiv LaTeX Converter

## Overview
This guide provides a comprehensive implementation for converting academic markdown documents to arXiv-ready LaTeX, with sophisticated citation management, beautiful concept boxes, and full Zotero integration.

## Environment Setup

### 1. Create `.env` File
```bash
# Zotero Configuration
ZOTERO_LIBRARY_ID=your_library_id_here
ZOTERO_LIBRARY_TYPE=user  # or 'group'
ZOTERO_API_KEY=your_api_key_here

# Optional API Keys for Enhanced Citation Fetching
SERPAPI_KEY=your_serpapi_key  # For Google Scholar
SEMANTIC_SCHOLAR_API_KEY=your_key  # Optional, but recommended
CORE_API_KEY=your_core_api_key  # For CORE academic search

# OpenAlex Configuration (free, no key needed but can add email)
OPENALEX_EMAIL=your_email@example.com
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Requirements.txt
```
pypandoc>=1.11
bibtexparser>=1.4.0
pyzotero>=1.5.0
requests>=2.28.0
beautifulsoup4>=4.11.0
lxml>=4.9.0
python-dotenv>=1.0.0
scholarly>=1.7.0
habanero>=1.2.0  # For CrossRef
pyalex>=0.10  # For OpenAlex
semanticscholar>=0.5.0
colorama>=0.4.6  # For colored terminal output
tqdm>=4.65.0  # For progress bars
```

## Complete Implementation Code

```python
#!/usr/bin/env python3
"""
Enhanced Markdown to LaTeX Converter for arXiv Submission
With sophisticated citation fetching and beautiful concept boxes
"""

import re
import os
import json
import requests
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import logging
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse, quote
import hashlib

# Third-party imports
from dotenv import load_dotenv
import pypandoc
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
from bs4 import BeautifulSoup
from tqdm import tqdm
from colorama import init, Fore, Style

# Citation fetching libraries
from pyzotero import zotero
from habanero import Crossref
from scholarly import scholarly
from semanticscholar import SemanticScholar
import pyalex
from pyalex import Works, Authors

# Initialize colorama for colored output
init(autoreset=True)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """Enhanced citation with multiple metadata fields"""
    text: str
    url: str
    year: str
    authors: List[str]
    key: str
    title: str = ""
    journal: str = ""
    volume: str = ""
    pages: str = ""
    doi: str = ""
    isbn: str = ""
    publisher: str = ""
    bibtex: Optional[str] = None
    source: str = "unknown"  # Where we found it
    confidence: float = 0.0  # Confidence in the match
    entry_type: str = "article"  # article, book, inproceedings, etc.


@dataclass
class ConceptBoxStyle:
    """Defines a concept box style"""
    name: str
    color_scheme: Dict[str, str]
    settings: Dict[str, Any]
    latex_code: str


class CitationFetcher:
    """Handles fetching citations from multiple sources"""

    def __init__(self):
        self.crossref = Crossref()
        self.semantic_scholar = SemanticScholar()
        self.cache_dir = Path(".citation_cache")
        self.cache_dir.mkdir(exist_ok=True)

        # Set up OpenAlex with email if provided
        if email := os.getenv('OPENALEX_EMAIL'):
            pyalex.config.email = email

    def fetch_citation(self, citation: Citation) -> Citation:
        """Try multiple sources to fetch complete citation data"""
        # Check cache first
        cache_key = hashlib.md5(f"{citation.text}{citation.url}".encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            logger.info(f"Using cached citation for {citation.key}")
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
                for key, value in cached_data.items():
                    setattr(citation, key, value)
                return citation

        # Try different sources based on URL
        if 'doi.org' in citation.url:
            citation = self.fetch_from_doi(citation)
        elif 'arxiv.org' in citation.url:
            citation = self.fetch_from_arxiv(citation)
        elif 'amazon.com' in citation.url or 'book' in citation.text.lower():
            citation = self.fetch_book(citation)
        else:
            # Try multiple academic sources
            citation = self.fetch_from_multiple_sources(citation)

        # Cache the result
        self.cache_citation(citation, cache_file)

        return citation

    def fetch_from_doi(self, citation: Citation) -> Citation:
        """Fetch from DOI using CrossRef"""
        try:
            doi = citation.url.split('doi.org/')[-1]
            work = self.crossref.works(ids=doi)
            if work and 'message' in work:
                msg = work['message']
                citation.title = msg.get('title', [''])[0]
                citation.journal = msg.get('container-title', [''])[0]
                citation.volume = str(msg.get('volume', ''))
                citation.pages = msg.get('page', '')
                citation.doi = doi
                citation.source = "crossref"
                citation.confidence = 1.0

                # Generate proper BibTeX
                citation.bibtex = self.generate_bibtex_from_crossref(msg, citation.key)

        except Exception as e:
            logger.warning(f"CrossRef fetch failed for {doi}: {e}")

        return citation

    def fetch_from_arxiv(self, citation: Citation) -> Citation:
        """Enhanced arXiv fetching"""
        try:
            arxiv_id = re.search(r'(\d{4}\.\d{4,5})', citation.url)
            if not arxiv_id:
                return citation

            arxiv_id = arxiv_id.group(1)

            # Use arXiv API
            url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
            response = requests.get(url)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'xml')
                entry = soup.find('entry')

                if entry:
                    citation.title = entry.find('title').text.strip()
                    citation.authors = [author.find('name').text for author in entry.find_all('author')]
                    citation.year = entry.find('published').text[:4]
                    citation.journal = f"arXiv preprint arXiv:{arxiv_id}"
                    citation.source = "arxiv"
                    citation.confidence = 1.0
                    citation.entry_type = "article"

                    # Check if published elsewhere
                    doi_elem = entry.find('arxiv:doi')
                    if doi_elem:
                        citation.doi = doi_elem.text
                        citation.journal = entry.find('arxiv:journal_ref').text if entry.find('arxiv:journal_ref') else citation.journal

                    citation.bibtex = self.generate_bibtex(citation)

        except Exception as e:
            logger.warning(f"arXiv fetch failed: {e}")

        return citation

    def fetch_book(self, citation: Citation) -> Citation:
        """Fetch book information from multiple sources"""
        # Try OpenLibrary first
        citation = self.fetch_from_openlibrary(citation)

        # If not found, try Google Books
        if citation.confidence < 0.8:
            citation = self.fetch_from_google_books(citation)

        # Set entry type
        citation.entry_type = "book"

        return citation

    def fetch_from_openlibrary(self, citation: Citation) -> Citation:
        """Fetch from OpenLibrary API"""
        try:
            # Search by title and author
            search_query = f"{citation.text.replace(f'({citation.year})', '').strip()}"
            url = f"https://openlibrary.org/search.json?q={quote(search_query)}&limit=5"

            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data['docs']:
                    # Find best match
                    best_match = self.find_best_book_match(data['docs'], citation)
                    if best_match:
                        citation.title = best_match.get('title', '')
                        citation.authors = best_match.get('author_name', [])
                        citation.publisher = ', '.join(best_match.get('publisher', []))
                        citation.year = str(best_match.get('first_publish_year', citation.year))
                        if isbn := best_match.get('isbn', []):
                            citation.isbn = isbn[0]
                        citation.source = "openlibrary"
                        citation.confidence = 0.8

        except Exception as e:
            logger.warning(f"OpenLibrary fetch failed: {e}")

        return citation

    def fetch_from_google_books(self, citation: Citation) -> Citation:
        """Fetch from Google Books API"""
        try:
            search_query = citation.text.replace(f'({citation.year})', '').strip()
            url = f"https://www.googleapis.com/books/v1/volumes?q={quote(search_query)}"

            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if 'items' in data and data['items']:
                    book = data['items'][0]['volumeInfo']
                    citation.title = book.get('title', '')
                    citation.authors = book.get('authors', [])
                    citation.publisher = book.get('publisher', '')
                    citation.year = book.get('publishedDate', citation.year)[:4]

                    # Get ISBN
                    for identifier in book.get('industryIdentifiers', []):
                        if identifier['type'] in ['ISBN_13', 'ISBN_10']:
                            citation.isbn = identifier['identifier']
                            break

                    citation.source = "google_books"
                    citation.confidence = 0.7

        except Exception as e:
            logger.warning(f"Google Books fetch failed: {e}")

        return citation

    def fetch_from_multiple_sources(self, citation: Citation) -> Citation:
        """Try multiple academic sources"""
        # Try Semantic Scholar
        citation = self.fetch_from_semantic_scholar(citation)

        # Try OpenAlex
        if citation.confidence < 0.7:
            citation = self.fetch_from_openalex(citation)

        # Try Google Scholar
        if citation.confidence < 0.7:
            citation = self.fetch_from_google_scholar(citation)

        return citation

    def fetch_from_semantic_scholar(self, citation: Citation) -> Citation:
        """Fetch from Semantic Scholar API"""
        try:
            search_query = citation.text.replace(f'({citation.year})', '').strip()
            results = self.semantic_scholar.search_paper(search_query, limit=3)

            for paper in results:
                # Check if it's a good match
                if self.is_good_match(paper.title, search_query):
                    citation.title = paper.title
                    citation.authors = [a.name for a in paper.authors] if paper.authors else []
                    citation.year = str(paper.year) if paper.year else citation.year
                    citation.journal = paper.venue if paper.venue else ""
                    citation.doi = paper.doi if hasattr(paper, 'doi') else ""
                    citation.source = "semantic_scholar"
                    citation.confidence = 0.85
                    break

        except Exception as e:
            logger.warning(f"Semantic Scholar fetch failed: {e}")

        return citation

    def fetch_from_openalex(self, citation: Citation) -> Citation:
        """Fetch from OpenAlex"""
        try:
            search_query = citation.text.replace(f'({citation.year})', '').strip()
            works = Works().search(search_query).get()

            if works:
                work = works[0]
                citation.title = work.get('title', '')

                # Extract authors
                if 'authorships' in work:
                    citation.authors = [
                        authorship['author']['display_name']
                        for authorship in work['authorships']
                        if 'author' in authorship and authorship['author']
                    ]

                citation.year = str(work.get('publication_year', citation.year))
                citation.doi = work.get('doi', '').replace('https://doi.org/', '')

                # Get venue
                if 'primary_location' in work and work['primary_location']:
                    if 'source' in work['primary_location'] and work['primary_location']['source']:
                        citation.journal = work['primary_location']['source'].get('display_name', '')

                citation.source = "openalex"
                citation.confidence = 0.8

        except Exception as e:
            logger.warning(f"OpenAlex fetch failed: {e}")

        return citation

    def fetch_from_google_scholar(self, citation: Citation) -> Citation:
        """Fetch from Google Scholar using scholarly"""
        try:
            search_query = citation.text.replace(f'({citation.year})', '').strip()
            search_results = scholarly.search_pubs(search_query)

            # Get first result
            try:
                result = next(search_results)
                pub = scholarly.fill(result)

                citation.title = pub.get('bib', {}).get('title', '')
                citation.authors = pub.get('bib', {}).get('author', '').split(' and ')
                citation.year = str(pub.get('bib', {}).get('pub_year', citation.year))
                citation.journal = pub.get('bib', {}).get('venue', '')
                citation.source = "google_scholar"
                citation.confidence = 0.7

            except StopIteration:
                pass

        except Exception as e:
            logger.warning(f"Google Scholar fetch failed: {e}")

        return citation

    def generate_bibtex(self, citation: Citation) -> str:
        """Generate BibTeX entry from citation data"""
        db = BibDatabase()

        entry = {
            'ID': citation.key,
            'ENTRYTYPE': citation.entry_type,
            'author': ' and '.join(citation.authors) if citation.authors else 'Unknown',
            'title': citation.title or citation.text.replace(f'({citation.year})', '').strip(),
            'year': citation.year
        }

        # Add fields based on entry type
        if citation.entry_type == 'article':
            if citation.journal:
                entry['journal'] = citation.journal
            if citation.volume:
                entry['volume'] = citation.volume
            if citation.pages:
                entry['pages'] = citation.pages

        elif citation.entry_type == 'book':
            if citation.publisher:
                entry['publisher'] = citation.publisher
            if citation.isbn:
                entry['isbn'] = citation.isbn

        # Add DOI if available
        if citation.doi:
            entry['doi'] = citation.doi

        # Add URL if no DOI
        if not citation.doi and citation.url:
            entry['url'] = citation.url

        db.entries = [entry]

        writer = BibTexWriter()
        writer.indent = '  '
        return writer.write(db)

    def generate_bibtex_from_crossref(self, crossref_data: Dict, key: str) -> str:
        """Generate BibTeX from CrossRef data"""
        entry_type = crossref_data.get('type', 'article').replace('-', '')

        entry = {
            'ID': key,
            'ENTRYTYPE': entry_type,
            'title': crossref_data.get('title', [''])[0],
            'year': str(crossref_data.get('published-print', {}).get('date-parts', [[None]])[0][0] or
                      crossref_data.get('published-online', {}).get('date-parts', [[None]])[0][0])
        }

        # Authors
        authors = []
        for author in crossref_data.get('author', []):
            name_parts = []
            if 'given' in author:
                name_parts.append(author['given'])
            if 'family' in author:
                name_parts.append(author['family'])
            if name_parts:
                authors.append(' '.join(name_parts))
        entry['author'] = ' and '.join(authors)

        # Journal/Publisher
        if 'container-title' in crossref_data:
            entry['journal'] = crossref_data['container-title'][0]
        if 'publisher' in crossref_data:
            entry['publisher'] = crossref_data['publisher']

        # Volume, Issue, Pages
        if 'volume' in crossref_data:
            entry['volume'] = crossref_data['volume']
        if 'issue' in crossref_data:
            entry['number'] = crossref_data['issue']
        if 'page' in crossref_data:
            entry['pages'] = crossref_data['page']

        # DOI
        if 'DOI' in crossref_data:
            entry['doi'] = crossref_data['DOI']

        db = BibDatabase()
        db.entries = [entry]

        writer = BibTexWriter()
        writer.indent = '  '
        return writer.write(db)

    def is_good_match(self, title1: str, title2: str) -> bool:
        """Check if two titles are a good match"""
        # Simple fuzzy matching - could be enhanced
        t1 = title1.lower().strip()
        t2 = title2.lower().strip()

        # Check if one contains the other
        if t1 in t2 or t2 in t1:
            return True

        # Check word overlap
        words1 = set(t1.split())
        words2 = set(t2.split())
        overlap = len(words1.intersection(words2))

        return overlap / min(len(words1), len(words2)) > 0.7

    def find_best_book_match(self, results: List[Dict], citation: Citation) -> Optional[Dict]:
        """Find best matching book from search results"""
        search_text = citation.text.lower()

        for result in results:
            title = result.get('title', '').lower()
            authors = [a.lower() for a in result.get('author_name', [])]

            # Check title similarity
            if self.is_good_match(title, search_text):
                return result

            # Check if author matches
            for author in citation.authors:
                if any(author.lower() in a for a in authors):
                    return result

        return results[0] if results else None

    def cache_citation(self, citation: Citation, cache_file: Path):
        """Cache citation data"""
        cache_data = {
            'title': citation.title,
            'authors': citation.authors,
            'year': citation.year,
            'journal': citation.journal,
            'volume': citation.volume,
            'pages': citation.pages,
            'doi': citation.doi,
            'isbn': citation.isbn,
            'publisher': citation.publisher,
            'bibtex': citation.bibtex,
            'source': citation.source,
            'confidence': citation.confidence,
            'entry_type': citation.entry_type
        }

        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)


class ZoteroManager:
    """Manages Zotero integration"""

    def __init__(self):
        self.library_id = os.getenv('ZOTERO_LIBRARY_ID')
        self.library_type = os.getenv('ZOTERO_LIBRARY_TYPE', 'user')
        self.api_key = os.getenv('ZOTERO_API_KEY')

        if all([self.library_id, self.api_key]):
            self.zot = zotero.Zotero(self.library_id, self.library_type, self.api_key)
            self.enabled = True
            logger.info("Zotero integration enabled")
        else:
            self.enabled = False
            logger.warning("Zotero credentials not found in .env")

    def create_collection(self, name: str) -> Optional[str]:
        """Create a new collection in Zotero"""
        if not self.enabled:
            return None

        try:
            collection_data = {
                'name': name,
                'parentCollection': False
            }
            result = self.zot.create_collections([collection_data])
            if result and 'successful' in result:
                return result['successful']['0']['key']
        except Exception as e:
            logger.error(f"Failed to create Zotero collection: {e}")

        return None

    def add_citation_to_zotero(self, citation: Citation, collection_key: Optional[str] = None) -> bool:
        """Add a citation to Zotero"""
        if not self.enabled:
            return False

        try:
            # Create item based on type
            if citation.entry_type == 'book':
                item = self.zot.item_template('book')
                item['ISBN'] = citation.isbn
                item['publisher'] = citation.publisher
            else:
                item = self.zot.item_template('journalArticle')
                item['publicationTitle'] = citation.journal
                item['volume'] = citation.volume
                item['pages'] = citation.pages

            # Common fields
            item['title'] = citation.title
            item['creators'] = [{'creatorType': 'author', 'name': author} for author in citation.authors]
            item['date'] = citation.year
            item['url'] = citation.url

            if citation.doi:
                item['DOI'] = citation.doi

            # Add to collection if specified
            if collection_key:
                item['collections'] = [collection_key]

            # Create item
            result = self.zot.create_items([item])
            return bool(result and 'successful' in result)

        except Exception as e:
            logger.error(f"Failed to add to Zotero: {e}")
            return False

    def search_in_library(self, query: str) -> Optional[Citation]:
        """Search for existing citation in Zotero library"""
        if not self.enabled:
            return None

        try:
            results = self.zot.items(q=query, limit=5)
            if results:
                # Use first result
                item = results[0]

                # Create Citation object
                citation = Citation(
                    text=item['data'].get('title', ''),
                    url=item['data'].get('url', ''),
                    year=item['data'].get('date', '0000')[:4],
                    authors=[self.format_creator(c) for c in item['data'].get('creators', [])],
                    key=item['data'].get('key', ''),
                    title=item['data'].get('title', ''),
                    source='zotero'
                )

                # Add more fields based on item type
                if item['data']['itemType'] == 'book':
                    citation.entry_type = 'book'
                    citation.isbn = item['data'].get('ISBN', '')
                    citation.publisher = item['data'].get('publisher', '')
                else:
                    citation.entry_type = 'article'
                    citation.journal = item['data'].get('publicationTitle', '')
                    citation.volume = item['data'].get('volume', '')
                    citation.pages = item['data'].get('pages', '')
                    citation.doi = item['data'].get('DOI', '')

                return citation

        except Exception as e:
            logger.error(f"Zotero search failed: {e}")

        return None

    def format_creator(self, creator: Dict) -> str:
        """Format Zotero creator object to name string"""
        if 'name' in creator:
            return creator['name']
        elif 'firstName' in creator and 'lastName' in creator:
            return f"{creator['firstName']} {creator['lastName']}"
        return "Unknown"


class ConceptBoxStyleManager:
    """Manages different concept box styles"""

    def __init__(self):
        self.styles = self.create_styles()

    def create_styles(self) -> Dict[str, ConceptBoxStyle]:
        """Create various concept box styles"""
        styles = {}

        # Professional Blue Style (Default)
        styles['professional_blue'] = ConceptBoxStyle(
            name="Professional Blue",
            color_scheme={
                'bg': 'blue!5!white',
                'frame': 'blue!75!black',
                'title': 'white'
            },
            settings={
                'rounded_corners': True,
                'shadow': True,
                'breakable': True
            },
            latex_code=r"""
\newtcolorbox{conceptbox}[1][]{
  colback=blue!5!white,
  colframe=blue!75!black,
  fonttitle=\bfseries,
  coltitle=white,
  colbacktitle=blue!75!black,
  title=#1,
  rounded corners,
  boxrule=0.5pt,
  boxsep=5pt,
  shadow={2mm}{-2mm}{0mm}{black!30},
  breakable,
  enhanced
}"""
        )

        # Modern Gradient Style
        styles['modern_gradient'] = ConceptBoxStyle(
            name="Modern Gradient",
            color_scheme={
                'bg': 'white',
                'frame': 'purple!50!blue',
                'title': 'white'
            },
            settings={
                'gradient': True,
                'rounded_corners': True
            },
            latex_code=r"""
\newtcolorbox{conceptbox}[1][]{
  colback=white,
  colframe=purple!50!blue,
  fonttitle=\bfseries\large,
  coltitle=white,
  colbacktitle=purple!50!blue,
  title=#1,
  rounded corners=northwest,
  arc=3mm,
  boxrule=0pt,
  leftrule=3mm,
  boxsep=5pt,
  breakable,
  enhanced,
  frame hidden,
  borderline west={3mm}{0pt}{purple!50!blue},
  colback=white,
  overlay={
    \fill[purple!50!blue]
      (frame.north west) --
      (frame.north east) --
      ([yshift=-20pt]frame.north east) --
      ([yshift=-20pt]frame.north west) -- cycle;
  },
  attach boxed title to top left={yshift=-12pt,xshift=10pt},
  boxed title style={
    boxrule=0pt,
    colback=purple!50!blue,
    enhanced,
    arc=2mm
  }
}"""
        )

        # Minimalist Style
        styles['minimalist'] = ConceptBoxStyle(
            name="Minimalist",
            color_scheme={
                'bg': 'gray!5',
                'frame': 'gray!50',
                'title': 'black'
            },
            settings={
                'simple': True,
                'clean': True
            },
            latex_code=r"""
\newtcolorbox{conceptbox}[1][]{
  colback=gray!5,
  colframe=gray!50,
  fonttitle=\bfseries\sffamily,
  coltitle=black,
  title=#1,
  boxrule=0.5pt,
  sharp corners,
  boxsep=10pt,
  breakable,
  enhanced,
  attach boxed title to top left={yshift=-8pt},
  boxed title style={
    boxrule=0pt,
    colback=white,
    sharp corners
  }
}"""
        )

        # Academic Style (with icon)
        styles['academic'] = ConceptBoxStyle(
            name="Academic",
            color_scheme={
                'bg': 'green!5!white',
                'frame': 'green!50!black',
                'title': 'green!20!black'
            },
            settings={
                'icon': True,
                'formal': True
            },
            latex_code=r"""
\usepackage{fontawesome5}
\newtcolorbox{conceptbox}[1][]{
  colback=green!5!white,
  colframe=green!50!black,
  fonttitle=\bfseries,
  coltitle=green!20!black,
  colbacktitle=green!10!white,
  title={\faLightbulb\space#1},
  rounded corners,
  boxrule=1.5pt,
  boxsep=5pt,
  breakable,
  enhanced,
  before upper={\parindent0pt}
}"""
        )

        # Tech/Code Style
        styles['tech'] = ConceptBoxStyle(
            name="Tech",
            color_scheme={
                'bg': 'black!95',
                'frame': 'green!50!white',
                'title': 'green!50!white'
            },
            settings={
                'monospace': True,
                'terminal': True
            },
            latex_code=r"""
\newtcolorbox{conceptbox}[1][]{
  colback=black!95,
  colframe=green!50!white,
  fonttitle=\bfseries\ttfamily,
  coltitle=green!50!white,
  coltext=green!70!white,
  colbacktitle=black!85,
  title={> #1},
  sharp corners,
  boxrule=1pt,
  boxsep=10pt,
  breakable,
  enhanced,
  listing only,
  fontfamily=tt
}"""
        )

        return styles

    def get_style_latex(self, style_name: str = 'professional_blue') -> str:
        """Get LaTeX code for a specific style"""
        if style_name in self.styles:
            return self.styles[style_name].latex_code
        return self.styles['professional_blue'].latex_code

    def get_all_styles_showcase(self) -> str:
        """Generate LaTeX to showcase all styles"""
        showcase = r"""
% Concept Box Style Showcase
\section*{Available Concept Box Styles}

"""
        for name, style in self.styles.items():
            showcase += f"""
\\subsection*{{{style.name}}}
{style.latex_code}

\\begin{{conceptbox}}{{Example: {style.name}}}
This is how the {style.name} style looks. It uses the following color scheme:
\\begin{{itemize}}
\\item Background: {style.color_scheme['bg']}
\\item Frame: {style.color_scheme['frame']}
\\item Title: {style.color_scheme['title']}
\\end{{itemize}}
\\end{{conceptbox}}

\\renewcommand{{\\conceptbox}}{{}}  % Clear for next style
"""
        return showcase


class EnhancedMarkdownToLatexConverter:
    """Enhanced converter with all advanced features"""

    def __init__(self,
                 concept_box_style: str = 'professional_blue',
                 create_zotero_collection: bool = True,
                 parallel_citation_fetch: bool = True):

        self.citations: Dict[str, Citation] = {}
        self.bibtex_entries = []
        self.concept_box_counter = 0

        # Initialize components
        self.citation_fetcher = CitationFetcher()
        self.zotero_manager = ZoteroManager()
        self.style_manager = ConceptBoxStyleManager()

        # Settings
        self.concept_box_style = concept_box_style
        self.parallel_fetch = parallel_citation_fetch

        # Create Zotero collection if requested
        self.zotero_collection_key = None
        if create_zotero_collection and self.zotero_manager.enabled:
            collection_name = f"arXiv_Paper_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.zotero_collection_key = self.zotero_manager.create_collection(collection_name)
            if self.zotero_collection_key:
                logger.info(f"Created Zotero collection: {collection_name}")

    def convert_file(self, input_file: str, output_dir: str = "arxiv_output"):
        """Main conversion method with progress tracking"""
        print(f"\n{Fore.CYAN}Starting conversion of {input_file}{Style.RESET_ALL}\n")

        # Create output directory
        Path(output_dir).mkdir(exist_ok=True)

        # Read markdown file
        print(f"{Fore.YELLOW}Reading markdown file...{Style.RESET_ALL}")
        with open(input_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        # Extract and process citations
        print(f"\n{Fore.YELLOW}Extracting citations...{Style.RESET_ALL}")
        markdown_with_cite_keys = self.extract_and_process_citations(markdown_content)

        # Convert concept boxes
        print(f"\n{Fore.YELLOW}Converting concept boxes...{Style.RESET_ALL}")
        markdown_processed = self.convert_concept_boxes(markdown_with_cite_keys)

        # Convert to LaTeX using pypandoc
        print(f"\n{Fore.YELLOW}Converting to LaTeX...{Style.RESET_ALL}")
        latex_content = self.markdown_to_latex(markdown_processed)

        # Post-process LaTeX
        latex_final = self.post_process_latex(latex_content)

        # Generate BibTeX file
        print(f"\n{Fore.YELLOW}Generating BibTeX file...{Style.RESET_ALL}")
        self.generate_bibtex_file(os.path.join(output_dir, "references.bib"))

        # Generate main LaTeX file
        self.generate_main_tex(latex_final, output_dir)

        # Generate style showcase if requested
        self.generate_style_showcase(output_dir)

        print(f"\n{Fore.GREEN}✓ Conversion complete!{Style.RESET_ALL}")
        print(f"\n{Fore.CYAN}Generated files in {output_dir}:{Style.RESET_ALL}")
        print(f"  - main.tex (main LaTeX file)")
        print(f"  - references.bib (bibliography with {len(self.citations)} citations)")
        print(f"  - Makefile (for compilation)")
        print(f"  - style_showcase.tex (concept box styles)")
        print(f"\n{Fore.YELLOW}To compile: cd {output_dir} && make{Style.RESET_ALL}")

    def extract_and_process_citations(self, content: str) -> str:
        """Extract citations with enhanced processing"""
        # Pattern for [Author et al. (Year)](URL) or [Author (Year)](URL)
        citation_pattern = r'\[([^\]]+\s*\(\d{4}\))\]\(([^\)]+)\)'

        citations_found = list(re.finditer(citation_pattern, content))

        if not citations_found:
            logger.warning("No citations found in markdown")
            return content

        print(f"Found {len(citations_found)} citations")

        # Process each citation with progress bar
        for match in tqdm(citations_found, desc="Processing citations"):
            full_match = match.group(0)
            citation_text = match.group(1)
            url = match.group(2)

            # Check Zotero first
            if self.zotero_manager.enabled:
                zotero_result = self.zotero_manager.search_in_library(citation_text)
                if zotero_result:
                    logger.info(f"Found in Zotero: {citation_text}")
                    citation = zotero_result
                else:
                    # Parse and fetch from other sources
                    citation = self.create_and_fetch_citation(citation_text, url)

                    # Add to Zotero if successful
                    if citation.bibtex and self.zotero_collection_key:
                        self.zotero_manager.add_citation_to_zotero(citation, self.zotero_collection_key)
            else:
                # No Zotero, fetch from other sources
                citation = self.create_and_fetch_citation(citation_text, url)

            # Store citation
            self.citations[citation.key] = citation

            # Replace in content with LaTeX cite command
            content = content.replace(full_match, f"\\cite{{{citation.key}}}")

            # Show fetch result
            if citation.confidence > 0.7:
                tqdm.write(f"  {Fore.GREEN}✓{Style.RESET_ALL} {citation.key} - {citation.source} (confidence: {citation.confidence:.2f})")
            else:
                tqdm.write(f"  {Fore.YELLOW}?{Style.RESET_ALL} {citation.key} - {citation.source} (confidence: {citation.confidence:.2f})")

        return content

    def create_and_fetch_citation(self, citation_text: str, url: str) -> Citation:
        """Create citation object and fetch metadata"""
        # Parse citation text
        authors, year = self.parse_citation_text(citation_text)

        # Create citation key
        cite_key = self.generate_cite_key(authors, year)

        # Create Citation object
        citation = Citation(
            text=citation_text,
            url=url,
            year=year,
            authors=authors,
            key=cite_key
        )

        # Fetch complete metadata
        citation = self.citation_fetcher.fetch_citation(citation)

        # Generate BibTeX if not already present
        if not citation.bibtex:
            citation.bibtex = self.citation_fetcher.generate_bibtex(citation)

        return citation

    def parse_citation_text(self, text: str) -> Tuple[List[str], str]:
        """Parse citation text to extract authors and year"""
        # Extract year
        year_match = re.search(r'\((\d{4})\)', text)
        year = year_match.group(1) if year_match else "0000"

        # Extract authors
        author_part = text.replace(f"({year})", "").strip()

        # Handle "et al."
        if "et al." in author_part:
            first_author = author_part.split("et al.")[0].strip()
            authors = [first_author]
        else:
            # Split by "and" or "&"
            authors = re.split(r'\s+and\s+|\s*&\s*', author_part)
            authors = [a.strip() for a in authors]

        return authors, year

    def generate_cite_key(self, authors: List[str], year: str) -> str:
        """Generate a citation key from authors and year"""
        if not authors:
            return f"unknown{year}"

        # Get last name of first author
        first_author = authors[0].split()[-1].lower()
        # Remove special characters
        first_author = re.sub(r'[^a-z0-9]', '', first_author)

        # Add suffix for uniqueness if needed
        base_key = f"{first_author}{year}" if len(authors) == 1 else f"{first_author}etal{year}"

        # Ensure uniqueness
        key = base_key
        counter = 1
        while key in self.citations:
            key = f"{base_key}{chr(96 + counter)}"  # a, b, c, ...
            counter += 1

        return key

    def convert_concept_boxes(self, content: str) -> str:
        """Convert markdown concept boxes to LaTeX format"""
        # Pattern for *Technical Concept Box: Title* ... content ...
        box_pattern = r'\*\s*(?:Technical\s+)?Concept Box:\s*([^*]+)\*\s*([^*]+?)(?=\n\n|\*\s*(?:Technical\s+)?Concept|\Z)'

        def replace_box(match):
            self.concept_box_counter += 1
            title = match.group(1).strip()
            content = match.group(2).strip()

            # Mark for LaTeX processing
            return f"\n\\begin{{conceptbox}}{{{title}}}\n{content}\n\\end{{conceptbox}}\n"

        converted = re.sub(box_pattern, replace_box, content, flags=re.DOTALL | re.IGNORECASE)

        if self.concept_box_counter > 0:
            print(f"Converted {self.concept_box_counter} concept boxes")

        return converted

    def markdown_to_latex(self, content: str) -> str:
        """Convert markdown to LaTeX using pypandoc"""
        # Prepare pandoc options
        pdoc_args = [
            '--from=markdown+tex_math_dollars+raw_tex',
            '--to=latex',
            '--standalone',
            '--pdf-engine=xelatex',
            '--highlight-style=tango',
            '--top-level-division=section'
        ]

        # Convert
        output = pypandoc.convert_text(
            content,
            'latex',
            format='md',
            extra_args=pdoc_args
        )

        return output

    def post_process_latex(self, latex_content: str) -> str:
        """Post-process LaTeX content for arXiv requirements"""
        # Remove or modify problematic commands
        replacements = {
            r'\\tightlist': '',
            r'\\passthrough': '',
            r'\\href\{([^}]+)\}\{([^}]+)\}': r'\2\footnote{\url{\1}}',  # Convert hrefs to footnotes
            r'\\begin\{Shaded\}': r'\\begin{lstlisting}',  # Convert Shaded to lstlisting
            r'\\end\{Shaded\}': r'\\end{lstlisting}',
        }

        for pattern, replacement in replacements.items():
            latex_content = re.sub(pattern, replacement, latex_content)

        return latex_content

    def generate_bibtex_file(self, output_path: str):
        """Generate BibTeX file from collected citations"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("% Automatically generated bibliography\n")
            f.write(f"% Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"% Total citations: {len(self.citations)}\n\n")

            # Group by source
            by_source = {}
            for cite_key, citation in self.citations.items():
                source = citation.source
                if source not in by_source:
                    by_source[source] = []
                by_source[source].append((cite_key, citation))

            # Write grouped citations
            for source, citations in sorted(by_source.items()):
                f.write(f"% ===== From {source} ({len(citations)} entries) =====\n\n")
                for cite_key, citation in sorted(citations):
                    if citation.bibtex:
                        f.write(citation.bibtex)
                        f.write("\n")

    def generate_main_tex(self, latex_content: str, output_dir: str):
        """Generate the main LaTeX file with proper preamble"""
        # Get the selected concept box style
        concept_box_latex = self.style_manager.get_style_latex(self.concept_box_style)

        preamble = rf"""\documentclass[11pt,a4paper]{{article}}

% Required packages
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage{{lmodern}}
\usepackage{{microtype}}
\usepackage{{hyperref}}
\usepackage{{graphicx}}
\usepackage{{amsmath,amssymb,amsthm}}
\usepackage[natbib=true,style=authoryear-comp,maxcitenames=2,maxbibnames=99,backend=biber]{{biblatex}}
\usepackage[most]{{tcolorbox}}
\usepackage{{xcolor}}
\usepackage{{geometry}}
\usepackage{{listings}}
\usepackage{{fancyvrb}}
\geometry{{margin=1in}}

% Hyperref settings
\hypersetup{{
    colorlinks=true,
    linkcolor=blue!70!black,
    citecolor=blue!70!black,
    urlcolor=blue!70!black,
    pdftitle={{The Architecture of Trust}},
    pdfauthor={{Your Name}}
}}

% Define concept box style (using {self.concept_box_style})
{concept_box_latex}

% Code listing style
\lstset{{
    basicstyle=\ttfamily\small,
    breaklines=true,
    frame=single,
    backgroundcolor=\color{{gray!10}},
    keywordstyle=\color{{blue}},
    commentstyle=\color{{green!60!black}},
    stringstyle=\color{{red}}
}}

% Bibliography
\addbibresource{{references.bib}}

% Document info
\title{{The Architecture of Trust: A Framework for AI-Augmented Real Estate Valuation in the Era of Structured Data}}
\author{{Your Name\\
\texttt{{your.email@example.com}}\\
Your Institution}}
\date{{\today}}

"""

        # Extract title and author from latex_content if present
        title_match = re.search(r'\\title\{([^}]+)\}', latex_content)
        if title_match:
            latex_content = re.sub(r'\\title\{[^}]+\}', '', latex_content)

        author_match = re.search(r'\\author\{([^}]+)\}', latex_content)
        if author_match:
            latex_content = re.sub(r'\\author\{[^}]+\}', '', latex_content)

        # Remove document class and preamble from converted content
        if '\\begin{document}' in latex_content:
            latex_content = latex_content[latex_content.find('\\begin{document}'):]

        # Add bibliography before \end{document}
        latex_content = latex_content.replace(
            '\\end{document}',
            '\n\\printbibliography\n\\end{document}'
        )

        # Combine
        full_latex = preamble + latex_content

        # Save
        output_path = os.path.join(output_dir, "main.tex")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_latex)

        # Also save a Makefile for easy compilation
        makefile_content = """# Makefile for compiling the LaTeX document

MAIN = main
LATEX = xelatex
BIBER = biber
LATEXMK = latexmk

all: $(MAIN).pdf

$(MAIN).pdf: $(MAIN).tex references.bib
\t$(LATEXMK) -pdf -xelatex -biber $(MAIN).tex

quick:
\t$(LATEX) $(MAIN).tex

clean:
\t$(LATEXMK) -c
\trm -f *.bbl *.run.xml *.bcf

cleanall:
\t$(LATEXMK) -C
\trm -f *.bbl *.run.xml *.bcf

view: $(MAIN).pdf
\topen $(MAIN).pdf  # Use 'xdg-open' on Linux, 'start' on Windows

.PHONY: all quick clean cleanall view
"""

        with open(os.path.join(output_dir, "Makefile"), 'w') as f:
            f.write(makefile_content)

        # Create a README
        readme_content = f"""# arXiv Paper: The Architecture of Trust

## Generated Files

- `main.tex` - Main LaTeX document
- `references.bib` - Bibliography with {len(self.citations)} references
- `style_showcase.tex` - Demonstration of available concept box styles
- `Makefile` - Build automation

## Compilation

### Using Make (recommended):
```bash
make
```

### Manual compilation:
```bash
xelatex main.tex
biber main
xelatex main.tex
xelatex main.tex
```

### Quick preview (single pass):
```bash
make quick
```

### Clean auxiliary files:
```bash
make clean
```

## Concept Box Style

Current style: **{self.concept_box_style}**

To see all available styles, compile:
```bash
xelatex style_showcase.tex
```

## Citation Summary

Total citations: {len(self.citations)}

By source:
"""

        # Add citation source summary
        by_source = {}
        for citation in self.citations.values():
            by_source[citation.source] = by_source.get(citation.source, 0) + 1

        for source, count in sorted(by_source.items(), key=lambda x: x[1], reverse=True):
            readme_content += f"- {source}: {count}\n"

        readme_content += f"""

## Notes

1. The document uses the `authoryear-comp` citation style for author-year citations
2. Concept boxes use the `{self.concept_box_style}` style
3. All hyperlinks have been converted to footnotes for arXiv compliance
4. The bibliography includes DOIs where available

## Customization

Edit `main.tex` to:
- Change author information
- Modify the concept box style
- Adjust page margins or fonts
- Add additional packages

## arXiv Submission

1. Run `make cleanall` to remove auxiliary files
2. Create a zip file with:
   - main.tex
   - references.bib
   - Any figure files (if applicable)
3. Upload to arXiv

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        with open(os.path.join(output_dir, "README.md"), 'w') as f:
            f.write(readme_content)

    def generate_style_showcase(self, output_dir: str):
        """Generate a LaTeX file showcasing all concept box styles"""
        showcase_content = r"""\documentclass[11pt,a4paper]{article}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage[most]{tcolorbox}
\usepackage{xcolor}
\usepackage{geometry}
\usepackage{fontawesome5}
\geometry{margin=1in}

\title{Concept Box Style Showcase}
\author{Generated by Enhanced Markdown to LaTeX Converter}
\date{\today}

\begin{document}

\maketitle

\section{Introduction}

This document showcases all available concept box styles for your arXiv paper. Each style has different visual characteristics suitable for different contexts.

"""

        # Add each style
        for style_name, style in self.style_manager.styles.items():
            showcase_content += f"""
\section{{{style.name} Style}}

% Define the style
{style.latex_code}

\subsection{{Example Usage}}

\\begin{{conceptbox}}{{Key Insight: {style.name}}}
This concept box uses the \\textbf{{{style.name}}} style.

Key features:
\\begin{{itemize}}
\\item Background color: \\texttt{{{style.color_scheme['bg']}}}
\\item Frame color: \\texttt{{{style.color_scheme['frame']}}}
\\item Title color: \\texttt{{{style.color_scheme['title']}}}
\\end{{itemize}}

This style is particularly suitable for {self.get_style_description(style_name)}.
\\end{{conceptbox}}

\\begin{{conceptbox}}{{Mathematical Example}}
The {style.name} style also handles mathematical content well:

\\begin{{equation}}
E = mc^2 \\quad \\text{{and}} \\quad e^{{i\\pi}} + 1 = 0
\\end{{equation}}

Code snippets also work:
\\begin{{verbatim}}
def hello_world():
    print("Hello from {style.name} style!")
\\end{{verbatim}}
\\end{{conceptbox}}

% Clear the definition for next style
\\let\\conceptbox\\undefined
\\let\\endconceptbox\\undefined

"""

        showcase_content += r"""
\section{Choosing a Style}

Consider these factors when selecting a concept box style:

\begin{itemize}
\item \textbf{Professional Blue}: Best for formal academic papers
\item \textbf{Modern Gradient}: Good for contemporary, visually appealing documents
\item \textbf{Minimalist}: Ideal when you want the content to speak for itself
\item \textbf{Academic}: Perfect for educational content with key insights
\item \textbf{Tech}: Great for code-heavy or technical documentation
\end{itemize}

\end{document}
"""

        with open(os.path.join(output_dir, "style_showcase.tex"), 'w') as f:
            f.write(showcase_content)

    def get_style_description(self, style_name: str) -> str:
        """Get description for each style"""
        descriptions = {
            'professional_blue': "formal academic papers and professional documents",
            'modern_gradient': "contemporary presentations and visually rich documents",
            'minimalist': "clean, distraction-free reading experiences",
            'academic': "educational content and highlighting key insights",
            'tech': "technical documentation and code-focused content"
        }
        return descriptions.get(style_name, "general purpose use")


def main():
    """Example usage with command line interface"""
    import argparse

    parser = argparse.ArgumentParser(description='Convert Markdown to arXiv-ready LaTeX')
    parser.add_argument('input', help='Input markdown file')
    parser.add_argument('-o', '--output', default='arxiv_output', help='Output directory')
    parser.add_argument('-s', '--style', default='professional_blue',
                       choices=['professional_blue', 'modern_gradient', 'minimalist', 'academic', 'tech'],
                       help='Concept box style')
    parser.add_argument('--no-zotero', action='store_true', help='Disable Zotero integration')
    parser.add_argument('--zotero-collection', action='store_true',
                       help='Create new Zotero collection for this paper')

    args = parser.parse_args()

    # Create converter
    converter = EnhancedMarkdownToLatexConverter(
        concept_box_style=args.style,
        create_zotero_collection=args.zotero_collection and not args.no_zotero
    )

    # Convert the file
    converter.convert_file(args.input, args.output)


if __name__ == "__main__":
    # If no arguments, use the default file
    import sys
    if len(sys.argv) == 1:
        converter = EnhancedMarkdownToLatexConverter(
            concept_box_style='professional_blue',
            create_zotero_collection=True
        )
        converter.convert_file("UADReview_v4b.md", "arxiv_output")
    else:
        main()
```

## How to Use This Implementation

### 1. Set Up Environment

Create `.env` file with your credentials:
```bash
ZOTERO_LIBRARY_ID=123456
ZOTERO_LIBRARY_TYPE=user
ZOTERO_API_KEY=your_api_key_here
SEMANTIC_SCHOLAR_API_KEY=optional_but_recommended
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Converter

Basic usage:
```bash
python converter.py UADReview_v4b.md
```

With options:
```bash
python converter.py UADReview_v4b.md -o my_output --style modern_gradient --zotero-collection
```

### 4. Available Concept Box Styles

- **professional_blue**: Classic academic style with blue accents
- **modern_gradient**: Contemporary style with gradient effects
- **minimalist**: Clean, simple design
- **academic**: Includes icons, good for educational content
- **tech**: Terminal/code style for technical content

### 5. Citation Fetching Sources

The converter tries these sources in order:
1. Your Zotero library (if configured)
2. CrossRef (for DOIs)
3. arXiv (for preprints)
4. Semantic Scholar
5. OpenAlex
6. Google Scholar
7. OpenLibrary (for books)
8. Google Books (for books)

### 6. Features

- **Automatic BibTeX generation** from URLs
- **Multiple citation source fallbacks**
- **Beautiful concept boxes** with 5 style options
- **Zotero integration** with automatic collection creation
- **Progress tracking** with colored output
- **Citation caching** to avoid repeated API calls
- **Comprehensive error handling**
- **arXiv-compliant output**

### 7. Output Files

- `main.tex` - Your converted paper
- `references.bib` - Generated bibliography
- `style_showcase.tex` - Preview all concept box styles
- `Makefile` - Easy compilation
- `README.md` - Documentation for your output

### 8. Troubleshooting

If citations aren't found:
1. Check your internet connection
2. Verify API keys in `.env`
3. Check the `.citation_cache` folder
4. Look at the confidence scores in the output

## Tips for Claude Code Implementation

1. **Start Simple**: First get basic conversion working, then add advanced features
2. **Test Incrementally**: Test citation fetching separately from LaTeX conversion
3. **Cache Results**: The citation cache prevents hitting API rate limits
4. **Handle Errors Gracefully**: Network requests will fail; have fallbacks
5. **Use Progress Bars**: Large documents take time; show progress
6. **Validate Output**: Compile the LaTeX to catch issues early

This implementation guide provides everything needed to convert your markdown to a beautiful arXiv-ready paper with sophisticated citation management!
