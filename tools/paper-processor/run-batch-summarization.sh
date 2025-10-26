#!/bin/bash
# Script to run batch summarization with API key

export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}"

# Run paper summarization with all features
paper-processor summarize-folder \
  "/home/petteri/Dropbox/LABs/github-personal/papers/scan2bim/biblio/bim" \
  --pattern all_formats \
  --parallel \
  --skip-existing \
  --debug \
  --timeout 60

echo "Summarization complete!"
