# Example Tool Structure: literature-reviewer

This document shows how the `literature-reviewer` tool would be structured after reorganization.

## Directory Structure

```
tools/literature-reviewer/
├── src/
│   └── literature_reviewer/
│       ├── __init__.py
│       ├── __main__.py          # CLI entry point
│       ├── cli.py               # Click-based CLI
│       ├── core/
│       │   ├── __init__.py
│       │   ├── summarizer.py    # 25% summarization engine
│       │   ├── reviewer.py      # Literature review generator
│       │   └── deduplicator.py  # Reference deduplication
│       ├── extractors/
│       │   ├── __init__.py
│       │   ├── arxiv.py         # ArXiv paper extractor
│       │   ├── sciencedirect.py # ScienceDirect extractor
│       │   └── generic.py       # Generic HTML extractor
│       ├── models/
│       │   ├── __init__.py
│       │   ├── paper.py         # Paper data model
│       │   ├── citation.py      # Citation model
│       │   └── summary.py       # Summary model
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── file_handler.py  # File I/O utilities
│       │   ├── text_utils.py    # Text processing
│       │   └── progress.py      # Progress tracking
│       └── templates/
│           └── review_template.md
├── tests/
│   ├── unit/
│   │   ├── test_summarizer.py
│   │   ├── test_reviewer.py
│   │   └── test_extractors.py
│   ├── integration/
│   │   └── test_full_workflow.py
│   └── fixtures/
│       ├── sample_papers/
│       └── expected_outputs/
├── scripts/
│   └── process_folder.sh        # Wrapper for batch processing
├── examples/
│   ├── basic_usage.py
│   ├── custom_template.py
│   └── batch_processing.py
├── README.md
├── CHANGELOG.md
├── pyproject.toml
└── Makefile

```

## pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "literature-reviewer"
version = "1.0.0"
description = "Automated literature review generator with intelligent summarization"
readme = "README.md"
license = "MIT"
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
keywords = ["literature-review", "academic", "summarization", "citations"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: Text Processing :: Linguistic",
]
requires-python = ">=3.8"
dependencies = [
    "click>=8.0",
    "beautifulsoup4>=4.11",
    "requests>=2.28",
    "rich>=13.0",  # For pretty CLI output
    "pydantic>=2.0",  # For data models
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "black>=23.0",
    "ruff>=0.1",
    "mypy>=1.0",
]

[project.scripts]
literature-reviewer = "literature_reviewer.cli:main"

[project.urls]
Homepage = "https://github.com/your-org/deep-biblio-tools"
Documentation = "https://deep-biblio-tools.readthedocs.io/tools/literature-reviewer"
"Bug Tracker" = "https://github.com/your-org/deep-biblio-tools/issues"

[tool.hatch.build.targets.wheel]
packages = ["src/literature_reviewer"]
```

## CLI Interface (cli.py)

```python
import click
from pathlib import Path
from rich.console import Console
from rich.progress import Progress

from .core import summarizer, reviewer
from .utils import file_handler

console = Console()

@click.group()
@click.version_option()
def cli():
    """Literature Review Generator - Create comprehensive academic literature reviews."""
    pass

@cli.command()
@click.argument('paper_path', type=click.Path(exists=True))
@click.option('--output', '-o', help='Output file path')
@click.option('--compression', '-c', default=25, help='Summary compression percentage')
@click.option('--format', type=click.Choice(['md', 'txt']), default='md')
def summarize(paper_path, output, compression, format):
    """Create a comprehensive summary of an academic paper."""
    console.print(f"[bold blue]Summarizing {paper_path}...[/bold blue]")

    with Progress() as progress:
        task = progress.add_task("Processing...", total=100)

        # Load paper
        paper = file_handler.load_paper(paper_path)
        progress.update(task, advance=30)

        # Generate summary
        summary = summarizer.create_summary(paper, compression_ratio=compression/100)
        progress.update(task, advance=60)

        # Save output
        if output:
            file_handler.save_summary(summary, output, format)
        else:
            console.print(summary.to_markdown())

        progress.update(task, advance=10)

    console.print("[bold green]✓ Summary complete![/bold green]")

@cli.command()
@click.argument('folder_path', type=click.Path(exists=True))
@click.option('--theme', '-t', required=True, help='Theme/context for the review')
@click.option('--output', '-o', default='literature_review.md')
@click.option('--contextualization', '-c', help='How to contextualize findings')
def generate_review(folder_path, theme, output, contextualization):
    """Generate a comprehensive literature review from paper summaries."""
    console.print(f"[bold blue]Generating literature review...[/bold blue]")
    console.print(f"Theme: {theme}")

    # Process all summaries
    summaries = file_handler.load_summaries(folder_path)

    # Generate review
    review = reviewer.create_review(
        summaries=summaries,
        theme=theme,
        contextualization=contextualization
    )

    # Save output
    file_handler.save_review(review, output)
    console.print(f"[bold green]✓ Review saved to {output}[/bold green]")

@cli.command()
@click.argument('folder_path', type=click.Path(exists=True))
@click.option('--theme', '-t', required=True)
@click.option('--contextualization', '-c')
@click.option('--compression', default=25)
def batch_process(folder_path, theme, contextualization, compression):
    """Process an entire folder of papers and generate a literature review."""
    console.print("[bold blue]Batch processing papers...[/bold blue]")

    # This combines summarize + generate_review
    # Implementation details...

if __name__ == '__main__':
    cli()
```

## README.md

```markdown
# literature-reviewer

> Part of the Deep Biblio Tools suite

Automated literature review generator with intelligent summarization capabilities.

## Features

- 📄 **Smart Summarization**: Create 25% summaries while preserving key information
- 🔗 **Citation Preservation**: Maintains author-year citations with hyperlinks
- 📚 **Literature Review Generation**: Automatically create themed literature reviews
- 🔍 **Reference Deduplication**: Intelligent merging of duplicate references
- 🎯 **Theme-based Analysis**: Organize papers by research themes
- 📊 **Batch Processing**: Handle entire folders of academic papers

## Installation

```bash
pip install literature-reviewer
```

Or as part of the full suite:
```bash
pip install deep-biblio-tools[research]
```

## Quick Start

### Summarize a Single Paper
```bash
literature-reviewer summarize paper.html -o summary.md
```

### Generate a Literature Review
```bash
literature-reviewer generate-review ./papers --theme "BIM and Machine Learning" \
    --contextualization "Applications in construction industry"
```

### Batch Process Papers
```bash
literature-reviewer batch-process ./papers --theme "Digital Twins" --compression 25
```

## API Usage

```python
from literature_reviewer import Summarizer, ReviewGenerator

# Summarize a paper
summarizer = Summarizer()
summary = summarizer.process_paper("paper.html", compression=0.25)

# Generate a review
generator = ReviewGenerator()
review = generator.create_review(
    summaries=["summary1.md", "summary2.md"],
    theme="BIM Applications",
    contextualization="Focus on real-world implementations"
)
```

## Configuration

Create a `.literature-reviewer.yml` file:

```yaml
defaults:
  compression: 25
  output_format: markdown

extraction:
  sciencedirect:
    timeout: 30
    retry_attempts: 3

summarization:
  preserve_citations: true
  include_references: true

review:
  dedup_references: true
  citation_style: apa
```

## Contributing

See the [Development Guide](../../docs/05-development/literature-reviewer.md) for details.

## License

MIT License - see LICENSE file in the root repository.
```

This structure provides:
- Clear separation of concerns
- Professional packaging
- Comprehensive testing
- Rich CLI experience
- Good documentation
- Easy installation and usage
