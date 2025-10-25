# **Complete Guide to Hardcoding LaTeX Bibliographies from Markdown**

## **Overview**

This guide provides a comprehensive workflow for converting Markdown citations to hardcoded LaTeX bibliographies, particularly useful when journals don't accept `.bib` files or when you're having issues with `.bst` formatting.

## **Why Hardcode Bibliographies?**

1. **Journal requirements**: Some journals require self-contained submissions without external `.bib` files
2. **Formatting control**: Bypass `.bst` issues and have complete control over citation formatting
3. **Programmatic workflow**: Integrate seamlessly into Python-based Markdown-to-LaTeX pipelines
4. **Preserve original formatting**: Maintain author's intended capitalization and styling

## **Title Case Preservation**

One of the most important aspects of bibliography formatting is preserving the original case of titles. BibTeX often converts titles to sentence case or title case based on the bibliography style, which can be problematic.

### **Common Case Issues**

1. **Acronyms being lowercased**: "LLM" → "llm", "COVID-19" → "covid-19"
2. **Proper nouns losing capitalization**: "Python" → "python", "GitHub" → "github"
3. **Stylistic choices being overridden**: "Don't Make Your LLM" → "Don't make your llm"

### **Example of Case Preservation**

**Original title from arXiv:**

Don't Make Your LLM an Evaluation Benchmark Cheater

**Incorrectly processed:**

Don't make your llm an evaluation benchmark cheater

**Correctly preserved:**

latex
\\bibitem{etal2023c}
et al KZ (2023c) Don't Make Your LLM an Evaluation Benchmark Cheater.

