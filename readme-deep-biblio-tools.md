# Deep Biblio Tools

Academic literature processing tools for creating comprehensive summaries and literature reviews from collections of research papers.

## Overview

This repository provides tools for:
- Processing academic papers (HTML/MD/PDF) into comprehensive summaries
- Creating literature reviews from paper collections
- Intelligent caching to avoid reprocessing unchanged files
- Maintaining proper academic citations in author-year format

## Features

- **25% Comprehensive Summaries**: Creates summaries that are exactly 25% of the original paper size
- **Citation Conversion**: Automatically converts numeric citations [1] to author-year format (Smith et al., 2023)
- **Smart Caching**: Tracks processed files to avoid redundant work
- **Literature Review Generation**: Synthesizes insights across multiple papers
- **Batch Processing**: Handles entire directories of papers efficiently

## Installation

```bash
git clone https://github.com/yourusername/deep-biblio-tools.git
cd deep-biblio-tools
chmod +x process_papers_with_cache.py
```

## Usage

### Basic Usage

Process all papers in a directory:

```bash
python process_papers_with_cache.py /path/to/papers/
```

### Force Reprocess Specific Files

```bash
python process_papers_with_cache.py /path/to/papers/ --force-reprocess "paper1.pdf" "paper2.html"
```

### Show Cache Contents

```bash
python process_papers_with_cache.py /path/to/papers/ --show-cache
```

## Directory Structure

When you run the tool, it creates the following structure:

```
your_papers_directory/
├── summaries/                    # 25% comprehensive summaries
│   ├── paper1_comprehensive_summary.md
│   ├── paper2_comprehensive_summary.md
│   └── ...
├── review/                       # Literature reviews
│   └── Literature_Review.md
├── paper_processing_cache.json   # Cache tracking file
└── *.prompt                      # Generated prompts for processing
```

## Workflow

1. **Prepare Papers**: Place all papers (HTML/MD files) in a directory
2. **Run Initial Processing**:
   ```bash
   python process_papers_with_cache.py /path/to/papers/
   ```
3. **Process with Claude**: Use the generated `.prompt` files with Claude to create summaries
4. **Generate Literature Review**: After summaries are complete, create a comprehensive review
5. **Add New Papers**: Simply add new files and re-run - only new papers will be processed

## Summary Requirements

Each summary maintains:
- **Exact 25% size** of the original document
- **Author-year citations** throughout
- **Complete bibliography** at the end
- **Structured sections**:
  - Title, Authors, Affiliations
  - Comprehensive Abstract (10-15%)
  - Key Contributions (20-25%)
  - Methodology (30-35%)
  - Results (20-25%)
  - Technical Details (10-15%)
  - References (10-15%)

## Literature Review Structure

Generated reviews include:
1. Abstract (300-400 words)
2. Introduction (800-1000 words)
3. Historical Development (1500-2000 words)
4. Current State-of-the-Art (1500-2000 words)
5. Knowledge Gaps (1000-1500 words)
6. Recent Solutions (1500-2000 words)
7. Future Directions (1000-1500 words)
8. Conclusions (500-700 words)
9. Domain-Specific Context (1500-2000 words)
10. References (complete bibliography)

## Cache Management

The cache system (`paper_processing_cache.json`) tracks:
- File content hash (detects changes)
- Original and output file sizes
- Processing timestamps
- Target summary sizes

This ensures:
- No reprocessing of unchanged files
- Consistent output quality
- Efficient incremental updates

## Example Use Cases

### Scene Graph Research
```bash
python process_papers_with_cache.py ~/papers/scene_graphs/
# Generates summaries and review focused on 3D scene understanding
```

### Active Perception Papers
```bash
python process_papers_with_cache.py ~/papers/active_perception/
# Creates review emphasizing uncertainty and exploration strategies
```

### Scan-to-BIM Literature
```bash
python process_papers_with_cache.py ~/papers/scan2bim/
# Produces industry-focused review with practical applications
```

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

Developed for academic research in computer vision, robotics, and construction technology domains.
