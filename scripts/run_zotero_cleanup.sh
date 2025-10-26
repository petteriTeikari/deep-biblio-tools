#!/bin/bash
# Master cleanup script for Zotero garbage entries
# This orchestrates the full cleanup workflow with safety checks

set -e  # Exit on error

PROJECT_ROOT="/Users/petteri/Dropbox/github-personal/deep-biblio-tools"
PAPER_DIR="/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review"

cd "$PROJECT_ROOT"

echo "================================================================"
echo "ZOTERO CLEANUP WORKFLOW"
echo "================================================================"
echo ""

# Step 1: List suspects
echo "Step 1: Listing suspect entries..."
echo "================================================================"
uv run --project "$PROJECT_ROOT" python3 scripts/zotero_list_suspects.py

if [ ! -f "zotero_suspects.json" ]; then
    echo "❌ No suspects file created. Nothing to clean up."
    exit 0
fi

# Check if suspects were found
SUSPECT_COUNT=$(python3 -c "import json; print(len(json.load(open('zotero_suspects.json'))))")
if [ "$SUSPECT_COUNT" = "0" ]; then
    echo "✅ No suspect entries found. Zotero is clean!"
    exit 0
fi

echo ""
echo "Found $SUSPECT_COUNT suspect entries."
echo ""

# Step 2: Dry-run deletion
echo "Step 2: Previewing deletion (DRY RUN)..."
echo "================================================================"
uv run --project "$PROJECT_ROOT" python3 scripts/zotero_delete_items.py \
    --file zotero_suspects.json \
    --dry-run

echo ""
echo "⚠️  Review the list above carefully!"
echo ""
read -p "Do you want to DELETE these entries? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deletion cancelled."
    exit 1
fi

# Step 3: Actually delete
echo ""
echo "Step 3: Deleting suspect entries..."
echo "================================================================"
uv run --project "$PROJECT_ROOT" python3 scripts/zotero_delete_items.py \
    --file zotero_suspects.json \
    --confirm

echo ""
echo "✅ Deletion complete!"
echo ""

# Step 4: Prepare URLs for re-adding
echo "Step 4: Extracting URLs for re-addition..."
echo "================================================================"

python3 << 'EOFPYTHON'
import json
suspects = json.load(open('zotero_suspects.json'))
urls = [s['url'] for s in suspects if s.get('url')]
with open('urls_to_readd.txt', 'w') as f:
    for url in urls:
        f.write(url + '\n')
print(f"Extracted {len(urls)} URLs to urls_to_readd.txt")
EOFPYTHON

if [ ! -f "urls_to_readd.txt" ]; then
    echo "⚠️  No URLs to re-add. Cleanup complete!"
    exit 0
fi

# Step 5: Dry-run re-addition
echo ""
echo "Step 5: Previewing re-addition (DRY RUN)..."
echo "================================================================"
uv run --project "$PROJECT_ROOT" python3 scripts/zotero_add_proper_entries.py \
    --urls urls_to_readd.txt \
    --dry-run

echo ""
echo "⚠️  Review the metadata preview above!"
echo ""
read -p "Do you want to ADD these entries with proper metadata? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Addition cancelled."
    echo "   URLs are in urls_to_readd.txt for manual processing."
    exit 1
fi

# Step 6: Actually add
echo ""
echo "Step 6: Adding entries with proper metadata..."
echo "================================================================"
uv run --project "$PROJECT_ROOT" python3 scripts/zotero_add_proper_entries.py \
    --urls urls_to_readd.txt \
    --confirm

echo ""
echo "================================================================"
echo "CLEANUP COMPLETE"
echo "================================================================"
echo ""
echo "Next steps:"
echo "1. Export Zotero collection to CSL JSON:"
echo "   Right-click 'dpp-fashion' → Export → CSL JSON"
echo "   Save to: $PAPER_DIR/mcp-draft-refined-v3.json"
echo ""
echo "2. Re-run author verification:"
echo "   python3 scripts/verify_author_names.py \\"
echo "     $PAPER_DIR/mcp-draft-refined-v3.md \\"
echo "     $PAPER_DIR/mcp-draft-refined-v3.json"
echo ""