\\href{https://arxiv.org/abs/2311.01964}{arXiv: 2311.01964}.

### **How to Preserve Case in BibTeX (if using .bib files)**

When using `.bib` files, protect capitalization with braces:

bibtex
@article{example2023,
  title \= "{Don't Make Your LLM an Evaluation Benchmark Cheater}",
  % or selectively:
  title \= "Don't Make Your {LLM} an Evaluation Benchmark Cheater",

}

## **Basic Workflow for Hardcoding**

### **Step 1: Generate formatted bibliography (if using existing .bib file)**

bash
pdflatex yourfile.tex
bibtex yourfile

pdflatex yourfile.tex

### **Step 2: Extract formatted bibliography**

Look in the `.bbl` file that BibTeX generates:

latex
\\begin{thebibliography}{99}
\\bibitem{smith2023}
Smith, J. (2023). Title of the article. \\emph{Journal Name}, 45(3), 123--145.

\\bibitem{jones2022}
Jones, A. B. (2022). Another paper title. In \\emph{Proceedings of Conference} (pp. 67--89).

\\end{thebibliography}

### **Step 3: Replace bibliography commands**

Remove:

latex
\\bibliography{mybibfile}

\\bibliographystyle{plain}

Replace with the entire contents of the `.bbl` file.

### **Step 4: Ensure citations work**

Your `\cite{key}` commands will work with the `\bibitem{key}` entries.

## **Converting Markdown Citations to LaTeX**

### **Basic Conversion Rules**

1. **Markdown links** `[text](url)` → `\href{url}{text}`
2. **Page ranges** `152-190` → `152--190`
3. **Journal names** → Wrap in `\emph{}`
4. **DOIs** → Format as `\href{https://doi.org/...}{10.xxxx/...}`
5. **Title case** → Preserve exactly as provided in the original source

### **Example Conversions**

#### **Journal Article with DOI**

**Markdown:**

markdown
Damgård et al. Bounded tamper resilience: How to go beyond the algebraic barrier.
Journal of Cryptology, 30:152–190, 2015a. doi:

\[10.1007/s00145-015-9218-0\](https://doi.org/10.1007/s00145-015-9218-0)

**LaTeX:**

latex
\\bibitem{damgard2015a}
Damgård et al. Bounded tamper resilience: How to go beyond the algebraic barrier.
\\emph{Journal of Cryptology}, 30:152--190, 2015a.

doi: \\href{https://doi.org/10.1007/s00145-015-9218-0}{10.1007/s00145-015-9218-0}.

#### **arXiv Preprint (with proper case)**

**Markdown:**

markdown
et al KZ (2023c) Don't Make Your LLM an Evaluation Benchmark Cheater.

\[arXiv: 2311.01964\](https://arxiv.org/abs/2311.01964)

**LaTeX:**

latex
\\bibitem{etal2023c}
et al KZ (2023c) Don't Make Your LLM an Evaluation Benchmark Cheater.

\\href{https://arxiv.org/abs/2311.01964}{arXiv: 2311.01964}.

## **Python Implementation**

### **Basic Conversion Function with Case Preservation**

python
import re

def markdown\_citation\_to\_latex(citation, key, preserve\_case\=True):
    """
    Convert a markdown citation to LaTeX bibitem format.

    Args:
        citation: The citation text
        key: The citation key
        preserve\_case: If True, maintains original capitalization
    """
    *\# Convert markdown links \[text\](url) to \\href{url}{text}*
    citation \= re.sub(r'\\\[(\[^\\\]\]+)\\\]\\((\[^)\]+)\\)', r'\\\\href{\\2}{\\1}', citation)

    *\# Convert journal names to italics (simple heuristic)*
    *\# Only if we're not preserving case completely*
    if not preserve\_case:
        parts \= citation.split('. ')
        if len(parts) \> 1:
            *\# Check if second part looks like a journal citation*
            if ',' in parts\[1\] and ':' in parts\[1\]:
                journal\_part \= parts\[1\].split(',')\[0\]
                parts\[1\] \= parts\[1\].replace(journal\_part, f'\\\\emph{{{journal\_part}}}', 1)
            citation \= '. '.join(parts)

    *\# Convert page ranges from \- to \--*
    citation \= re.sub(r'(\\d+)-(\\d+)', r'\\1--\\2', citation)


    return f'\\\\bibitem{{{key}}}\\n{citation}'

### **Advanced Function with Title Extraction and Case Preservation**

python
import re
from urllib.parse import urlparse

def extract\_and\_preserve\_title(citation):
    """
    Extract title from citation while preserving its original case.

    Common patterns:
    \- Author (Year) Title. Journal...
    \- Author et al. Title. Conference...
    \- Author. "Title." Source...
    """
    *\# Pattern 1: After year in parentheses*
    match \= re.search(r'\\(\\d{4}\[a-z\]?\\)\\s+(\[^.\]+?)\\.', citation)
    if match:
        return match.group(1).strip()

    *\# Pattern 2: After "et al." or author name, before journal/conference*
    match \= re.search(r'(?:et al\\.|\[A-Z\]\[a-z\]+(?:\\s+\[A-Z\]\[a-z\]+)\*)\\s+(\[^.\]+?)(?:\\.|,\\s\*(?:In|Journal|Proceedings))', citation)
    if match:
        return match.group(1).strip()

    *\# Pattern 3: Quoted title*
    match \= re.search(r'"(\[^"\]+)"', citation)
    if match:
        return match.group(1).strip()

    return None

def format\_paper\_citation\_with\_case(citation, key, title\_override\=None):
    """
    Convert citation with URL to LaTeX format, preserving title case.

    Args:
        citation: The citation text
        key: The citation key
        title\_override: Optional correct title to use (e.g., from original source)
    """
    *\# If we have a title override, use it*
    if title\_override:
        original\_title \= extract\_and\_preserve\_title(citation)
        if original\_title and original\_title.lower() \== title\_override.lower():
            *\# Replace the title with the correctly cased version*
            citation \= citation.replace(original\_title, title\_override)

    *\# Extract URL if present*
    url\_match \= re.search(r'https?://\[^\\s\]+', citation)
    if url\_match:
        url \= url\_match.group(0)
        base\_citation \= citation.replace(url, '').strip()

        *\# Determine venue type from URL*
        domain \= urlparse(url).netloc

        venue\_map \= {
            'neurips.cc': 'NeurIPS',
            'nips.cc': 'NeurIPS',
            'openreview.net': 'OpenReview',
            'aclweb.org': 'ACL Anthology',
            'aclanthology.org': 'ACL Anthology',
            'ieee': 'IEEE Xplore',
            'springer': 'Springer',
            'mlr.press': 'MLR Press',
            'proceedings.mlr.press': 'MLR Press',
            'arxiv.org': 'arXiv',
        }

        link\_text \= None
        for domain\_key, venue\_name in venue\_map.items():
            if domain\_key in domain:
                link\_text \= venue\_name
                *\# Try to extract year for conference proceedings*
                if venue\_name in \['NeurIPS', 'ICML', 'ICLR'\]:
                    year\_match \= re.search(r'/(\\d{4})/', url)
                    if year\_match:
                        link\_text \= f"{venue\_name} {year\_match.group(1)}"
                break

        if not link\_text:
            link\_text \= "Online"

        *\# Format the citation*
        formatted \= f"\\\\bibitem{{{key}}}\\n{base\_citation} "
        formatted \+= f"\\\\href{{{url}}}{{{link\_text}}}."

        return formatted
    else:

        return f"\\\\bibitem{{{key}}}\\n{citation}"

### **Function to Fetch and Preserve Original Titles**

python
import requests
from bs4 import BeautifulSoup

def fetch\_arxiv\_title(arxiv\_id):
    """
    Fetch the correct title from arXiv with proper capitalization.

    Args:
        arxiv\_id: The arXiv ID (e.g., "2311.01964")

    Returns:
        The title with correct capitalization, or None if not found
    """
    try:
        url \= f"https://arxiv.org/abs/{arxiv\_id}"
        response \= requests.get(url)
        soup \= BeautifulSoup(response.text, 'html.parser')

        *\# Find the title in the meta tag or h1*
        title\_meta \= soup.find('meta', {'name': 'citation\_title'})
        if title\_meta:
            return title\_meta.get('content')

        *\# Fallback to h1 title*
        title\_h1 \= soup.find('h1', class\_\='title')
        if title\_h1:
            *\# Remove "Title:" prefix if present*
            title\_text \= title\_h1.text.strip()
            if title\_text.startswith('Title:'):
                title\_text \= title\_text\[6:\].strip()
            return title\_text

    except Exception as e:
        print(f"Error fetching arXiv title: {e}")

    return None

*\# Example usage with title correction*
def process\_citation\_with\_correct\_title(citation, key):
    """Process citation and correct title case if it's from arXiv."""
    *\# Check if it's an arXiv citation*
    arxiv\_match \= re.search(r'arxiv.org/abs/(\\d+\\.\\d+)', citation, re.IGNORECASE)
    if arxiv\_match:
        arxiv\_id \= arxiv\_match.group(1)
        correct\_title \= fetch\_arxiv\_title(arxiv\_id)
        if correct\_title:
            return format\_paper\_citation\_with\_case(citation, key, title\_override\=correct\_title)


    return format\_paper\_citation\_with\_case(citation, key)

### **Complete Example with Case Preservation**

python
*\# Example citations with case issues*
citations \= \[
    ("etal2023c", "et al KZ (2023c) don't make your llm an evaluation benchmark cheater. https://arxiv.org/abs/2311.01964"),
    ("smith2024", "Smith J (2024) understanding covid-19 and machine learning. Journal of AI Research, 45:123-145"),
    ("workshop2024", "Lee et al. (2024) pytorch and tensorflow: a comparison. NeurIPS 2024 Workshop on ML Frameworks"),
\]

*\# Correct titles (could be fetched automatically or provided manually)*
correct\_titles \= {
    "etal2023c": "Don't Make Your LLM an Evaluation Benchmark Cheater",
    "smith2024": "Understanding COVID-19 and Machine Learning",
    "workshop2024": "PyTorch and TensorFlow: A Comparison"
}

print("\\\\begin{thebibliography}{99}\\n")

for key, citation in citations:
    correct\_title \= correct\_titles.get(key)
    formatted \= format\_paper\_citation\_with\_case(citation, key, title\_override\=correct\_title)
    print(formatted)
    print()

print("\\\\end{thebibliography}")

## **Handling Different Citation Types**

### **Papers Without DOI or arXiv**

#### **Option 1: Conference name only**

latex
\\bibitem{a2024a}
A et al. (2024a) Benchmarking Uncertainty Disentanglement:
Specialized Uncertainties for Specialized Tasks.

In \\emph{Proceedings of NeurIPS 2024}.

#### **Option 2: Shortened descriptive link**

latex
\\bibitem{a2024a}
A et al. (2024a) Benchmarking Uncertainty Disentanglement:
Specialized Uncertainties for Specialized Tasks.

\\href{https://proceedings.neurips.cc/...}{NeurIPS 2024}.

### **Workshop Papers**

latex
\\bibitem{workshop2024}
Author, A. (2024). Paper Title With Proper Capitalization.

In \\emph{ICML 2024 Workshop on Trustworthy ML}.

### **Technical Reports**

latex
\\bibitem{report2024}
Author, B. (2024). Report Title: Maintaining Original Case.

Technical Report, Stanford University.

### **Preprints on Other Platforms**

* bioRxiv: `\href{url}{bioRxiv}`
* SSRN: `\href{url}{SSRN: paper-id}`
* OSF: `\href{url}{OSF Preprints}`

### **Blog Posts**

latex
\\bibitem{smith2024blog}
Smith, J. (2024, March 15). Understanding Neural Networks and LLMs \[Blog post\].
\\href{https://jsmith.com/neural-nets}{Personal Blog}.

Accessed: July 31, 2025\.

### **Online News Articles**

latex
\\bibitem{nyt2024}
Johnson, A. (2024, June 10). AI Breakthroughs in 2024: GPT-5 and Beyond. \\emph{The New York Times}.
\\href{https://nytimes.com/...}{Online}.

Accessed: July 31, 2025\.

### **PDF Documents**

latex
\\bibitem{amorin2024}
Amorin (2024). \\emph{Artificial Intelligence in Real Estate Appraisal} \[PDF\].
\\href{https://www.appraisalinstitute.org/...}{Appraisal Institute}.

Accessed: July 31, 2025\.

### **GitHub Repositories**

latex
\\bibitem{repo2024}
Author, C. (2024). PyTorch-Lightning: High-Performance ML Framework (Version 1.2) \[Computer software\].

\\href{https://github.com/user/repo}{GitHub: user/repo}.

## **Complete LaTeX Document Structure**

latex
\\documentclass{article}
\\usepackage{hyperref}
\\usepackage{url}

\\begin{document}

*% Your content with citations*
This is discussed in \\cite{damgard2015a} and further explored in \\cite{etal2023c}.
Recent web resources \\cite{amorin2024} provide additional context.

*% Hardcoded bibliography with preserved capitalization*
\\begin{thebibliography}{99}

\\bibitem{damgard2015a}
Damgård et al. Bounded Tamper Resilience: How to Go Beyond the Algebraic Barrier.
\\emph{Journal of Cryptology}, 30:152--190, 2015a.
doi: \\href{https://doi.org/10.1007/s00145-015-9218-0}{10.1007/s00145-015-9218-0}.

\\bibitem{etal2023c}
et al KZ (2023c) Don't Make Your LLM an Evaluation Benchmark Cheater.
\\href{https://arxiv.org/abs/2311.01964}{arXiv: 2311.01964}.

\\bibitem{amorin2024}
Amorin (2024). \\emph{Web Page by Amorin}.
\\href{https://www.appraisalinstitute.org/...}{Appraisal Institute}.
Accessed: July 31, 2025\.

\\end{thebibliography}

\\end{document}

## **Complete Python Pipeline Example with Case Preservation**

python
import re
from urllib.parse import urlparse
from datetime import datetime

class BibliographyConverter:
    def \_\_init\_\_(self):
        self.domain\_map \= {
            'neurips.cc': 'NeurIPS',
            'openreview.net': 'OpenReview',
            'aclweb.org': 'ACL Anthology',
            'ieee': 'IEEE Xplore',
            'springer': 'Springer',
            'mlr.press': 'MLR Press',
            'arxiv.org': 'arXiv',
            'github.com': 'GitHub',
        }

        *\# Common acronyms and proper nouns to preserve*
        self.preserve\_words \= {
            'llm', 'llms', 'gpt', 'bert', 'covid', 'covid-19',
            'ai', 'ml', 'nlp', 'rl', 'gan', 'gans', 'vae', 'vaes',
            'lstm', 'rnn', 'cnn', 'transformer', 'transformers',
            'pytorch', 'tensorflow', 'python', 'javascript',
            'github', 'arxiv', 'neurips', 'icml', 'iclr', 'cvpr',
            'acl', 'emnlp', 'naacl', 'ieee', 'aaai', 'ijcai'
        }

        *\# Map lowercase to proper case*
        self.case\_corrections \= {
            'llm': 'LLM',
            'llms': 'LLMs',
            'gpt': 'GPT',
            'bert': 'BERT',
            'covid': 'COVID',
            'covid-19': 'COVID-19',
            'ai': 'AI',
            'ml': 'ML',
            'nlp': 'NLP',
            'rl': 'RL',
            'gan': 'GAN',
            'gans': 'GANs',
            'vae': 'VAE',
            'vaes': 'VAEs',
            'lstm': 'LSTM',
            'rnn': 'RNN',
            'cnn': 'CNN',
            'pytorch': 'PyTorch',
            'tensorflow': 'TensorFlow',
            'python': 'Python',
            'javascript': 'JavaScript',
            'github': 'GitHub',
            'arxiv': 'arXiv',
            'neurips': 'NeurIPS',
            'icml': 'ICML',
            'iclr': 'ICLR',
            'cvpr': 'CVPR',
            'acl': 'ACL',
            'emnlp': 'EMNLP',
            'naacl': 'NAACL',
            'ieee': 'IEEE',
            'aaai': 'AAAI',
            'ijcai': 'IJCAI'
        }

    def correct\_common\_acronyms(self, text):
        """Correct common acronyms and proper nouns in text."""
        words \= text.split()
        corrected\_words \= \[\]

        for word in words:
            *\# Check if word (lowercase) needs correction*
            word\_lower \= word.lower().rstrip('.,;:\!?')
            punctuation \= word\[len(word\_lower):\]

            if word\_lower in self.case\_corrections:
                corrected\_words.append(self.case\_corrections\[word\_lower\] \+ punctuation)
            else:
                corrected\_words.append(word)

        return ' '.join(corrected\_words)

    def convert\_markdown\_to\_latex(self, citations, auto\_correct\_case\=True):
        """
        Convert a list of (key, citation) tuples to LaTeX bibliography.

        Args:
            citations: List of (key, citation\_text) tuples
            auto\_correct\_case: Whether to automatically correct common acronyms
        """
        latex\_entries \= \[\]

        for key, citation in citations:
            *\# Optionally correct common acronyms*
            if auto\_correct\_case:
                citation \= self.correct\_common\_acronyms(citation)

            *\# Determine citation type and convert appropriately*
            if 'doi:' in citation.lower():
                entry \= self.\_convert\_doi\_citation(citation, key)
            elif 'arxiv' in citation.lower():
                entry \= self.\_convert\_arxiv\_citation(citation, key)
            elif 'http' in citation:
                entry \= self.\_convert\_url\_citation(citation, key)
            else:
                entry \= self.\_convert\_basic\_citation(citation, key)

            latex\_entries.append(entry)

        *\# Combine into bibliography*
        bibliography \= "\\\\begin{thebibliography}{99}\\n\\n"
        bibliography \+= "\\n\\n".join(latex\_entries)
        bibliography \+= "\\n\\n\\\\end{thebibliography}"

        return bibliography

    def \_convert\_basic\_citation(self, citation, key):
        """Convert basic citation without URLs."""
        *\# Convert markdown links*
        citation \= re.sub(r'\\\[(\[^\\\]\]+)\\\]\\((\[^)\]+)\\)', r'\\\\href{\\2}{\\1}', citation)

        *\# Convert page ranges*
        citation \= re.sub(r'(\\d+)-(\\d+)', r'\\1--\\2', citation)

        *\# Add emphasis to journal names (if identifiable)*
        *\# This is a simple heuristic \- improve as needed*

        return f"\\\\bibitem{{{key}}}\\n{citation}"

    def \_convert\_doi\_citation(self, citation, key):
        """Convert citation with DOI."""
        return self.\_convert\_basic\_citation(citation, key)

    def \_convert\_arxiv\_citation(self, citation, key):
        """Convert arXiv citation."""
        return self.\_convert\_basic\_citation(citation, key)

    def \_convert\_url\_citation(self, citation, key):
        """Convert citation with generic URL."""
        return self.\_convert\_basic\_citation(citation, key)

*\# Usage example*
converter \= BibliographyConverter()

*\# Citations with incorrect case*
citations \= \[
    ("damgard2015a", "Damgård et al. Bounded tamper resilience: How to go beyond the algebraic barrier..."),
    ("etal2023c", "et al KZ (2023c) don't make your llm an evaluation benchmark cheater. https://arxiv.org/abs/2311.01964"),
    ("smith2024ai", "Smith J. (2024) ai and ml in healthcare: A comprehensive study of covid-19 applications. IEEE Transactions on AI."),
    ("workshop2024", "Lee et al. (2024) pytorch vs tensorflow: Performance analysis. neurips 2024 Workshop.")
\]

latex\_bibliography \= converter.convert\_markdown\_to\_latex(citations, auto\_correct\_case\=True)

print(latex\_bibliography)

## **Best Practices and Tips**

### **For Journal Submission**

1. **Keep original `.bib` file**: Store for future revisions
2. **Comment rather than delete**: Keep original `\bibliography{}` commands commented
3. **Verify formatting**: Ensure hardcoded format matches journal style
4. **Test thoroughly**: Compile multiple times to verify all references resolve
5. **Check capitalization**: Verify that all proper nouns, acronyms, and stylistic choices are preserved

### **Case Preservation Guidelines**

1. **Always check original sources**: When in doubt, visit the paper's official page
2. **Maintain author's intent**: Respect stylistic choices in titles (e.g., "eBay" not "Ebay")
3. **Be consistent**: If you correct "LLM" in one place, correct it everywhere
4. **Document corrections**: Keep a list of case corrections made for consistency
5. **Use protection in BibTeX**: When using `.bib` files, protect capitals with `{}`

### **General Guidelines**

1. **Consistency**: Use same format throughout bibliography
2. **Access dates**: Always include for web sources
3. **URL length**: Use domain names for very long URLs
4. **Document type**: Include \[PDF\], \[Video\], \[Blog post\] tags when relevant
5. **Journal compliance**: Follow specific guidelines (e.g., "Retrieved from" vs "Accessed")

### **Alternative: Using filecontents with Protected Capitals**

latex
\\begin{filecontents}{\\jobname.bib}
@article{smith2023,
  author \= {Smith, John},
  title \= {{Don't Make Your LLM an Evaluation Benchmark Cheater}},
  journal \= {Journal of {AI} Research},
  year \= {2023},
  volume \= {45},
  number \= {3},
  pages \= {123--145}
}

\\end{filecontents}

This approach embeds the bibliography in the document while maintaining BibTeX formatting advantages and protecting capitalization.

### **Common Patterns to Watch For**

1. **Contractions**: "Don't" → "don't" (incorrect)
2. **Acronyms**: "BERT", "GPT", "LSTM" → often lowercased
3. **Product names**: "GitHub", "PyTorch", "TensorFlow" → often lose their CamelCase
4. **Technical terms**: "JavaScript", "LaTeX" → often simplified
5. **Subtitles after colons**: Often incorrectly lowercased

By following these guidelines, you can ensure that your bibliography maintains the professional appearance and accuracy that authors intended when they titled their works.
