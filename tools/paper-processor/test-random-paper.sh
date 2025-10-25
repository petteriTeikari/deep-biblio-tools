#!/bin/bash
# Test script to summarize a random paper with improved compression

export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}"

# Test with BIM-based quantity takeoff paper
echo "Testing summarization on: BIM-based quantity takeoff paper"
echo "=================================================="

paper-processor summarize \
  "/home/petteri/Dropbox/LABs/KusiKasa/papers/scan2bim/biblio/bim/BIM-based quantity takeoff_ Current state and future opportunities - ScienceDirect.html" \
  -o "/home/petteri/Dropbox/LABs/KusiKasa/github/deep-biblio-tools/test_bim_takeoff_summary.md"

echo -e "\nSummary complete! Let's check the compression ratio..."

# Check if summary was created
if [ -f "test_bim_takeoff_summary.md" ]; then
    echo -e "\nSummary preview (first 1000 chars):"
    echo "-----------------------------------"
    head -c 1000 test_bim_takeoff_summary.md
    echo -e "\n..."

    # Count words
    words=$(wc -w < test_bim_takeoff_summary.md)
    echo -e "\nSummary word count: $words words"
fi
