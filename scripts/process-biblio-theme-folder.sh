#!/bin/bash
# Script to process a bibliography theme folder with proper 25% comprehensive summaries

# Check if folder path is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <theme_folder_path>"
    echo "Example: $0 /path/to/papers/folder"
    exit 1
fi

THEME_FOLDER="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Validate folder exists
if [ ! -d "$THEME_FOLDER" ]; then
    echo "Error: Theme folder does not exist: $THEME_FOLDER"
    exit 1
fi

echo "============================================"
echo "Bibliography Theme Folder Processing"
echo "============================================"
echo "Folder: $THEME_FOLDER"
echo ""
echo "This script will process academic papers in the folder and create:"
echo "  - Extracted markdown content"
echo "  - 25% comprehensive summaries"
echo ""
echo "Please provide context about this collection of papers:"
echo "(e.g., 'BIM and point cloud processing', 'deep learning in construction', etc.)"
echo -n "Theme/Context: "
read THEME_CONTEXT
echo ""

echo "How would you like the findings contextualized in the final literature review?"
echo "(e.g., 'And if you could have a final chapter contextualizing the learnings for scan-to-bim solutions')"
echo -n "Contextualization: "
read CONTEXTUALIZATION
echo ""

echo "Processing papers related to: $THEME_CONTEXT"
echo "Contextualization approach: $CONTEXTUALIZATION"
echo "============================================"

# Create output directories
SUMMARIES_DIR="$THEME_FOLDER/summaries"
MARKDOWN_DIR="$THEME_FOLDER/markdown_parse"

mkdir -p "$SUMMARIES_DIR"
mkdir -p "$MARKDOWN_DIR"

# Save theme context and contextualization
echo "$THEME_CONTEXT" > "$THEME_FOLDER/.theme_context"
echo "$CONTEXTUALIZATION" > "$THEME_FOLDER/.contextualization"
echo "Configuration saved to: $THEME_FOLDER/.theme_context and .contextualization"
echo ""

# Count HTML files
TOTAL_FILES=$(find "$THEME_FOLDER" -maxdepth 1 -name "*.html" -not -name "*_files" | wc -l)
echo "Found $TOTAL_FILES HTML files to process"
echo ""

# Process each HTML file
PROCESSED=0
FAILED=0

find "$THEME_FOLDER" -maxdepth 1 -name "*.html" -not -name "*_files" | while read -r HTML_FILE; do
    BASENAME=$(basename "$HTML_FILE" .html)
    PROCESSED=$((PROCESSED + 1))

    echo "[$PROCESSED/$TOTAL_FILES] Processing: $(basename "$HTML_FILE")"

    # Extract paper content
    EXTRACTED_FILE="$MARKDOWN_DIR/${BASENAME}.md"
    echo "  - Extracting content..."

    if python3 "$PROJECT_ROOT/src/parsers/extract_sciencedirect_paper.py" "$HTML_FILE" "$EXTRACTED_FILE" 2>/dev/null; then
        # Get file size for calculating 25% summary
        if [ -f "$EXTRACTED_FILE" ]; then
            FILE_SIZE=$(wc -c < "$EXTRACTED_FILE")
            TARGET_SIZE=$((FILE_SIZE / 4))  # 25% of original

            # Create and save prompt
            PROMPT_FILE="$THEME_FOLDER/${BASENAME}.prompt"
            echo "Creating prompt for: ${BASENAME}.html" | tee "$PROMPT_FILE"
            echo "  Original size: $(numfmt --to=iec $FILE_SIZE)" | tee -a "$PROMPT_FILE"
            echo "  Target size: $(numfmt --to=iec $TARGET_SIZE) (25%)" | tee -a "$PROMPT_FILE"
            echo "  Theme context: $THEME_CONTEXT" >> "$PROMPT_FILE"
            echo "  Prompt saved to: $PROMPT_FILE"

            # Create comprehensive summary
            SUMMARY_FILE="$SUMMARIES_DIR/${BASENAME}_comprehensive_summary.md"
            echo "  - Creating 25% summary..."

            if python3 "$PROJECT_ROOT/src/processors/create_literature_summary.py" "$EXTRACTED_FILE" "$SUMMARY_FILE"; then
                echo "  [SUCCESS] Summary created"
            else
                echo "  [FAILED] Failed to create summary"
                FAILED=$((FAILED + 1))
            fi
        else
            echo "  [FAILED] Failed to extract content"
            FAILED=$((FAILED + 1))
        fi
    else
        echo "  [FAILED] Failed to parse HTML file"
        FAILED=$((FAILED + 1))
    fi

    echo ""
done

# Summary report
echo "============================================"
echo "Processing Complete!"
echo "  - Total files: $TOTAL_FILES"
echo "  - Successfully processed: $((TOTAL_FILES - FAILED))"
echo "  - Failed: $FAILED"
echo ""
echo "Output locations:"
echo "  - Extracted content: $MARKDOWN_DIR"
echo "  - Comprehensive summaries: $SUMMARIES_DIR"
echo "============================================"

# Ask if user wants to create a comprehensive literature review
echo ""
echo "Would you like to create a comprehensive literature review from all summaries? (y/n)"
read -r CREATE_REVIEW

if [[ "$CREATE_REVIEW" == "y" || "$CREATE_REVIEW" == "Y" ]]; then
    echo ""
    echo "Creating comprehensive literature review..."
    REVIEW_FILE="$THEME_FOLDER/literature_review_$(date +%Y%m%d_%H%M%S).md"

    # Create the review using a separate script
    if python3 "$PROJECT_ROOT/src/processors/create_theme_review.py" \
        "$SUMMARIES_DIR" \
        "$REVIEW_FILE" \
        "$THEME_CONTEXT" \
        "$CONTEXTUALIZATION"; then
        echo "[SUCCESS] Literature review created: $REVIEW_FILE"
    else
        echo "[FAILED] Failed to create literature review"
    fi
fi
