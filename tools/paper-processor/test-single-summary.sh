#!/bin/bash
# Test script to verify improved compression ratios with a single file

export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}"

# Test with a single file first to verify compression ratio
echo "Testing summarization with improved compression (target: 10-25%)..."

# Use the original HTML file that was previously over-compressed with debug mode
paper-processor summarize-folder \
  "/home/petteri/Dropbox/LABs/github-personal/papers/scan2bim/biblio/bim" \
  --pattern "2D–3D fusion approach for improved point cloud segmentation - ScienceDirect.html" \
  --debug \
  -o "/home/petteri/Dropbox/LABs/github-personal/papers/scan2bim/biblio/bim/summaries_test"

echo "Test complete! Check the file size ratio."
