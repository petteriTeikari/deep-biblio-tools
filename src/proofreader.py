#!/usr/bin/env python3
"""
Streamlit-based proofreading interface for failed citation extractions.

This tool provides a web interface to manually review and correct citations that
failed automatic extraction, storing the corrections in the cache for future use.

Usage: streamlit run src/deep_biblio_tools/proofreader.py
"""

# Standard library imports
import csv
import logging
import sys
import webbrowser
from pathlib import Path

# Handle direct script execution
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))

# Third-party imports
import requests
import streamlit as st

# Local imports
try:
    from .utils.cache import BiblioCache
    from .utils.citation_context_finder import CitationContextFinder
except ImportError:
    from utils.cache import BiblioCache
    from utils.citation_context_finder import CitationContextFinder

# Configure Streamlit page
st.set_page_config(
    page_title="Citation Proofreader",
    page_icon="book",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CitationProofreader:
    """Main proofreading interface class"""

    def __init__(self):
        self.cache = BiblioCache()
        self.context_finder = CitationContextFinder()

        # Initialize session state
        if "current_index" not in st.session_state:
            st.session_state.current_index = 0
        if "citation_contexts" not in st.session_state:
            st.session_state.citation_contexts = {}
        if "failed_entries" not in st.session_state:
            st.session_state.failed_entries = []
        if "corrections_made" not in st.session_state:
            st.session_state.corrections_made = 0
        if "contexts_loaded" not in st.session_state:
            st.session_state.contexts_loaded = False

    def load_citation_contexts(self) -> None:
        """Load contexts for all failed entries in the background."""
        if (
            not st.session_state.failed_entries
            or st.session_state.contexts_loaded
        ):
            return

        with st.spinner("Loading citation contexts from markdown files..."):
            # Extract unique URLs from failed entries
            unique_urls = list(
                set(entry["url"] for entry in st.session_state.failed_entries)
            )

            # Find contexts for all URLs
            all_contexts = self.context_finder.find_all_citation_contexts(
                unique_urls
            )

            # Store in session state
            st.session_state.citation_contexts = all_contexts
            st.session_state.contexts_loaded = True

            # Log summary
            total_contexts = sum(
                len(contexts) for contexts in all_contexts.values()
            )
            logger.info(
                f"Loaded {total_contexts} contexts for {len(unique_urls)} URLs"
            )

    def load_failed_citations(
        self, csv_file_path: str | None = None
    ) -> list[dict]:
        """
        Load failed citations from CSV file or cache.

        Args:
            csv_file_path: Path to CSV file with citation results

        Returns:
            List of failed citation entries
        """
        failed_entries = []

        if csv_file_path and Path(csv_file_path).exists():
            # Load from CSV file
            with open(csv_file_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["Status"] == "ERROR":
                        failed_entries.append(
                            {
                                "original_citation": row["Original_Citation"],
                                "url": row["Original_URL"],
                                "error_message": row["Errors"],
                                "source_file": row["Source_File"],
                                "line_number": row["Line_Number"],
                                "context_before": row.get("Context_Before", ""),
                                "context_after": row.get("Context_After", ""),
                                "full_line": row.get("Full_Line", ""),
                                "has_context": True,
                            }
                        )
        else:
            # Load from cache
            cache_failed = self.cache.get_failed_entries()
            for entry in cache_failed:
                failed_entries.append(
                    {
                        "original_citation": "Unknown",
                        "url": entry["url"],
                        "error_message": entry["error_message"],
                        "timestamp": entry["timestamp"],
                        "needs_manual_review": True,
                    }
                )

        return failed_entries

    def save_correction(
        self,
        url: str,
        citation_text: str,
        corrected_url: str = "",
        enhanced_data: dict = None,
        manual_overrides: dict = None,
    ) -> None:
        """Save manual correction to cache with enhanced DOI data"""
        enhanced_data = enhanced_data or {}
        manual_overrides = manual_overrides or {}

        # Use enhanced data if available, otherwise fall back to manual overrides or defaults
        author = manual_overrides.get("author") or enhanced_data.get(
            "author", ""
        )
        title = enhanced_data.get("title", "")
        year = manual_overrides.get("year") or enhanced_data.get("year", "")
        journal = enhanced_data.get("journal", "")
        doi = enhanced_data.get("doi", "")

        self.cache.add_manual_entry(
            url=url,
            citation_text=citation_text,
            author=author,
            title=title,
            year=year,
            journal=journal,
            doi=doi,
        )
        st.session_state.corrections_made += 1
        logger.info(f"Saved correction for {url}: {citation_text}")

    def extract_doi_from_url(self, url: str) -> str:
        """Extract DOI from URL"""
        # Extract DOI from various URL formats without regex
        url_lower = url.lower()

        # Standard DOI URLs
        if "doi.org/" in url_lower:
            start = url_lower.find("doi.org/") + 8
            doi = url[start:].rstrip("/")
            # Validate it starts with 10.
            if doi.startswith("10."):
                return doi

        # Old DOI format
        elif "dx.doi.org/" in url_lower:
            start = url_lower.find("dx.doi.org/") + 11
            doi = url[start:].rstrip("/")
            # Validate it starts with 10.
            if doi.startswith("10."):
                return doi

        return ""

    def fetch_from_doi_apis(self, url: str) -> str:
        """Quick fetch for preview - returns formatted citation string"""
        doi = self.extract_doi_from_url(url)
        if not doi:
            return None

        # Try CrossRef API
        try:
            response = requests.get(
                f"https://api.crossref.org/works/{doi}",
                headers={"Accept": "application/json"},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                work = data.get("message", {})

                # Extract basic info for preview
                authors = []
                for author in work.get("author", [])[
                    :3
                ]:  # Max 3 authors for preview
                    if "family" in author:
                        authors.append(author["family"])

                year = ""
                if "published-print" in work:
                    year = str(work["published-print"]["date-parts"][0][0])
                elif "published-online" in work:
                    year = str(work["published-online"]["date-parts"][0][0])

                # Format citation preview
                if authors:
                    if len(authors) == 1:
                        citation = authors[0]
                    elif len(authors) == 2:
                        citation = f"{authors[0]} and {authors[1]}"
                    else:
                        citation = f"{authors[0]} et al."

                    if year:
                        citation += f" ({year})"

                    return citation

        except Exception as e:
            logger.debug(f"CrossRef API error: {e}")

        return None

    def fetch_detailed_doi_data(self, url: str) -> dict:
        """Comprehensive fetch for saving - returns structured data"""
        doi = self.extract_doi_from_url(url)
        if not doi:
            return {}

        # Try CrossRef API first
        try:
            response = requests.get(
                f"https://api.crossref.org/works/{doi}",
                headers={"Accept": "application/json"},
                timeout=15,
            )
            if response.status_code == 200:
                data = response.json()
                work = data.get("message", {})

                # Extract comprehensive bibliographic data
                result = {"doi": doi}

                # Authors
                authors = []
                for author in work.get("author", []):
                    if "family" in author:
                        given = author.get("given", "")
                        family = author["family"]
                        if given:
                            authors.append(f"{given} {family}")
                        else:
                            authors.append(family)

                if authors:
                    result["author"] = " and ".join(authors)

                # Title
                titles = work.get("title", [])
                if titles:
                    result["title"] = titles[0]

                # Year
                if "published-print" in work:
                    result["year"] = str(
                        work["published-print"]["date-parts"][0][0]
                    )
                elif "published-online" in work:
                    result["year"] = str(
                        work["published-online"]["date-parts"][0][0]
                    )

                # Journal
                journal_titles = work.get("container-title", [])
                if journal_titles:
                    result["journal"] = journal_titles[0]

                # Volume, Issue, Pages
                if "volume" in work:
                    result["volume"] = work["volume"]
                if "issue" in work:
                    result["issue"] = work["issue"]
                if "page" in work:
                    result["pages"] = work["page"]

                logger.info(f"Successfully fetched DOI data for {doi}")
                return result

        except Exception as e:
            logger.debug(f"CrossRef API error: {e}")

        # Try Semantic Scholar as fallback
        try:
            response = requests.get(
                f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
                params={"fields": "title,authors,year,venue,externalIds"},
                timeout=15,
            )
            if response.status_code == 200:
                data = response.json()
                result = {"doi": doi}

                if "title" in data:
                    result["title"] = data["title"]

                if "authors" in data and data["authors"]:
                    authors = [author["name"] for author in data["authors"]]
                    result["author"] = " and ".join(authors)

                if "year" in data and data["year"]:
                    result["year"] = str(data["year"])

                if "venue" in data and data["venue"]:
                    result["journal"] = data["venue"]

                logger.info(
                    f"Successfully fetched Semantic Scholar data for {doi}"
                )
                return result

        except Exception as e:
            logger.debug(f"Semantic Scholar API error: {e}")

        return {}

    def render_sidebar(self) -> None:
        """Render the sidebar with navigation and stats"""
        st.sidebar.title("Citation Proofreader")

        # Load from cache button
        if st.sidebar.button("Load Failed from Cache"):
            failed_entries = self.load_failed_citations()
            st.session_state.failed_entries = failed_entries
            st.session_state.current_index = 0
            st.session_state.contexts_loaded = False  # Reset contexts flag
            st.session_state.citation_contexts = {}  # Clear old contexts
            st.sidebar.success(
                f"Loaded {len(failed_entries)} failed citations from cache"
            )
            # Load contexts after loading failed entries
            self.load_citation_contexts()

        st.sidebar.divider()

        # Navigation
        if st.session_state.failed_entries:
            total = len(st.session_state.failed_entries)
            current = st.session_state.current_index + 1

            st.sidebar.subheader(f"Navigation ({current}/{total})")

            # Show current citation preview
            if st.session_state.current_index < len(
                st.session_state.failed_entries
            ):
                current_entry = st.session_state.failed_entries[
                    st.session_state.current_index
                ]
                preview_text = current_entry.get(
                    "original_citation", "Unknown"
                )[:30]
                if len(current_entry.get("original_citation", "")) > 30:
                    preview_text += "..."

                # Show context preview if available
                context_preview = ""
                if current_entry.get("context_before"):
                    context_preview = (
                        current_entry["context_before"][-20:] + " -> "
                    )

                st.sidebar.info(
                    f"**Current:** {preview_text}\n{context_preview}*[citation]*"
                )

            # Progress bar
            progress = current / total if total > 0 else 0
            st.sidebar.progress(progress)

            # Navigation buttons
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("Previous", disabled=(current <= 1)):
                    st.session_state.current_index = max(
                        0, st.session_state.current_index - 1
                    )
                    st.rerun()

            with col2:
                if st.button("Next", disabled=(current >= total)):
                    st.session_state.current_index = min(
                        total - 1, st.session_state.current_index + 1
                    )
                    st.rerun()

            # Jump to specific entry
            new_index = (
                st.sidebar.number_input(
                    "Jump to entry",
                    min_value=1,
                    max_value=total,
                    value=current,
                    step=1,
                )
                - 1
            )

            if new_index != st.session_state.current_index:
                st.session_state.current_index = new_index
                st.rerun()

        st.sidebar.divider()

        # Cache management
        st.sidebar.subheader("Cache Management")

        if st.sidebar.button("Create Backup"):
            try:
                backup_path = self.cache.create_backup()
                st.sidebar.success(f"Backup created: {backup_path.name}")
            except Exception as e:
                st.sidebar.error(f"Backup failed: {e}")

        # Show recent backups
        backups = self.cache.list_backups()
        if backups:
            st.sidebar.write("**Recent Backups:**")
            for backup in backups[-3:]:  # Show last 3
                st.sidebar.write(
                    f"- {backup['name']} ({backup['size_mb']:.1f}MB)"
                )

    def render_citation_editor(self, entry: dict) -> None:
        """Render the main citation editing interface"""
        st.markdown("### Citation Review & Correction")

        # Display current citation info
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("#### Citation Details")

            # URL with clickable link
            st.markdown("**URL:**")
            st.markdown(f"[{entry['url']}]({entry['url']})")

            # Original citation text (if available)
            if (
                "original_citation" in entry
                and entry["original_citation"] != "Unknown"
            ):
                st.markdown("**Original Citation Text:**")
                st.code(entry["original_citation"])

            # Error message
            st.markdown("**Error Message:**")
            st.error(entry["error_message"])

            # Check for contexts from CitationContextFinder
            contexts_from_finder = st.session_state.citation_contexts.get(
                entry["url"], []
            )

            # Show contexts from CSV if available
            if entry.get("has_context") and (
                entry.get("context_before") or entry.get("context_after")
            ):
                st.markdown("**Context in Document (from CSV):**")

                # Build context display with highlighting
                context_display = ""
                if entry.get("context_before"):
                    context_display += entry["context_before"]

                # Highlight the citation
                citation_part = (
                    f"[{entry['original_citation']}]({entry['url']})"
                )
                context_display += f" **-> {citation_part} <-** "

                if entry.get("context_after"):
                    context_display += entry["context_after"]

                st.markdown(
                    f"<div style='font-size: 0.9em; font-style: italic; background-color: #f0f2f6; padding: 10px; border-radius: 5px;'>...{context_display.strip()}...</div>",
                    unsafe_allow_html=True,
                )

                # Show full line if available and different from context
                if entry.get("full_line") and len(entry["full_line"]) > len(
                    context_display
                ):
                    with st.expander("Full line context"):
                        st.text(entry["full_line"])

            # Show contexts from CitationContextFinder
            if contexts_from_finder:
                st.markdown("**All Occurrences in Markdown Files:**")

                # Group contexts by file
                contexts_by_file = {}
                for ctx in contexts_from_finder:
                    if ctx.file_path not in contexts_by_file:
                        contexts_by_file[ctx.file_path] = []
                    contexts_by_file[ctx.file_path].append(ctx)

                # Display contexts
                for file_path, file_contexts in contexts_by_file.items():
                    file_name = Path(file_path).name
                    with st.expander(
                        f"{file_name} ({len(file_contexts)} occurrences)"
                    ):
                        for i, ctx in enumerate(file_contexts, 1):
                            st.markdown(
                                f"**Occurrence {i} (line {ctx.line_number}):**"
                            )

                            # Build highlighted context
                            context_html = '<div style="font-family: monospace; background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin: 10px 0;">'
                            context_html += f'{ctx.text_before}<span style="background-color: #ffeb3b; padding: 2px 4px; border-radius: 3px; font-weight: bold;">[{ctx.citation_text}]({entry["url"]})</span>{ctx.text_after}'
                            context_html += "</div>"
                            st.markdown(context_html, unsafe_allow_html=True)

                            if (
                                ctx.full_line
                                != ctx.text_before
                                + f"[{ctx.citation_text}]({entry['url']})"
                                + ctx.text_after
                            ):
                                with st.expander("Show full line"):
                                    st.code(ctx.full_line, language=None)
            elif not entry.get("has_context"):
                # No contexts found anywhere
                st.info("No context found in markdown files for this URL.")

            # Additional context (moved after main context for better flow)
            if "source_file" in entry:
                st.markdown(
                    f"<small><strong>Source:</strong> {entry['source_file']} (line {entry.get('line_number', 'unknown')})</small>",
                    unsafe_allow_html=True,
                )

        with col2:
            st.markdown("#### Quick Actions")

            # Open URL in new tab
            if st.button("Open URL", key="open_url"):
                webbrowser.open_new_tab(entry["url"])
                st.success("Opened in new tab")

            # Skip this entry
            if st.button("Skip Entry", key="skip"):
                st.session_state.current_index += 1
                st.rerun()

            # Mark as unsolvable
            if st.button("Mark Unsolvable", key="unsolvable"):
                self.save_correction(
                    url=entry["url"],
                    citation_text="[UNSOLVABLE]",
                    corrected_url=entry["url"],
                    enhanced_data={
                        "author": "Unknown",
                        "title": "Could not resolve",
                    },
                )
                st.success("Marked as unsolvable")
                st.session_state.current_index += 1
                st.rerun()

        st.divider()

        # Manual correction form
        st.markdown("#### Manual Correction")

        with st.form("correction_form", clear_on_submit=True):
            citation_text = st.text_input(
                "Citation Text *",
                placeholder="Smith et al. (2023)",
                help="How the citation should appear in the text",
                value="",
            )

            corrected_url = st.text_input(
                "URL",
                placeholder="https://doi.org/10.1000/example",
                help="Corrected or verified URL (can be same as original)",
                value=entry["url"],  # Pre-fill with original URL
            )

            # Advanced options (collapsible)
            with st.expander("Advanced Options (Optional)"):
                st.info(
                    "**Tip**: If you provide a DOI URL, we'll automatically fetch bibliographic details from CrossRef and other databases when you submit."
                )

                # Manual override fields (for edge cases)
                manual_author = st.text_input(
                    "Manual Author Override",
                    placeholder="Leave blank to auto-detect",
                )
                manual_year = st.text_input(
                    "Manual Year Override",
                    placeholder="Leave blank to auto-detect",
                )

            # Submit button
            submit = st.form_submit_button(
                "Save Correction", type="primary", use_container_width=True
            )

            if submit:
                if not citation_text.strip():
                    st.error("Citation text is required!")
                else:
                    # Try to enhance with DOI data if URL is a DOI
                    enhanced_data = {}
                    if corrected_url and "doi.org" in corrected_url:
                        with st.spinner("Enhancing with DOI data..."):
                            enhanced_data = self.fetch_detailed_doi_data(
                                corrected_url
                            )

                    # Save the correction with enhanced data
                    self.save_correction(
                        url=entry["url"],
                        citation_text=citation_text.strip(),
                        corrected_url=corrected_url.strip(),
                        enhanced_data=enhanced_data,
                        manual_overrides={
                            "author": manual_author.strip()
                            if "manual_author" in locals()
                            else "",
                            "year": manual_year.strip()
                            if "manual_year" in locals()
                            else "",
                        },
                    )

                    st.success(f"Saved correction: {citation_text}")

                    # Move to next entry
                    if (
                        st.session_state.current_index
                        < len(st.session_state.failed_entries) - 1
                    ):
                        st.session_state.current_index += 1

                    st.rerun()

    def render_main_interface(self) -> None:
        """Render the main interface"""
        if not st.session_state.failed_entries:
            st.title("Citation Proofreader")
            st.info(
                "Use the sidebar to load failed citations from a CSV file or cache."
            )

            st.subheader("Getting Started")
            st.markdown("""
            1. **Upload CSV**: Use the file uploader in the sidebar to load a citation CSV file
            2. **Load from Cache**: Or click "Load Failed from Cache" to review cached failures
            3. **Review & Correct**: Click through failed citations and provide manual corrections
            4. **Save Progress**: Corrections are automatically saved to the cache for future use
            """)

            st.subheader("Tips")
            st.markdown("""
            - Click the URL link to open the source in a new tab for reference
            - Use "Skip Entry" for citations you can't resolve right now
            - Use "Mark Unsolvable" for permanently broken/inaccessible URLs
            - Your corrections will be used automatically in future processing runs
            """)

        else:
            # Show current citation for editing
            if st.session_state.current_index < len(
                st.session_state.failed_entries
            ):
                current_entry = st.session_state.failed_entries[
                    st.session_state.current_index
                ]
                self.render_citation_editor(current_entry)
            else:
                st.success("All citations reviewed!")
                st.balloons()

                if st.button("Start Over"):
                    st.session_state.current_index = 0
                    st.rerun()

    def run(self) -> None:
        """Main application entry point"""
        try:
            self.render_sidebar()
            self.render_main_interface()

        except Exception as e:
            st.error(f"Application error: {e}")
            logger.error(f"Application error: {e}", exc_info=True)


def main():
    """Run the Streamlit app"""
    app = CitationProofreader()
    app.run()


if __name__ == "__main__":
    main()
