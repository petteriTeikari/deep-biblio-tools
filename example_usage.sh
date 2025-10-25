#!/bin/bash
# Example usage of deep-biblio-tools

echo "=== Deep Biblio Tools - Example Usage ==="
echo ""

# Set the directory containing your papers
PAPERS_DIR="$1"

if [ -z "$PAPERS_DIR" ]; then
    echo "Usage: $0 /path/to/papers/directory"
    echo ""
    echo "Example:"
    echo "  $0 ~/papers/scene_graphs/"
    echo ""
    exit 1
fi

# Check if directory exists
if [ ! -d "$PAPERS_DIR" ]; then
    echo "Error: Directory '$PAPERS_DIR' does not exist"
    exit 1
fi

echo "Processing papers in: $PAPERS_DIR"
echo ""

# Step 1: Initial processing (creates prompts)
echo "Step 1: Analyzing papers and creating prompts..."
python process_papers_with_cache.py "$PAPERS_DIR"

echo ""
echo "Step 2: Process the generated prompts with Claude"
echo "You'll find .prompt files in $PAPERS_DIR"
echo "Use these with Claude to generate comprehensive summaries"

echo ""
echo "Step 3: After processing, check cache status:"
python process_papers_with_cache.py "$PAPERS_DIR" --show-cache

echo ""
echo "Step 4: To force reprocess specific files:"
echo "python process_papers_with_cache.py '$PAPERS_DIR' --force-reprocess 'paper_name.html'"

echo ""
echo "=== Directory Structure Created ==="
echo "$PAPERS_DIR/"
echo " summaries/                    # Your comprehensive summaries go here"
echo " review/                       # Literature review will be generated here"
echo " paper_processing_cache.json   # Tracks processed files"
echo " *.prompt                      # Prompts for Claude processing"
