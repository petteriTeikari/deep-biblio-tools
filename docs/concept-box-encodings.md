# Concept Box Encoding Formats

The markdown to LaTeX converter supports multiple encoding formats for technical concept boxes. This allows flexibility in how you mark up your concept boxes in markdown documents.

## Available Encodings

### 1. Asterisk Format (Default)

The original format using asterisks:

```markdown
*Technical Concept Box: Neural Networks*
Neural networks are computational models inspired by biological neurons.
They consist of layers of interconnected nodes that process information.
```

### 2. Horizontal Line Format (`hline`)

Content between horizontal line markers (`---`):

```markdown
---
*Technical Concept Box: Machine Learning*
Machine learning enables systems to learn from data without explicit programming.

Key types include:
- Supervised learning
- Unsupervised learning
- Reinforcement learning
---
```

### 3. Blockquote Format

Using markdown blockquote syntax:

```markdown
> Technical Concept Box: Deep Learning
> Deep learning uses neural networks with multiple layers.
> It has revolutionized computer vision and natural language processing.
> Key architectures include CNNs, RNNs, and Transformers.
```

## Usage Examples

### Command Line

```bash
# Use default asterisk format
deep-biblio-md2latex paper.md

# Use horizontal line format
deep-biblio-md2latex paper.md --box-encoding hline

# Use blockquote format
deep-biblio-md2latex paper.md --box-encoding blockquote
```

### Python API

```python
from deep_biblio_tools.converters.md_to_latex import (
    MarkdownToLatexConverter,
    ConceptBoxStyle,
)

# Using hline encoding
converter = MarkdownToLatexConverter(
    concept_box_encoding='hline',
    concept_box_style=ConceptBoxStyle.PROFESSIONAL_BLUE
)

# Convert your document
output_file = converter.convert(Path("paper.md"))
```

## Real-World Example

Here's an example matching the UADReview format:

```markdown
---

*Technical Concept Box: Neural 3D Reconstruction Evolution*
The progression from classical to neural reconstruction methods represents a fundamental shift in how we capture and represent physical spaces:

Classical Methods (2000-2020):

- Photogrammetry: Uses multiple photos to triangulate 3D points
- Time to process: 2-8 hours for a single room
- Output: Sparse point clouds requiring manual cleanup
- Accuracy: High geometric precision but poor visual quality

Neural Methods (2020-present):

- NeRFs: Learn implicit 3D representation from images
- 3D Gaussian Splatting: Explicit primitives enabling real-time rendering
- Time to process: 5-30 minutes with modern algorithms
- Output: Photorealistic, explorable 3D models

Business Impact: The 100x speedup from NeRFs to 3DGS makes on-demand 3D capture viable for routine appraisals.

---
```

This will be converted to a beautifully formatted LaTeX tcolorbox with your chosen style.

## Combining with Styles

All encoding formats work with any of the available concept box styles:

```bash
# Horizontal lines with modern gradient style
deep-biblio-md2latex paper.md --box-encoding hline --style modern_gradient

# Blockquotes with academic formal style
deep-biblio-md2latex paper.md --box-encoding blockquote --style academic_formal
```

## Custom Encodings

The architecture supports adding custom encoding formats. If you have a specific format requirement, you can extend the `BoxDetector` class to implement your own pattern matching.
