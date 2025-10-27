"""Main converter class for markdown to LaTeX conversion."""

# Standard library imports
import csv
import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

# Third-party imports
import pypandoc
from markdown_it import MarkdownIt
from tqdm import tqdm

# Local imports
from src.converters.md_to_latex.bbl_transformer import BblTransformer
from src.converters.md_to_latex.citation_manager import CitationManager
from src.converters.md_to_latex.citation_matcher import CitationMatcher
from src.converters.md_to_latex.concept_boxes import (
    ConceptBoxConverter,
    ConceptBoxStyle,
)
from src.converters.md_to_latex.debug_logger import PipelineDebugger
from src.converters.md_to_latex.latex_builder import LatexBuilder
from src.converters.md_to_latex.post_processing import post_process_latex_file
from src.converters.md_to_latex.utils import (
    clean_markdown_headings,
    convert_html_entities,
    ensure_directory,
    extract_abstract_from_markdown,
    extract_title_from_markdown,
    generate_citation_key,
    normalize_arxiv_url,
    normalize_url,
    parse_bibtex_entries,
)
from src.converters.md_to_latex.zotero_integration import ZoteroClient

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class MarkdownToLatexConverter:
    """Converts markdown documents to LaTeX format with citation and concept box support."""

    def __init__(
        self,
        output_dir: Path | None = None,
        cache_dir: Path | None = None,
        concept_box_style: ConceptBoxStyle = ConceptBoxStyle.PROFESSIONAL_BLUE,
        concept_box_encoding: str | None = None,
        arxiv_ready: bool = True,
        two_column: bool = True,
        prefer_arxiv: bool = False,
        zotero_api_key: str | None = None,
        zotero_library_id: str | None = None,
        zotero_json_path: Path
        | str
        | None = None,  # Local Zotero CSL JSON export
        bibliography_style: str
        | None = "spbasic_pt",  # arXiv-ready default (see CLAUDE.md)
        use_cache: bool = True,
        use_better_bibtex_keys: bool = True,
        font_size: str = "11pt",
        debug_output_dir: Path
        | None = None,  # Optional debug artifact directory
        collection_name: str | None = None,  # Zotero collection name for API
    ):
        """Initialize the converter.

        Args:
            output_dir: Directory for output files
            cache_dir: Directory for citation cache
            concept_box_style: Style for concept boxes
            concept_box_encoding: Encoding format for concept boxes ('asterisk', 'hline', etc.)
            arxiv_ready: Whether to format for arXiv submission
            two_column: Whether to use two-column layout (default True)
            prefer_arxiv: Whether to prefer arXiv metadata over CrossRef when both available
            zotero_api_key: Zotero API key for fetching metadata
            zotero_library_id: Zotero library ID for searching user's library
            bibliography_style: Custom bibliography style (default: 'biblio-style-compact')
            use_cache: Whether to use SQLite cache for citation metadata (default True)
            use_better_bibtex_keys: Whether to use Better BibTeX key format (default True)
            font_size: Font size for document (default '11pt', can be '10pt' for arXiv)
            debug_output_dir: Optional directory for debug artifacts (defaults to output_dir/debug)
            collection_name: Zotero collection name for API fetching
        """
        self.output_dir = (
            output_dir  # Will be set relative to input file if None
        )
        self.cache_dir = cache_dir
        self.concept_box_style = concept_box_style
        self.concept_box_encoding = concept_box_encoding
        self.arxiv_ready = arxiv_ready
        self.two_column = two_column
        self.prefer_arxiv = prefer_arxiv
        self.zotero_api_key = zotero_api_key
        self.zotero_library_id = zotero_library_id
        self.zotero_json_path = (
            Path(zotero_json_path) if zotero_json_path else None
        )
        self.bibliography_style = bibliography_style
        self.use_cache = use_cache
        self.use_better_bibtex_keys = use_better_bibtex_keys
        self.font_size = font_size
        self.debug_output_dir = debug_output_dir
        self.collection_name = collection_name

        # Initialize components
        self.citation_manager = CitationManager(
            cache_dir=self.cache_dir,
            prefer_arxiv=self.prefer_arxiv,
            zotero_api_key=self.zotero_api_key,
            zotero_library_id=self.zotero_library_id,
            use_cache=self.use_cache,
            use_better_bibtex_keys=self.use_better_bibtex_keys,
        )

        # Use enhanced converter if encoding is specified
        if self.concept_box_encoding:
            # Import here to avoid circular imports
            from src.converters.md_to_latex.concept_boxes_enhanced import (
                ConceptBoxEncoding,
                EnhancedConceptBoxConverter,
            )

            # Map string encoding to enum
            encoding_map = {
                "asterisk": ConceptBoxEncoding.ASTERISK,
                "hline": ConceptBoxEncoding.HLINE,
                "blockquote": ConceptBoxEncoding.BLOCKQUOTE,
            }

            encoding = encoding_map.get(self.concept_box_encoding.lower())
            if encoding is None:
                logger.warning(
                    f"Unknown encoding '{self.concept_box_encoding}', using default"
                )
                self.concept_box_converter = ConceptBoxConverter(
                    default_style=self.concept_box_style
                )
            else:
                self.concept_box_converter = EnhancedConceptBoxConverter(
                    encoding=encoding, default_style=self.concept_box_style
                )
        else:
            self.concept_box_converter = ConceptBoxConverter(
                default_style=self.concept_box_style
            )

        self.latex_builder = None

    def _populate_from_zotero_json(self, citations: list) -> tuple[int, int]:
        """Populate citation metadata from local Zotero CSL JSON file.

        Args:
            citations: List of Citation objects extracted from markdown

        Returns:
            Tuple of (matched_count, missing_count)
        """

        if not self.zotero_json_path or not self.zotero_json_path.exists():
            logger.warning(
                f"Zotero JSON file not found: {self.zotero_json_path}"
            )
            return 0, len(citations)

        # Load Zotero JSON
        with open(self.zotero_json_path, encoding="utf-8") as f:
            zotero_entries = json.load(f)

        logger.info(
            f"Loaded {len(zotero_entries)} entries from {self.zotero_json_path}"
        )

        # Use production CitationMatcher
        matcher = CitationMatcher(
            zotero_entries,
            allow_zotero_write=False,  # Read-only for now
        )

        # Match citations using multi-strategy approach
        matched = 0
        for citation in citations:
            entry, strategy = matcher.match(citation.url)
            if entry:
                self._populate_citation_from_csl_json(citation, entry)
                matched += 1

        # Log statistics
        stats = matcher.get_statistics()
        logger.info("Citation matching statistics:")
        logger.info(f"  Total: {stats['total_citations']}")
        logger.info(f"  Matched by DOI: {stats['matched_by_doi']}")
        logger.info(f"  Matched by ISBN: {stats['matched_by_isbn']}")
        logger.info(f"  Matched by arXiv: {stats['matched_by_arxiv']}")
        logger.info(f"  Matched by URL: {stats['matched_by_url']}")
        logger.info(f"  Unmatched: {stats['unmatched']}")
        logger.info(f"  Match rate: {stats['match_rate']:.1f}%")
        logger.info(f"  Deterministic hash: {stats['deterministic_hash']}")

        return matched, len(citations) - matched

    def _populate_from_zotero_api(
        self, citations: list, collection_name: str = "dpp-fashion"
    ) -> tuple[int, int]:
        """Populate citation metadata from Zotero Web API.

        Args:
            citations: List of Citation objects extracted from markdown
            collection_name: Name of Zotero collection to load from

        Returns:
            Tuple of (matched_count, missing_count)
        """
        if not self.zotero_api_key or not self.zotero_library_id:
            logger.error(
                "Zotero API credentials not found. Cannot load from API."
            )
            logger.error("Set ZOTERO_API_KEY and ZOTERO_LIBRARY_ID in .env")
            return 0, len(citations)

        try:
            client = ZoteroClient(
                api_key=self.zotero_api_key, library_id=self.zotero_library_id
            )

            logger.info(
                f"Loading collection '{collection_name}' from Zotero API..."
            )
            zotero_entries = client.get_collection_items(collection_name)

            logger.info(f"Loaded {len(zotero_entries)} entries from Zotero API")

            # Use production CitationMatcher
            matcher = CitationMatcher(
                zotero_entries,
                allow_zotero_write=False,
            )

            # Match citations using multi-strategy approach
            matched = 0
            for citation in citations:
                entry, strategy = matcher.match(citation.url)
                if entry:
                    self._populate_citation_from_csl_json(citation, entry)
                    matched += 1

            # Log statistics
            stats = matcher.get_statistics()
            logger.info("Citation matching statistics:")
            logger.info(f"  Total: {stats['total_citations']}")
            logger.info(f"  Matched by DOI: {stats['matched_by_doi']}")
            logger.info(f"  Matched by ISBN: {stats['matched_by_isbn']}")
            logger.info(f"  Matched by arXiv: {stats['matched_by_arxiv']}")
            logger.info(f"  Matched by URL: {stats['matched_by_url']}")
            logger.info(f"  Unmatched: {stats['unmatched']}")
            logger.info(f"  Match rate: {stats['match_rate']:.1f}%")
            logger.info(f"  Deterministic hash: {stats['deterministic_hash']}")

            return matched, len(citations) - matched

        except Exception as e:
            logger.error(f"Failed to load from Zotero API: {e}")

            traceback.print_exc()
            return 0, len(citations)

    def _populate_from_zotero_bibtex(
        self, citations: list, collection_name: str = "dpp-fashion"
    ) -> tuple[int, int]:
        """Populate citation keys from Zotero BibTeX export with Better BibTeX keys.

        This method fetches the BibTeX export from Zotero, which includes
        Better BibTeX citation keys if the BBT plugin is installed. It then
        matches these keys to the citations extracted from markdown and uses
        the raw BibTeX entries directly, avoiding key generation inconsistencies.

        Args:
            citations: List of Citation objects extracted from markdown
            collection_name: Name of Zotero collection to load from

        Returns:
            Tuple of (matched_count, missing_count)
        """
        if not self.zotero_api_key or not self.zotero_library_id:
            logger.error(
                "Zotero API credentials not found. Cannot load from API."
            )
            logger.error("Set ZOTERO_API_KEY and ZOTERO_LIBRARY_ID in .env")
            return 0, len(citations)

        try:
            client = ZoteroClient(
                api_key=self.zotero_api_key, library_id=self.zotero_library_id
            )

            logger.info(
                f"Fetching BibTeX export from collection '{collection_name}'..."
            )
            bibtex_content = client.get_collection_bibtex(collection_name)

            logger.info(
                f"Parsing BibTeX export ({len(bibtex_content)} chars)..."
            )
            bib_entries = parse_bibtex_entries(bibtex_content)
            logger.info(f"Parsed {len(bib_entries)} BibTeX entries")

            # Build lookup maps for efficient matching
            # Map: normalized URL -> (citation_key, raw_entry)
            url_to_key = {}
            doi_to_key = {}
            arxiv_to_key = {}

            for cite_key, metadata in bib_entries.items():
                # Normalize and index by URL
                if metadata["url"]:
                    normalized = normalize_url(
                        normalize_arxiv_url(metadata["url"])
                    )
                    url_to_key[normalized] = (cite_key, metadata["raw_entry"])

                # Index by DOI
                if metadata["doi"]:
                    doi_to_key[metadata["doi"].lower()] = (
                        cite_key,
                        metadata["raw_entry"],
                    )

                # Index by arXiv ID
                if metadata["arxiv_id"]:
                    arxiv_to_key[metadata["arxiv_id"]] = (
                        cite_key,
                        metadata["raw_entry"],
                    )

            # Match citations
            matched = 0
            for citation in citations:
                matched_key = None
                matched_entry = None

                # Try URL matching (normalize both sides)
                normalized_cite_url = normalize_url(
                    normalize_arxiv_url(citation.url)
                )
                if normalized_cite_url in url_to_key:
                    matched_key, matched_entry = url_to_key[normalized_cite_url]
                    logger.debug(
                        f"Matched by URL: {citation.url} -> {matched_key}"
                    )

                # Try DOI matching
                elif citation.doi and citation.doi.lower() in doi_to_key:
                    matched_key, matched_entry = doi_to_key[
                        citation.doi.lower()
                    ]
                    logger.debug(
                        f"Matched by DOI: {citation.doi} -> {matched_key}"
                    )

                # Try arXiv ID matching
                elif "arxiv.org" in citation.url:
                    # Extract arXiv ID from citation URL
                    if "arxiv.org/abs/" in citation.url:
                        abs_pos = citation.url.find("arxiv.org/abs/")
                        arxiv_id = (
                            citation.url[abs_pos + 14 :]
                            .split("?")[0]
                            .split("#")[0]
                        )
                        # Remove version specifier
                        if "v" in arxiv_id:
                            for i, char in enumerate(arxiv_id):
                                if (
                                    char == "v"
                                    and i > 0
                                    and arxiv_id[i + 1 :].isdigit()
                                ):
                                    arxiv_id = arxiv_id[:i]
                                    break
                        if arxiv_id in arxiv_to_key:
                            matched_key, matched_entry = arxiv_to_key[arxiv_id]
                            logger.debug(
                                f"Matched by arXiv ID: {arxiv_id} -> {matched_key}"
                            )

                if matched_key and matched_entry:
                    # Update citation to use the Better BibTeX key
                    old_key = citation.key
                    citation.key = matched_key
                    citation.raw_bibtex = matched_entry

                    # Update citation manager's registry
                    if old_key in self.citation_manager.citations:
                        del self.citation_manager.citations[old_key]
                    self.citation_manager.citations[matched_key] = citation

                    matched += 1
                else:
                    logger.debug(f"No match found for: {citation.url}")

            logger.info(
                f"Matched {matched}/{len(citations)} citations using Better BibTeX keys"
            )
            unmatched = len(citations) - matched
            if unmatched > 0:
                logger.warning(
                    f"{unmatched} citations not found in Zotero - will generate keys locally"
                )

            return matched, unmatched

        except Exception as e:
            logger.error(f"Failed to load from Zotero BibTeX: {e}")
            traceback.print_exc()
            return 0, len(citations)

    def _populate_citation_from_csl_json(
        self, citation, csl_entry: dict
    ) -> None:
        """Populate citation metadata from CSL JSON entry.

        Note: We do NOT sanitize here because sanitization happens in
        citation_manager.py _escape_bibtex() when generating the .bib file.
        We store the raw metadata here and escape it only when outputting.
        """

        # Extract year from issued field
        issued = csl_entry.get("issued", {})
        date_parts = issued.get("date-parts", [])
        if date_parts and date_parts[0]:
            citation.year = str(date_parts[0][0])

        # Extract authors
        authors = csl_entry.get("author", [])
        if authors:
            author_names = []
            for author in authors:
                # Convert HTML entities in author names
                family = convert_html_entities(author.get("family", ""))
                given = convert_html_entities(author.get("given", ""))
                if family and given:
                    author_names.append(f"{family}, {given}")
                elif family:
                    author_names.append(family)
            if author_names:
                citation.authors = author_names[0].split(",")[
                    0
                ]  # First author last name
                citation.full_authors = " and ".join(author_names)

        # Extract title (convert HTML entities but don't escape yet)
        if "title" in csl_entry:
            citation.title = convert_html_entities(csl_entry["title"])

        # Extract journal/container (convert HTML entities but don't escape yet)
        if "container-title" in csl_entry:
            citation.journal = convert_html_entities(
                csl_entry["container-title"]
            )

        # Extract other fields
        if "volume" in csl_entry:
            citation.volume = str(csl_entry["volume"])
        if "issue" in csl_entry:
            citation.number = str(csl_entry["issue"])
        if "page" in csl_entry:
            citation.pages = csl_entry["page"]
        if "DOI" in csl_entry:
            citation.doi = csl_entry["DOI"]

        # Set BibTeX type
        item_type = csl_entry.get("type", "misc")
        type_map = {
            "article-journal": "article",
            "book": "book",
            "chapter": "incollection",
            "paper-conference": "inproceedings",
            "thesis": "phdthesis",
            "report": "techreport",
            "webpage": "misc",
        }
        citation.bibtex_type = type_map.get(item_type, "misc")

        # CRITICAL: Regenerate citation key with the populated data

        new_key = generate_citation_key(
            citation.authors,
            citation.year,
            citation.title if self.use_better_bibtex_keys else "",
            use_better_bibtex=self.use_better_bibtex_keys,
        )
        # Update the citation key AND the registry
        old_key = citation.key
        citation.key = new_key

        # Update citation manager's registry
        if old_key in self.citation_manager.citations:
            del self.citation_manager.citations[old_key]
            self.citation_manager.citations[new_key] = citation

    def _strip_tables_from_markdown(
        self, markdown_content: str
    ) -> tuple[str, str]:
        """Remove ALL tables from markdown using AST parsing.

        Uses markdown-it-py to parse markdown into AST, identify table line ranges,
        and extract them from source. This handles ALL edge cases including
        multiline cells, nested content, etc.

        Args:
            markdown_content: Original markdown with tables

        Returns:
            Tuple of (markdown_without_tables, markdown_with_only_tables)
        """

        # Parse markdown into tokens with table plugin enabled
        md = MarkdownIt().enable("table")
        tokens = md.parse(markdown_content)

        # Collect table line ranges (start, end) from token.map
        table_ranges = []
        i = 0

        while i < len(tokens):
            token = tokens[i]

            if token.type == "table_open":
                # Found a table - get its source line range from the table_open token
                if token.map and len(token.map) == 2:
                    table_start = token.map[0]
                    table_end = token.map[1]  # Initial end from table_open

                    # Find the table_close to get the actual end line
                    nesting_level = 1
                    j = i + 1

                    while j < len(tokens) and nesting_level > 0:
                        current_token = tokens[j]

                        if current_token.type == "table_open":
                            nesting_level += 1
                        elif current_token.type == "table_close":
                            nesting_level -= 1
                            if nesting_level == 0 and current_token.map:
                                table_end = current_token.map[1]

                        j += 1

                    table_ranges.append((table_start, table_end))

            i += 1

        # Split content into lines
        lines = markdown_content.split("\n")

        # Mark which lines are table lines
        is_table_line = [False] * len(lines)

        for start, end in table_ranges:
            for line_num in range(start, end):
                if line_num < len(lines):
                    is_table_line[line_num] = True

        # Build clean content (non-table lines) with placeholders
        clean_lines = []
        table_lines = []
        table_count = 0
        i = 0

        while i < len(lines):
            if is_table_line[i]:
                # Start of a table region
                table_count += 1
                placeholder = (
                    f"\n[TABLE {table_count} REMOVED - See tables file]\n"
                )
                clean_lines.append(placeholder)

                # Extract all consecutive table lines
                while i < len(lines) and is_table_line[i]:
                    table_lines.append(lines[i])
                    i += 1
            else:
                clean_lines.append(lines[i])
                i += 1

        clean_md = "\n".join(clean_lines)
        tables_md = "\n".join(table_lines)

        logger.info(
            f"Stripped {table_count} tables from markdown using AST parsing"
        )
        logger.info(f"Original size: {len(markdown_content):,} bytes")

        # Avoid division by zero for empty markdown
        if len(markdown_content) > 0:
            clean_pct = len(clean_md) / len(markdown_content) * 100
            tables_pct = len(tables_md) / len(markdown_content) * 100
            logger.info(
                f"Clean size: {len(clean_md):,} bytes ({clean_pct:.1f}%)"
            )
            logger.info(
                f"Tables size: {len(tables_md):,} bytes ({tables_pct:.1f}%)"
            )
        else:
            logger.info(f"Clean size: {len(clean_md):,} bytes")
            logger.info(f"Tables size: {len(tables_md):,} bytes")

        return clean_md, tables_md

    def _extract_tables_to_files(self, content: str) -> str:
        """Extract table environments to separate files in tables/ subdirectory.

        Deduplicates tables by content hash to avoid extracting the same table
        multiple times when the LaTeX builder creates duplicate wrappers.

        Args:
            content: LaTeX content with inline tables

        Returns:
            Modified content with \\input{tables/table_XX} commands
        """

        # Create tables subdirectory
        tables_dir = self.output_dir / "tables"
        tables_dir.mkdir(exist_ok=True)

        # Track seen tables by hash to avoid duplicates
        seen_hashes = {}
        unique_table_counter = 0
        result_lines = []
        current_table = []
        in_table = False
        table_env = None

        for line in content.split("\n"):
            # Check for table start
            if (
                "\\begin{table}" in line
                or "\\begin{table*}" in line
                or "\\begin{longtable}" in line
            ):
                in_table = True
                if "\\begin{table*}" in line:
                    table_env = "table*"
                elif "\\begin{longtable}" in line:
                    table_env = "longtable"
                else:
                    table_env = "table"
                current_table = [line]
                continue

            # If in table, collect lines
            if in_table:
                current_table.append(line)

                # Check for table end
                if f"\\end{{{table_env}}}" in line:
                    in_table = False

                    # Calculate hash of table content
                    table_content = "\n".join(current_table)
                    content_hash = hashlib.md5(
                        table_content.encode()
                    ).hexdigest()

                    # Check if we've seen this table before
                    if content_hash in seen_hashes:
                        # Duplicate table - reuse existing filename
                        table_filename = seen_hashes[content_hash]
                        logger.debug(
                            f"Skipping duplicate table (reusing {table_filename})"
                        )
                    else:
                        # New unique table
                        unique_table_counter += 1
                        table_filename = f"table_{unique_table_counter:02d}.tex"
                        table_path = tables_dir / table_filename

                        # Write table to file
                        with open(table_path, "w", encoding="utf-8") as f:
                            f.write(table_content)

                        seen_hashes[content_hash] = table_filename
                        logger.info(
                            f"Extracted {table_filename} ({len(current_table)} lines)"
                        )

                    # Add input command wrapped in group
                    result_lines.append(
                        "{\\def\\LTcaptype{none} % do not increment counter"
                    )
                    result_lines.append(f"\\input{{tables/{table_filename}}}")
                    result_lines.append("}")
                    result_lines.append("")

                    current_table = []
                    continue

            # Not in table, keep line as is
            if not in_table:
                result_lines.append(line)

        logger.info(f"Total unique tables extracted: {unique_table_counter}")
        return "\n".join(result_lines)

    def convert(
        self,
        markdown_file: Path,
        output_name: str | None = None,
        author: str | None = None,
        verbose: bool = True,
    ) -> Path:
        """Convert a markdown file to LaTeX.

        Args:
            markdown_file: Path to the markdown file
            output_name: Name for output files (without extension)
            author: Author name for the document
            verbose: Whether to show progress

        Returns:
            Path to the generated LaTeX file
        """
        markdown_file = Path(markdown_file)
        if not markdown_file.exists():
            raise FileNotFoundError(f"Markdown file not found: {markdown_file}")

        # Determine output directory relative to input file if not specified
        if self.output_dir is None:
            # Save output in an 'output' subdirectory within the input file's directory
            self.output_dir = markdown_file.parent / "output"

        # Clean output directory to avoid stale artifacts BEFORE ensuring it exists
        if self.output_dir and self.output_dir.exists():
            for item in self.output_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            logger.info(f"Cleaned output directory: {self.output_dir}")

        # Ensure output directory exists
        ensure_directory(self.output_dir)

        # Initialize debug logger for pipeline inspection
        debug_dir = (
            self.debug_output_dir
            if self.debug_output_dir
            else (self.output_dir / "debug")
        )
        debugger = PipelineDebugger(debug_dir)
        logger.info(f"Debug artifacts will be saved to: {debug_dir}")

        # Auto-detect local citation sources if not explicitly provided
        # Fallback order (per OpenAI recommendations):
        # 1. MCP server (via API) - handled by zotero_api_key
        # 2. Local RDF file: {basename}.rdf
        # 3. Local CSL JSON file: {basename}.json
        if not self.zotero_json_path:
            basename = markdown_file.stem
            directory = markdown_file.parent

            # Check for JSON file first (easier to parse)
            json_path = directory / f"{basename}.json"
            if json_path.exists():
                logger.info(f"Auto-detected Zotero CSL JSON file: {json_path}")
                self.zotero_json_path = json_path

            # TODO: Add RDF support
            # rdf_path = directory / f"{basename}.rdf"
            # if rdf_path.exists():
            #     logger.info(f"Auto-detected Zotero RDF file: {rdf_path}")
            #     self.zotero_rdf_path = rdf_path

        # Determine output name
        if output_name is None:
            output_name = markdown_file.stem

        logger.info(f"Converting {markdown_file} to LaTeX")

        # Define conversion steps
        steps = [
            "Reading markdown",
            "Extracting metadata",
            "Processing citations",
            "Processing concept boxes",
            "Converting to LaTeX",
            "Building document",
            "Writing output files",
            "Compiling PDF",
        ]

        # Create progress bar if verbose
        if verbose:
            pbar = tqdm(
                total=len(steps),
                desc="Starting conversion",
                unit=" steps",
                bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}",
            )

        try:
            # Step 1: Read markdown content
            if verbose:
                pbar.set_description("Reading markdown")
            with open(markdown_file, encoding="utf-8") as f:
                content = f.read()
            if verbose:
                pbar.update(1)

            # Step 1.5: Clean markdown headings (remove bold and numbers)
            content = clean_markdown_headings(content)

            # Step 1.6: Strip ALL tables from markdown to avoid table processing bugs
            logger.info("=" * 60)
            logger.info("STRIPPING ALL TABLES FROM MARKDOWN")
            logger.info("=" * 60)
            clean_content, tables_content = self._strip_tables_from_markdown(
                content
            )

            # Save tables to separate file for user to handle manually
            tables_output = self.output_dir / f"{output_name}-TABLES.md"
            tables_output.write_text(tables_content, encoding="utf-8")
            logger.info(f"Tables saved to: {tables_output}")
            logger.info("Main markdown now has ZERO tables - clean conversion!")

            # Use clean content (no tables) for conversion
            content = clean_content

            # Set flag to skip table extraction later in the pipeline
            self._tables_were_stripped = True

            # Step 1.7: Apply smart heuristics for structure
            content, title, abstract = self._apply_structure_heuristics(content)

            # Step 2: Extract title and abstract (if not already found by heuristics)
            if verbose:
                pbar.set_description("Extracting metadata")
            if not title:
                title = extract_title_from_markdown(content)
            if not abstract:
                abstract = extract_abstract_from_markdown(content)
            if verbose:
                pbar.update(1)

            # Step 3: Extract and process citations
            if verbose:
                pbar.set_description("Extracting citations")
            citations = self.citation_manager.extract_citations(content)

            # STAGE 1: Citation Extraction Debug
            debugger.log_stage(1, "Citation Extraction")
            debugger.log_stats(extracted_count=len(citations))
            debugger.log_sample(
                [
                    {
                        "url": c.url,
                        "authors": c.authors,
                        "year": c.year,
                    }
                    for c in citations
                ],
                label="extracted citations",
                max_show=5,
            )
            debugger.dump_json(
                [
                    {
                        "url": c.url,
                        "authors": c.authors,
                        "year": c.year,
                        "title": c.title,
                        "key": c.key,
                    }
                    for c in citations
                ],
                "debug-01-extracted-citations.json",
            )

            # Step 3.5: Pre-populate from Zotero (API preferred, fallback to JSON)
            collection_name = os.getenv("ZOTERO_COLLECTION", "dpp-fashion")

            if self.zotero_api_key and self.zotero_library_id:
                # PREFERRED: Use Zotero Web API
                if verbose:
                    pbar.set_description(
                        f"Loading from Zotero API ({collection_name})"
                    )

                # STAGE 2: Zotero Matching Debug (CRITICAL)
                debugger.log_stage(2, "Zotero Matching via BibTeX Export")
                matched, missing = self._populate_from_zotero_bibtex(
                    citations, collection_name
                )

                # Log matching statistics
                match_rate = (
                    f"{100 * matched / len(citations):.1f}%"
                    if len(citations) > 0
                    else "N/A (no citations)"
                )
                debugger.log_stats(
                    total_citations=len(citations),
                    matched_from_zotero=matched,
                    missing_from_zotero=missing,
                    match_rate=match_rate,
                )

                # Sample of matched citations
                matched_citations = [
                    c for c in citations if c.key and c.key != ""
                ]
                debugger.log_sample(
                    [
                        {
                            "url": c.url,
                            "key": c.key,
                            "authors": c.authors,
                            "year": c.year,
                        }
                        for c in matched_citations[:5]
                    ],
                    label="matched citations",
                    max_show=5,
                )

                # Sample of unmatched citations
                unmatched_citations = [
                    c for c in citations if not c.key or c.key == ""
                ]
                if unmatched_citations:
                    debugger.log_sample(
                        [
                            {"url": c.url, "authors": c.authors, "year": c.year}
                            for c in unmatched_citations[:5]
                        ],
                        label="unmatched citations",
                        max_show=5,
                    )

                # Dump matching results
                match_rate_json = (
                    f"{100 * matched / len(citations):.1f}%"
                    if len(citations) > 0
                    else "N/A"
                )
                debugger.dump_json(
                    {
                        "total": len(citations),
                        "matched": matched,
                        "missing": missing,
                        "match_rate": match_rate_json,
                        "matched_citations": [
                            {
                                "url": c.url,
                                "key": c.key,
                                "authors": c.authors,
                                "year": c.year,
                            }
                            for c in matched_citations
                        ],
                        "unmatched_citations": [
                            {"url": c.url, "authors": c.authors, "year": c.year}
                            for c in unmatched_citations
                        ],
                    },
                    "debug-02-zotero-matching-results.json",
                )

                logger.info(
                    f"Matched {matched}/{len(citations)} citations from Zotero API"
                )
                if missing > 0:
                    logger.warning(
                        f"{missing} citations not found in Zotero - will fetch from APIs"
                    )
            elif self.zotero_json_path:
                # FALLBACK: Use local JSON (deprecated)
                logger.warning(
                    "Using local CSL JSON - consider migrating to Zotero API"
                )
                if verbose:
                    pbar.set_description(
                        f"Loading {self.zotero_json_path.name}"
                    )
                matched, missing = self._populate_from_zotero_json(citations)
                logger.info(
                    f"Matched {matched}/{len(citations)} citations from local Zotero JSON"
                )
                if missing > 0:
                    logger.warning(
                        f"{missing} citations not found in Zotero JSON - will fetch from APIs"
                    )
            else:
                logger.warning(
                    "No Zotero source configured - will fetch all citations from APIs"
                )
                logger.warning(
                    "Set ZOTERO_API_KEY and ZOTERO_LIBRARY_ID in .env for best results"
                )

            # Pre-fetch metadata for all citations to ensure Better BibTeX keys are generated
            if verbose:
                pbar.set_description(
                    f"Fetching metadata for {len(citations)} citations"
                )

            for citation in citations:
                self.citation_manager.fetch_citation_metadata(citation)

            # STAGE 3: Citation Key Generation Debug
            debugger.log_stage(3, "Citation Key Generation & Metadata Fetching")
            keys_generated = sum(1 for c in citations if c.key and c.key != "")
            unknown_authors = sum(
                1 for c in citations if c.authors == "Unknown"
            )
            unknown_years = sum(1 for c in citations if c.year == "Unknown")
            debugger.log_stats(
                total_citations=len(citations),
                keys_generated=keys_generated,
                unknown_authors=unknown_authors,
                unknown_years=unknown_years,
            )
            debugger.dump_json(
                [
                    {
                        "url": c.url,
                        "key": c.key,
                        "authors": c.authors,
                        "year": c.year,
                        "title": c.title,
                    }
                    for c in citations
                ],
                "debug-03-citation-keys-generated.json",
            )

            # Collect failed citations for report
            failed_citations = []
            for citation in citations:
                if citation.authors == "Unknown" or citation.year == "Unknown":
                    # Reconstruct original citation text format: [authors (year)](url)
                    original_text = f"[{citation.authors} ({citation.year})]({citation.url})"
                    failed_citations.append(
                        {
                            "text": original_text,
                            "url": citation.url,
                            "authors": citation.authors,
                            "year": citation.year,
                            "reason": "Not found in Zotero collection, external API fetch failed or returned incomplete data",
                            "action": "Verify URL is correct, check if item exists in Zotero, or add manually to dpp-fashion collection",
                        }
                    )

            # Write missing citations report if there are failures
            if failed_citations:
                # Write JSON report to output directory
                json_path = self.output_dir / "missing-citations-report.json"
                match_rate_report = (
                    f"{100 * (len(citations) - len(failed_citations)) / len(citations):.1f}%"
                    if len(citations) > 0
                    else "N/A"
                )
                with open(json_path, "w") as f:
                    json.dump(
                        {
                            "total_citations": len(citations),
                            "missing_count": len(failed_citations),
                            "match_rate": match_rate_report,
                            "missing_citations": failed_citations,
                        },
                        f,
                        indent=2,
                    )

                # Write CSV for human review with supervision columns to output directory
                csv_path = self.output_dir / "missing-citations-review.csv"
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    # Header with review columns
                    writer.writerow(
                        [
                            "Citation Text",
                            "URL",
                            "Current Authors",
                            "Current Year",
                            "Reason",
                            "Is Real Problem? (YES/NO)",
                            "Should Be In Zotero? (YES/NO)",
                            "Notes",
                        ]
                    )
                    # Data rows
                    for cit in failed_citations:
                        writer.writerow(
                            [
                                cit["text"],
                                cit["url"],
                                cit["authors"],
                                cit["year"],
                                cit["reason"],
                                "",  # User fills: Is this a real problem?
                                "",  # User fills: Should this be in Zotero?
                                "",  # User fills: Additional notes
                            ]
                        )

                logger.warning("Missing citations reports written to:")
                logger.warning(f"  JSON: {json_path}")
                logger.warning(f"  CSV for review: {csv_path}")
                logger.warning(
                    f"{len(failed_citations)}/{len(citations)} citations could not be fully resolved"
                )

            if verbose:
                pbar.set_description(f"Processing {len(citations)} citations")
            content = self.citation_manager.replace_citations_in_text(content)
            if verbose:
                pbar.update(1)

            # Step 4: Extract and process concept boxes
            if verbose:
                pbar.set_description("Processing concept boxes")
            concept_boxes = self.concept_box_converter.extract_concept_boxes(
                content
            )
            content = self.concept_box_converter.replace_boxes_in_text(content)

            # Step 4.5: Mark content between horizontal rules with special markers
            content = self._mark_horizontal_rule_boxes(content)

            # Step 4.6: Escape dollar signs for currency (not math mode)
            # This project processes documents where $ means currency, not math
            content = self._escape_currency_dollars(content)

            if verbose:
                pbar.update(1)

            # Step 5: Convert to LaTeX using pandoc
            if verbose:
                pbar.set_description("Converting with pandoc")
            try:
                latex_content = pypandoc.convert_text(
                    content,
                    "latex",
                    format="markdown+tex_math_dollars+raw_tex+pipe_tables",
                    extra_args=[
                        "--standalone",
                        "--wrap=preserve",
                        "--columns=80",
                        "--listings",  # Use listings for code blocks
                        "--no-highlight",  # Disable syntax highlighting
                        "-V",
                        "documentclass=article",
                        "-V",
                        "geometry:margin=1in",
                        "-V",
                        "tables=true",  # Enable table support
                    ],
                )
            except (RuntimeError, OSError, ValueError) as e:
                logger.error(f"Pandoc conversion failed: {e}")
                raise

            # Fix escaped dollar signs in math equations
            # Pandoc sometimes escapes $$ as \$\$ which breaks LaTeX math
            latex_content = latex_content.replace(r"\$\$", "$$")
            latex_content = latex_content.replace(r"\$", "$")

            if verbose:
                pbar.update(1)

            # Step 6: Build final LaTeX document
            if verbose:
                pbar.set_description("Building LaTeX document")
            self.latex_builder = LatexBuilder(
                title=title,
                author=author,
                abstract=abstract,
                arxiv_ready=self.arxiv_ready,
                two_column=self.two_column,
                bibliography_style=self.bibliography_style or "spbasic_pt",
                font_size=self.font_size,
            )

            # Add required packages for concept boxes
            self.latex_builder.add_packages(
                self.concept_box_converter.get_required_packages()
            )

            # DIAGNOSTIC: Save raw pandoc output for analysis
            raw_path = Path(tempfile.gettempdir()) / "raw_pandoc_output.tex"
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(latex_content)
            logger.info(
                f"Raw pandoc output written to {raw_path} (size={len(latex_content)} chars)"
            )
            logger.info(
                f"Contains \\begin{{document}}: {r'\\begin{document}' in latex_content}, "
                f"Contains \\end{{document}}: {r'\\end{document}' in latex_content}"
            )
            # Correct check without r-string in the search
            has_begin = "\\begin{document}" in latex_content
            has_end = "\\end{document}" in latex_content
            logger.info(f"CORRECTED: Has begin={has_begin}, has end={has_end}")

            # Process pandoc output and build document
            processed_content = self.latex_builder.process_pandoc_output(
                latex_content
            )
            # Pass appendix info if available
            has_appendix = getattr(self, "_has_appendix", False)
            final_latex = self.latex_builder.build_document(
                processed_content, has_appendix=has_appendix
            )
            if verbose:
                pbar.update(1)

            # Step 6b: Extract tables to separate files (only if tables exist)
            if verbose:
                pbar.set_description("Extracting tables to files")

            # Skip table extraction entirely if tables were already stripped from markdown
            if (
                hasattr(self, "_tables_were_stripped")
                and self._tables_were_stripped
            ):
                logger.info("=" * 60)
                logger.info("SKIPPING TABLE EXTRACTION")
                logger.info("=" * 60)
                logger.info(
                    "All tables were stripped from markdown before conversion"
                )
                logger.info(
                    "Any table environments in LaTeX output are spurious/erroneous"
                )
                logger.info(
                    "Skipping extraction prevents bugs in table extraction code"
                )
            else:
                # Count table environments to avoid running extraction on documents with no tables
                table_count = (
                    final_latex.count("\\begin{table}")
                    + final_latex.count("\\begin{table*}")
                    + final_latex.count("\\begin{longtable}")
                )

                if table_count > 0:
                    logger.info(
                        f"Found {table_count} table environments - extracting to separate files"
                    )
                    final_latex = self._extract_tables_to_files(final_latex)
                else:
                    logger.info(
                        "No table environments found - skipping table extraction"
                    )
                    logger.info(
                        "This prevents bugs in table extraction code when processing table-free documents"
                    )

            # Step 7: Write output files
            if verbose:
                pbar.set_description("Writing output files")
            output_tex = self.output_dir / f"{output_name}.tex"
            with open(output_tex, "w", encoding="utf-8") as f:
                f.write(final_latex)

            # Step 7a: Post-process LaTeX file to fix common issues
            if verbose:
                pbar.set_description("Post-processing LaTeX")
            post_process_latex_file(output_tex)
            logger.info("Applied post-processing fixes to LaTeX file")

            # STAGE 5: LaTeX Citation Commands Debug
            debugger.log_stage(5, "LaTeX Citation Commands Validation")
            tex_content = output_tex.read_text(encoding="utf-8")
            citep_count = tex_content.count(r"\citep{")
            citet_count = tex_content.count(r"\citet{")
            cite_count = tex_content.count(r"\cite{")
            total_cites = citep_count + citet_count + cite_count
            debugger.log_stats(
                tex_file_size=len(tex_content),
                citep_count=citep_count,
                citet_count=citet_count,
                cite_count=cite_count,
                total_citations_in_tex=total_cites,
            )
            debugger.dump_json(
                {
                    "citep_count": citep_count,
                    "citet_count": citet_count,
                    "cite_count": cite_count,
                    "total": total_cites,
                    "expected": len(citations),
                    "matches_expected": total_cites == len(citations),
                },
                "debug-05-latex-citations.json",
            )

            # Write BibTeX file
            output_bib = self.output_dir / "references.bib"
            if verbose and citations:
                pbar.set_description(
                    f"Writing bibliography ({len(citations)} citations)"
                )
            self.citation_manager.generate_bibtex_file(
                output_bib, show_progress=verbose
            )

            # STAGE 4: BibTeX File Generation Debug
            debugger.log_stage(4, "BibTeX File Generation & Validation")
            bib_content = output_bib.read_text(encoding="utf-8")
            entry_count = bib_content.count("@")
            unknown_count = bib_content.count("Unknown")
            anonymous_count = bib_content.count("Anonymous")
            debugger.log_stats(
                bib_file_size=len(bib_content),
                entry_count=entry_count,
                unknown_count=unknown_count,
                anonymous_count=anonymous_count,
            )
            # Save copy of BibTeX for inspection
            debugger.dump_text(bib_content, "debug-04-references.bib")
            debugger.dump_json(
                {
                    "entry_count": entry_count,
                    "unknown_count": unknown_count,
                    "anonymous_count": anonymous_count,
                    "has_errors": unknown_count > 0 or anonymous_count > 0,
                },
                "debug-04-bibtex-validation.json",
            )

            # Copy bibliography style file (use spbasic_pt as default)
            bib_style = self.bibliography_style or "spbasic_pt"
            bst_filename = f"{bib_style}.bst"

            # Look for .bst file in converter directory first, then templates, then project root
            converter_dir = Path(__file__).parent
            bst_source = converter_dir / bst_filename

            if not bst_source.exists():
                project_root = Path(__file__).parent.parent.parent.parent.parent
                templates_dir = project_root / "templates"
                bst_source = templates_dir / bst_filename

                # If not in templates, check project root
                if not bst_source.exists():
                    bst_source = project_root / bst_filename

            if bst_source.exists():
                bst_dest = self.output_dir / bst_filename
                shutil.copy2(bst_source, bst_dest)
                logger.info(f"Copied {bst_filename} to output directory")
            else:
                logger.warning(
                    f"Bibliography style file {bst_filename} not found"
                )

            # Create Makefile
            self.latex_builder.create_makefile(
                self.output_dir, f"{output_name}.tex"
            )

            # Create README
            self.latex_builder.create_readme(self.output_dir)
            if verbose:
                pbar.update(1)

            # Step 8: Compile PDF
            if verbose:
                pbar.set_description("Compiling PDF")
            pdf_path = self._compile_pdf(output_tex, verbose)
            if verbose:
                pbar.update(1)

            # STAGE 6: PDF Compilation & Citation Resolution Debug
            debugger.log_stage(
                6, "PDF Compilation & Citation Resolution Validation"
            )
            if pdf_path and pdf_path.exists():
                debugger.log_stats(
                    pdf_generated=True, pdf_size_bytes=pdf_path.stat().st_size
                )

                # Check .blg file for unresolved citations
                blg_path = pdf_path.with_suffix(".blg")
                if blg_path.exists():
                    blg_content = blg_path.read_text(encoding="utf-8")
                    missing_entries = []
                    for line in blg_content.splitlines():
                        if "didn't find a database entry for" in line:
                            # Extract the citation key from the error line
                            parts = line.split('"')
                            if len(parts) >= 2:
                                missing_entries.append(parts[1])

                    debugger.log_stats(
                        blg_file_exists=True,
                        missing_entries_count=len(missing_entries),
                    )
                    debugger.dump_json(
                        {
                            "pdf_exists": True,
                            "pdf_size": pdf_path.stat().st_size,
                            "missing_entries": missing_entries,
                            "has_unresolved": len(missing_entries) > 0,
                        },
                        "debug-06-pdf-validation.json",
                    )
                else:
                    debugger.log_stats(blg_file_exists=False)
                    debugger.dump_json(
                        {
                            "pdf_exists": True,
                            "pdf_size": pdf_path.stat().st_size,
                            "blg_missing": True,
                        },
                        "debug-06-pdf-validation.json",
                    )
            else:
                debugger.log_stats(pdf_generated=False)
                debugger.dump_json(
                    {"pdf_exists": False, "error": "PDF compilation failed"},
                    "debug-06-pdf-validation.json",
                )

            # Step 9: Summary
            if verbose:
                pbar.set_description("Complete")
                pbar.close()

            self._print_summary(output_tex, citations, concept_boxes, pdf_path)

            return output_tex

        except Exception as e:
            if verbose and "pbar" in locals():
                pbar.close()
            logger.error(f"Conversion failed: {e}")
            raise

    def _escape_currency_dollars(self, content: str) -> str:
        """Escape dollar signs that represent currency, not math mode.

        This is critical for this project where all $ signs represent USD currency.
        Also converts Unicode math symbols to LaTeX text-mode commands directly.
        """
        # Replace Unicode symbols with LaTeX text-mode commands directly
        # This avoids placeholders and ensures proper rendering
        replacements = {
            "×": r"\texttimes{}",  # Text mode multiplication sign
            "±": r"\textpm{}",  # Text mode plus-minus
            "≥": r"\textgreaterequal{}",  # May need textcomp package
            "≤": r"\textlessequal{}",  # May need textcomp package
            "°": r"\textdegree{}",  # Text mode degree symbol
            "µ": r"\textmu{}",  # Text mode micro symbol
            "∞": r"\textinfty{}",  # May need custom definition
            "≈": r"\textapprox{}",  # May need custom definition
            "÷": r"\textdiv{}",  # May need custom definition
            "≠": r"\textneq{}",  # May need custom definition
        }

        for symbol, latex_cmd in replacements.items():
            content = content.replace(symbol, latex_cmd)

        # Replace all dollar signs with escaped versions
        # We'll use a temporary placeholder to avoid double-escaping
        content = content.replace(r"\$", "ESCAPED_DOLLAR_PLACEHOLDER")
        content = content.replace("$", r"\$")
        content = content.replace("ESCAPED_DOLLAR_PLACEHOLDER", r"\$")

        return content

    def _mark_horizontal_rule_boxes(self, content: str) -> str:
        """Mark content from 'Technical Concept Box' to next '---' with special markers."""
        # import re  # Banned - using string methods instead

        # Pattern to find Technical Concept Box followed by content until ---
        # This handles multiple formats:
        # 1. Plain text format: Technical Concept Box: Title
        # 2. Bold format (**Title**) on its own line
        # 3. Italic format (*Title*) with content on same line

        box_count = 0

        # First, handle empty concept boxes more robustly
        # Pattern for empty boxes: ---\nTechnical Concept Box: Title\n---

        def replace_empty_box(match):
            nonlocal box_count
            title = match.group(1).strip()
            box_count += 1
            # Remove escaped characters for cleaner title
            clean_title = title.replace("\\!", "!").replace("\\", "")
            return f"---\nTechnical Concept Box: {clean_title}\n(Content to be added)\n---"

        # Apply empty box replacement first without regex
        lines = content.split("\n")
        new_lines = []
        i = 0

        while i < len(lines):
            # Check for empty box pattern: ---\nTechnical Concept Box: Title\n---
            if (
                i + 2 < len(lines)
                and lines[i].strip() == "---"
                and lines[i + 1].strip().startswith("Technical Concept Box:")
                and lines[i + 2].strip() == "---"
            ):
                # Extract title
                title_line = lines[i + 1].strip()
                title = title_line[len("Technical Concept Box:") :].strip()

                # Create fake match for replace function
                class FakeMatch:
                    def __init__(self, title):
                        self._title = title

                    def group(self, n):
                        if n == 1:
                            return self._title
                        return ""

                fake_match = FakeMatch(title)
                replacement = replace_empty_box(fake_match)
                new_lines.extend(replacement.split("\n"))
                i += 3
            else:
                new_lines.append(lines[i])
                i += 1

        content = "\n".join(new_lines)

        def replace_box(match):
            nonlocal box_count
            title = match.group(1).strip()
            content = match.group(2).strip()
            box_count += 1
            # Use special text markers that will survive pandoc conversion
            return f"\n\nCONCEPTBOXSTART{{{title}}}CONCEPTBOXSTART\n\n{content}\n\nCONCEPTBOXEND\n\n---"

        # Pattern 1: Plain text format (no markdown formatting)
        # This handles the format: ---\nTechnical Concept Box: Title\nContent...\n---

        # Apply pattern 1 without regex
        # Pattern: ^Technical Concept Box:\s*([^\n]+)\n((?:(?!^---)(?!^Technical Concept Box:).)*?)\n---
        lines = content.split("\n")
        result_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check for Technical Concept Box at start of line
            if line.strip().startswith("Technical Concept Box:"):
                # Extract title
                title = line.strip()[len("Technical Concept Box:") :].strip()

                # Collect content until --- or next Technical Concept Box
                content_lines = []
                j = i + 1
                while j < len(lines):
                    if lines[j].strip() == "---":
                        # Found end marker
                        class FakeMatch:
                            def __init__(self, title, content):
                                self._title = title
                                self._content = content

                            def group(self, n):
                                if n == 1:
                                    return self._title
                                elif n == 2:
                                    return self._content
                                return ""

                        box_content = "\n".join(content_lines)
                        fake_match = FakeMatch(title, box_content)
                        replacement = replace_box(fake_match)
                        result_lines.extend(replacement.split("\n"))
                        i = j + 1
                        break
                    elif lines[j].strip().startswith("Technical Concept Box:"):
                        # Hit next box, no end marker
                        result_lines.append(line)
                        i += 1
                        break
                    else:
                        content_lines.append(lines[j])
                        j += 1
                else:
                    # No end found
                    result_lines.append(line)
                    i += 1
            else:
                result_lines.append(line)
                i += 1

        result = "\n".join(result_lines)

        # Pattern 2: Bold format with title on its own line

        # Apply pattern 2 if no matches from pattern 1
        if box_count == 0:
            # Apply pattern 2 without regex - Bold title on its own line
            lines = result.split("\n")
            result_lines = []
            i = 0

            while i < len(lines):
                line = lines[i].strip()

                # Check for **Title** format
                if (
                    line.startswith("**")
                    and line.endswith("**")
                    and len(line) > 4
                    and "\n" not in line[2:-2]
                ):
                    title = line[2:-2].strip()

                    # Look for Technical Concept Box on next line
                    if (
                        i + 1 < len(lines)
                        and lines[i + 1].strip() == "Technical Concept Box:"
                    ):
                        # Collect content until ---
                        content_lines = []
                        j = i + 2
                        while j < len(lines):
                            if lines[j].strip() == "---":
                                # Found end
                                class FakeMatch:
                                    def __init__(self, title, content):
                                        self._title = title
                                        self._content = content

                                    def group(self, n):
                                        if n == 1:
                                            return self._title
                                        elif n == 2:
                                            return self._content
                                        return ""

                                box_content = "\n".join(content_lines)
                                fake_match = FakeMatch(title, box_content)
                                replacement = replace_box(fake_match)
                                result_lines.extend(replacement.split("\n"))
                                i = j + 1
                                break
                            else:
                                content_lines.append(lines[j])
                                j += 1
                        else:
                            result_lines.append(lines[i])
                            i += 1
                    else:
                        result_lines.append(lines[i])
                        i += 1
                else:
                    result_lines.append(lines[i])
                    i += 1

            result = "\n".join(result_lines)

        # Pattern 3: Italic format with content on same line
        # Match: *Technical Concept Box: Title* Content...

        # Apply pattern 3 if still no matches
        if box_count == 0:
            # Apply pattern 3 without regex - Italic title with content
            lines = result.split("\n")
            result_lines = []
            i = 0

            while i < len(lines):
                line = lines[i]

                # Look for *Technical Concept Box: Title* pattern
                if "*Technical Concept Box:" in line:
                    start_pos = line.find("*Technical Concept Box:")
                    # Find closing *
                    end_pos = line.find(
                        "*", start_pos + 23
                    )  # 23 = len('*Technical Concept Box:')

                    if end_pos > start_pos:
                        # Extract title
                        title_part = line[start_pos + 23 : end_pos].strip()

                        # Collect content until ---
                        content_lines = (
                            [line[end_pos + 1 :].strip()]
                            if line[end_pos + 1 :].strip()
                            else []
                        )
                        j = i + 1

                        while j < len(lines):
                            if lines[j].strip() == "---":
                                # Found end
                                class FakeMatch:
                                    def __init__(self, title, content):
                                        self._title = title
                                        self._content = content

                                    def group(self, n):
                                        if n == 1:
                                            return self._title
                                        elif n == 2:
                                            return self._content
                                        return ""

                                box_content = "\n".join(content_lines)
                                fake_match = FakeMatch(title_part, box_content)
                                replacement = replace_box(fake_match)

                                # Add any content before the pattern
                                if start_pos > 0:
                                    result_lines.append(line[:start_pos])

                                result_lines.extend(replacement.split("\n"))
                                i = j + 1
                                break
                            else:
                                content_lines.append(lines[j])
                                j += 1
                        else:
                            result_lines.append(line)
                            i += 1
                    else:
                        result_lines.append(line)
                        i += 1
                else:
                    result_lines.append(line)
                    i += 1

            result = "\n".join(result_lines)

        if box_count > 0:
            logger.info(
                f"Marked {box_count} concept boxes (from 'Technical Concept Box' to '---') for conversion"
            )

        return result

    def _apply_structure_heuristics(
        self, content: str
    ) -> tuple[str, str | None, str | None]:
        """Apply smart heuristics to improve document structure.

        Returns:
            tuple of (modified_content, title, abstract)
        """
        lines = content.split("\n")
        modified_lines = []
        title = None
        abstract = None
        abstract_lines = []
        in_abstract = False
        found_first_heading = False
        has_appendix = False
        appendix_line_idx = None

        # First pass: check for appendix
        for i, line in enumerate(lines):
            # Check for appendix heading without regex
            stripped = line.strip()
            if stripped.startswith("#"):
                # Count heading level
                heading_level = 0
                for char in stripped:
                    if char == "#":
                        heading_level += 1
                    else:
                        break

                if 1 <= heading_level <= 3:
                    # Extract heading text
                    heading_text = stripped[heading_level:].strip()
                    if heading_text.lower().startswith(
                        ("appendix", "appendices")
                    ):
                        has_appendix = True
                        appendix_line_idx = i
                        break

        # Second pass: process lines with smart heuristics
        for i, line in enumerate(lines):
            # Check for first level-1 heading (title)
            if not found_first_heading and line.startswith("# "):
                found_first_heading = True
                title = line[2:].strip()
                # Remove markdown formatting
                title = title.replace("**", "").replace("*", "")
                # Skip this line in output (will be handled by \maketitle)
                continue

            # Check for headings (both abstract and other headings)
            stripped = line.strip()
            if stripped.startswith("#"):
                heading_level = 0
                for char in stripped:
                    if char == "#":
                        heading_level += 1
                    else:
                        break

                if 1 <= heading_level <= 3:
                    heading_text = stripped[heading_level:].strip()
                    if heading_text.lower() == "abstract" and not in_abstract:
                        in_abstract = True
                        # Skip the abstract heading line
                        continue
                    elif in_abstract:
                        # End of abstract when we hit next heading
                        in_abstract = False
                        abstract = "\n".join(abstract_lines).strip()
                        abstract_lines = []
                        # Don't skip this heading - let it be added to modified_lines

            # Collect abstract content
            if in_abstract:
                abstract_lines.append(line)
                continue

            # Add line to output
            modified_lines.append(line)

        # If still in abstract at end of file
        if in_abstract and abstract_lines:
            abstract = "\n".join(abstract_lines).strip()

        # Reconstruct content
        modified_content = "\n".join(modified_lines)

        # Store appendix info for later use
        self._has_appendix = has_appendix
        self._appendix_line_idx = appendix_line_idx

        return modified_content, title, abstract

    def _compile_pdf(self, tex_file: Path, verbose: bool) -> Path | None:
        """Compile LaTeX to PDF using xelatex or pdflatex.

        Returns:
            Path to the generated PDF if successful, None otherwise
        """

        # Check if xelatex is available (preferred for UTF-8)
        if shutil.which("xelatex"):
            latex_cmd = "xelatex"
        elif shutil.which("pdflatex"):
            latex_cmd = "pdflatex"
            logger.info(
                "Using pdflatex (xelatex preferred for better UTF-8 support)"
            )
        else:
            logger.warning(
                "No LaTeX compiler found in PATH. Skipping PDF compilation."
            )
            logger.info(
                "To compile PDF manually, install a LaTeX distribution (e.g., TeX Live, MiKTeX)"
            )
            return None

        pdf_name = tex_file.stem + ".pdf"

        # Save current directory
        original_dir = Path.cwd()

        try:
            # Change to output directory for compilation

            os.chdir(self.output_dir)

            # Run first latex pass to generate aux file
            if verbose:
                logger.info(f"Running {latex_cmd} (pass 1/3)...")

            cmd = [
                latex_cmd,
                "-interaction=nonstopmode",
                tex_file.name,  # Remove halt-on-error to continue past math errors
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )

            if result.returncode != 0:
                logger.warning(
                    f"{latex_cmd} pass 1 had errors (continuing to run bibtex)"
                )

            # Run biber/bibtex if we have citations and using biblatex
            # Use relative path since we're already in output_dir
            if Path("references.bib").exists():
                # Check if we're using biblatex by looking for the .bcf file
                bcf_file = tex_file.with_suffix(".bcf")
                if bcf_file.exists():
                    # Using biblatex - run biber
                    if verbose:
                        logger.info("Running biber...")

                    bibtex_result = subprocess.run(
                        ["biber", tex_file.stem],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=30,
                    )
                else:
                    # Using traditional bibtex
                    if verbose:
                        logger.info("Running bibtex...")

                    bibtex_result = subprocess.run(
                        ["bibtex", tex_file.stem],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=30,
                    )

                if bibtex_result.returncode != 0:
                    logger.warning("biber/bibtex had warnings/errors")
                    if verbose:
                        logger.warning(bibtex_result.stdout)
                        if bibtex_result.stderr:
                            logger.warning(bibtex_result.stderr)

                # Check if .bbl file was created and is valid
                # Use relative path since we're in output_dir
                bbl_file = Path(tex_file.stem + ".bbl")

                if not bbl_file.exists() or bbl_file.stat().st_size == 0:
                    logger.warning(
                        "Bibliography processing failed - continuing without bibliography"
                    )
                    # Don't try to run pdflatex again with broken bibliography
                    # Check if PDF was already created in initial passes
                    pdf_path = self.output_dir / pdf_name
                    return pdf_path if pdf_path.exists() else None

                # Transform .bbl to arXiv format with hyperlinked author names
                try:
                    # Use relative path since we're in output_dir
                    bib_file = Path("references.bib")

                    if bib_file.exists() and bbl_file.exists():
                        if verbose:
                            logger.info(
                                "Transforming .bbl to arXiv format with hyperlinked authors..."
                            )

                        transformer = BblTransformer(bib_file, bbl_file)
                        transformed_bbl = transformer.transform()

                        # Write transformed .bbl back
                        with open(bbl_file, "w") as f:
                            f.write(transformed_bbl)

                        if verbose:
                            logger.info("BBL transformation complete")
                except Exception as e:
                    logger.warning(f"BBL transformation failed: {e}")
                    # Continue with untransformed .bbl

                # Run pdflatex twice more to incorporate bibliography
                for i in range(2):
                    if verbose:
                        logger.info(
                            f"Running {latex_cmd} with bibliography (pass {i + 1}/2)..."
                        )

                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=60,
                    )

                    if result.returncode != 0:
                        logger.error(f"{latex_cmd} failed after bibtex")
                        return None

        except subprocess.TimeoutExpired:
            logger.error(f"{latex_cmd} timed out")
            return None
        except Exception as e:
            logger.error(f"Error during PDF compilation: {e}")
            return None
        finally:
            # Always return to original directory
            os.chdir(original_dir)

        # Check if PDF exists in output directory (after returning to original dir)
        pdf_check_path = self.output_dir / pdf_name
        if pdf_check_path.exists():
            logger.info(f"PDF successfully generated: {pdf_check_path}")
            return pdf_check_path
        else:
            logger.error("PDF file was not created")
            return None

    def _extract_latex_errors(self, log_file: Path) -> None:
        """Extract and display LaTeX errors from log file."""
        try:
            with open(log_file, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            in_error = False
            error_lines = []

            for line in lines:
                if line.startswith("!"):
                    in_error = True
                    error_lines.append(line)
                elif in_error and line.strip() == "":
                    in_error = False
                    if error_lines:
                        logger.error("LaTeX Error:")
                        for err_line in error_lines[:10]:  # Show first 10 lines
                            logger.error(f"  {err_line.rstrip()}")
                        error_lines = []
                elif in_error:
                    error_lines.append(line)

        except Exception as e:
            logger.warning(f"Could not parse LaTeX log: {e}")

    def _print_summary(
        self,
        output_file: Path,
        citations: list,
        concept_boxes: list,
        pdf_path: Path | None = None,
    ) -> None:
        """Print conversion summary."""
        print("\n" + "=" * 60)
        print("CONVERSION SUMMARY")
        print("=" * 60)
        print(f"Output file: {output_file}")
        if pdf_path:
            print(f"PDF file: {pdf_path}")
        else:
            print(
                "PDF file: Not generated (pdflatex not available or compilation failed)"
            )
        print(f"Citations extracted: {len(citations)}")
        print(f"Concept boxes found: {len(concept_boxes)}")
        print("Additional files created:")
        print("  - references.bib")
        print("  - Makefile")
        print("  - README.md")

        if not pdf_path:
            print("\nTo compile the LaTeX document manually:")
            print(f"  cd {self.output_dir}")
            print("  make")

        print("=" * 60 + "\n")

    def set_concept_box_style(self, style: ConceptBoxStyle) -> None:
        """Change the concept box style."""
        self.concept_box_style = style
        self.concept_box_converter.set_style(style)

    def get_available_styles(self) -> list:
        """Get list of available concept box styles."""
        return [style.value for style in ConceptBoxStyle]
