"""Example of converting files to LyX format."""

from pathlib import Path

from src.converters.to_lyx import (
    MarkdownToLyxConverter,
    TexToLyxConverter,
)


def example_tex_to_lyx():
    """Convert a TeX file to LyX."""
    print("=== TeX to LyX Conversion ===")

    # Create a sample TeX file
    tex_content = r"""
\documentclass[11pt]{article}
\usepackage{amsmath}
\usepackage{graphicx}

\title{Sample LaTeX Document}
\author{Jane Doe}
\date{\today}

\begin{document}
\maketitle

\begin{abstract}
This is a sample LaTeX document demonstrating conversion to LyX format.
\end{abstract}

\section{Introduction}
LaTeX is a powerful typesetting system. Here's the famous equation:

\begin{equation}
E = mc^2
\label{eq:einstein}
\end{equation}

\section{Features}
\begin{itemize}
\item Mathematical equations
\item Cross-references
\item Bibliography support
\item Figure inclusion
\end{itemize}

\end{document}
"""

    # Save to temporary file
    tex_file = Path("sample.tex")
    tex_file.write_text(tex_content)

    try:
        # Convert to LyX
        converter = TexToLyxConverter()
        lyx_file = converter.convert(tex_file)
        print(f"Converted {tex_file} to {lyx_file}")

        # Also try with roundtrip option
        lyx_roundtrip = converter.convert_with_options(
            tex_file, output_file=Path("sample_roundtrip.lyx"), roundtrip=True
        )
        print(f"Converted with roundtrip to {lyx_roundtrip}")

    finally:
        # Clean up
        tex_file.unlink(missing_ok=True)


def example_markdown_to_lyx():
    """Convert a Markdown file to LyX."""
    print("\n=== Markdown to LyX Conversion ===")

    # Create a sample Markdown file
    md_content = """# Research Paper on Machine Learning

**Author:** John Smith
**Date:** 2025

## Abstract

This paper explores recent advances in machine learning, particularly
in the field of deep learning. We reference [LeCun et al. (2015)](https://doi.org/10.1038/nature14539)
for foundational concepts.

## Introduction

Machine learning has revolutionized many fields. According to
[Goodfellow et al. (2016)](https://www.deeplearningbook.org/),
deep learning represents a significant advancement.

*Technical Concept Box: Neural Networks*
Neural networks are computational models inspired by biological neurons.
They consist of layers of interconnected nodes that process information.
Key components include:
- Input layer
- Hidden layers
- Output layer
- Activation functions

## Methods

We implemented our approach using Python:

```python
import numpy as np
import tensorflow as tf

def create_model():
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dense(10, activation='softmax')
    ])
    return model
```

## Results

Our experiments showed promising results:

| Model | Accuracy | F1 Score |
|-------|----------|----------|
| CNN   | 95.2%    | 0.94     |
| RNN   | 93.8%    | 0.92     |
| LSTM  | 96.1%    | 0.95     |

## Conclusion

Deep learning continues to push the boundaries of what's possible
in artificial intelligence.
"""

    # Save to temporary file
    md_file = Path("sample.md")
    md_file.write_text(md_content)

    try:
        converter = MarkdownToLyxConverter()

        # Simple conversion
        lyx_simple = converter.convert_simple(md_file)
        print(f"Simple conversion: {md_file} to {lyx_simple}")

        # Advanced conversion with citation processing
        lyx_advanced = converter.convert_advanced(
            md_file,
            output_file=Path("sample_advanced.lyx"),
            process_citations=True,
            process_concept_boxes=True,
        )
        print(f"Advanced conversion: {md_file} to {lyx_advanced}")

    finally:
        # Clean up
        md_file.unlink(missing_ok=True)


def example_batch_conversion():
    """Convert multiple files at once."""
    print("\n=== Batch Conversion ===")

    # Create sample files
    files = []
    for i in range(3):
        tex_file = Path(f"doc{i}.tex")
        tex_file.write_text(
            f"\\documentclass{{article}}\n\\begin{{document}}\nDocument {i}\n\\end{{document}}"
        )
        files.append(tex_file)

    md_file = Path("readme.md")
    md_file.write_text("# README\n\nThis is a readme file.")
    files.append(md_file)

    try:
        # Batch convert
        md_converter = MarkdownToLyxConverter()
        md_converter.batch_convert([md_file], simple=True)

        tex_converter = TexToLyxConverter()
        for tex_file in files[:-1]:
            lyx_file = tex_converter.convert(tex_file)
            print(f"Converted {tex_file} to {lyx_file}")

    finally:
        # Clean up
        for f in files:
            f.unlink(missing_ok=True)


if __name__ == "__main__":
    print("LyX Conversion Examples\n")

    try:
        example_tex_to_lyx()
        example_markdown_to_lyx()
        example_batch_conversion()

        print("\nAll examples completed successfully!")
        print("\nYou can also use the CLI:")
        print("  deep-biblio-to-lyx from-tex input.tex")
        print("  deep-biblio-to-lyx from-markdown input.md")
        print("  deep-biblio-to-lyx batch *.tex *.md")

    except Exception as e:
        print(f"\nError: {e}")
        print("Make sure LyX and pandoc are installed:")
