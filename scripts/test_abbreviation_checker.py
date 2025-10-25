#!/usr/bin/env python3
"""Test the abbreviation checker with real examples."""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.utils.abbreviation_checker import AbbreviationChecker


def test_abbreviation_checker():
    """Test the abbreviation checker with various examples."""

    test_text = """
# Introduction

Machine Learning (ML) has become crucial in many domains. The use of ML algorithms
has increased dramatically over the past decade. Deep Learning (DL) is a subset of ML.

## Methods

We used LSTM networks for time series prediction. The LSTM architecture is well-suited
for sequential data. We also experimented with GRU cells as an alternative.

The SHAP values were calculated to provide model interpretability. For comparison,
we also used LIME for local explanations.

## Background

Convolutional Neural Networks (CNN) have revolutionized computer vision. Similarly,
RNNs have been successful in NLP tasks. The combination of CNN and RNN architectures
has led to powerful models.

## Technical Details

The API was designed following REST principles. Our SDK provides easy integration.
The system uses a CLI for advanced users and a GUI for beginners.

## Results

The UAD performed better than expected. We achieved 95% accuracy on the test set.
The use of GANs for data augmentation improved results significantly.

## Abbreviations Not Defined

Several techniques like NeRF and VAE were considered but not implemented.
The PCA analysis revealed interesting patterns in the data.

## References

[1] Smith et al. (2023) introduced the concept of Automated Valuation Models (AVM).
"""

    checker = AbbreviationChecker()
    issues, definitions = checker.check_document(test_text)

    print("Test Abbreviation Checker")
    print("=" * 80)

    print(f"\nFound {len(definitions)} defined abbreviations:")
    for defn in definitions:
        print(
            f"  Line {defn.line_number}: {defn.abbreviation} = {defn.full_form}"
        )

    print(f"\n\nFound {len(issues)} undefined abbreviations:")
    for issue in issues:
        print(f"  Line {issue.line_number}: {issue.abbreviation}")
        print(f"    Context: {issue.context}")
        if issue.suggested_definition:
            print(
                f"    Suggestion: {issue.abbreviation} = {issue.suggested_definition}"
            )
        print()

    # Test with a real file
    print("\n" + "=" * 80)
    print("Testing on real file excerpt")
    print("=" * 80)

    real_text = """
The statistical and machine learning literature provides sophisticated frameworks for uncertainty quantification. Der Kiureghian and Ditlevsen ([2009](https://doi.org/10.1016/j.strusafe.2008.06.020)) formalize the aleatory/epistemic distinction and methods for propagation through complex systems. For neural network models, several approaches have emerged:

The work of Lundberg and Lee ([2017](https://arxiv.org/abs/1705.07874)) developed SHAP values for model interpretation. SHAP provides both local and global explanations by computing feature attributions based on Shapley values from cooperative game theory.

Similarly, Ribeiro et al. ([2016](https://arxiv.org/abs/1602.04938)) introduced LIME for explaining individual predictions of any classifier. LIME works by approximating the model locally with an interpretable model.

Modern AVMs leverage deep learning architectures including CNNs for image analysis and RNNs for sequential data processing. The integration of NLP techniques has enabled better handling of textual property descriptions.
"""

    issues2, definitions2 = checker.check_document(real_text)

    print(f"\nFound {len(definitions2)} defined abbreviations:")
    for defn in definitions2:
        print(
            f"  Line {defn.line_number}: {defn.abbreviation} = {defn.full_form}"
        )

    print(f"\n\nFound {len(issues2)} undefined abbreviations:")
    for issue in issues2:
        print(f"  Line {issue.line_number}: {issue.abbreviation}")
        if issue.suggested_definition:
            print(
                f"    Suggestion: {issue.abbreviation} = {issue.suggested_definition}"
            )


if __name__ == "__main__":
    test_abbreviation_checker()
