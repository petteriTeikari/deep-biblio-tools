#!/bin/bash
# Test script with debug mode and shorter paper

export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}"

# First extract the paper to see its size
echo "Step 1: Extracting paper to check size..."
paper-processor extract \
  "/home/petteri/Dropbox/LABs/github-personal/papers/scan2bim/biblio/bim/BIM-based quantity takeoff_ Current state and future opportunities - ScienceDirect.html" \
  -o "test_extract.md"

if [ -f "test_extract.md" ]; then
    words=$(wc -w < test_extract.md)
    size=$(du -h test_extract.md | cut -f1)
    echo "Extracted paper: $words words, $size"

    # Show first few lines
    echo -e "\nFirst 500 characters of extracted content:"
    head -c 500 test_extract.md
    echo "..."
fi

echo -e "\n\nStep 2: Creating summary (this may take 30-60 seconds)..."
# Now try summarization with folder command which has better error handling
paper-processor summarize-folder \
  "/home/petteri/Dropbox/LABs/github-personal/papers/scan2bim/biblio/bim" \
  --pattern "BIM-based quantity takeoff_ Current state and future opportunities - ScienceDirect.html" \
  --debug \
  -o "test_summaries" \
  --timeout 90

echo -e "\nChecking results..."
if [ -d "test_summaries" ]; then
    ls -la test_summaries/
fi
