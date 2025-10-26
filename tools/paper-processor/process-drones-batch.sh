#!/bin/bash
# Process all papers in drones folder with comprehensive monitoring

export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}"

INPUT_DIR="/home/petteri/Dropbox/LABs/github-personal/papers/scan2bim/biblio/drones"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="drones_processing_${TIMESTAMP}.log"

echo "Starting batch processing of drones papers" | tee $LOG_FILE
echo "==========================================" | tee -a $LOG_FILE
echo "Start time: $(date)" | tee -a $LOG_FILE
echo "Input directory: $INPUT_DIR" | tee -a $LOG_FILE

# Count files
echo -e "\nCounting files..." | tee -a $LOG_FILE
HTML_COUNT=$(find "$INPUT_DIR" -name "*.html" -o -name "*.htm" 2>/dev/null | wc -l)
PDF_COUNT=$(find "$INPUT_DIR" -name "*.pdf" 2>/dev/null | wc -l)
XML_COUNT=$(find "$INPUT_DIR" -name "*.xml" 2>/dev/null | wc -l)
TOTAL_COUNT=$((HTML_COUNT + PDF_COUNT + XML_COUNT))

echo "Found files:" | tee -a $LOG_FILE
echo "  HTML/HTM: $HTML_COUNT" | tee -a $LOG_FILE
echo "  PDF: $PDF_COUNT" | tee -a $LOG_FILE
echo "  XML: $XML_COUNT" | tee -a $LOG_FILE
echo "  Total: $TOTAL_COUNT" | tee -a $LOG_FILE

# Phase 1: Extract all papers
echo -e "\n\nPHASE 1: EXTRACTION" | tee -a $LOG_FILE
echo "===================" | tee -a $LOG_FILE
START_EXTRACT=$(date +%s)

paper-processor batch-extract \
  "$INPUT_DIR" \
  --pattern all_formats \
  --parallel \
  --retry-failed \
  --timeout 60 2>&1 | tee -a $LOG_FILE

END_EXTRACT=$(date +%s)
EXTRACT_TIME=$((END_EXTRACT - START_EXTRACT))
echo -e "\nExtraction completed in $EXTRACT_TIME seconds" | tee -a $LOG_FILE

# Count extracted files
EXTRACTED_COUNT=$(find "$INPUT_DIR/extracted" -name "*.md" 2>/dev/null | wc -l)
echo "Successfully extracted: $EXTRACTED_COUNT files" | tee -a $LOG_FILE

# Phase 2: Summarize all papers
echo -e "\n\nPHASE 2: SUMMARIZATION" | tee -a $LOG_FILE
echo "======================" | tee -a $LOG_FILE
START_SUMMARY=$(date +%s)

# Run with debug mode to monitor compression ratios
paper-processor summarize-folder \
  "$INPUT_DIR" \
  --pattern all_formats \
  --parallel \
  --skip-existing \
  --debug \
  --retry-failed \
  --timeout 90 2>&1 | tee -a $LOG_FILE

END_SUMMARY=$(date +%s)
SUMMARY_TIME=$((END_SUMMARY - START_SUMMARY))
echo -e "\nSummarization completed in $SUMMARY_TIME seconds" | tee -a $LOG_FILE

# Count summary files
SUMMARY_COUNT=$(find "$INPUT_DIR/summaries" -name "*_summary.md" 2>/dev/null | wc -l)
echo "Successfully summarized: $SUMMARY_COUNT files" | tee -a $LOG_FILE

# Phase 3: Analysis
echo -e "\n\nPHASE 3: ANALYSIS" | tee -a $LOG_FILE
echo "=================" | tee -a $LOG_FILE

# Calculate compression statistics
echo -e "\nCalculating compression statistics..." | tee -a $LOG_FILE

python3 - << 'EOF' | tee -a $LOG_FILE
import os
from pathlib import Path
import statistics

input_dir = Path("/home/petteri/Dropbox/LABs/github-personal/papers/scan2bim/biblio/drones")
extracted_dir = input_dir / "extracted"
summaries_dir = input_dir / "summaries"

compressions = []
word_counts = []
summary_word_counts = []

if extracted_dir.exists() and summaries_dir.exists():
    for summary_file in summaries_dir.glob("*_summary.md"):
        # Find corresponding extracted file
        base_name = summary_file.stem.replace("_summary", "")
        extracted_file = extracted_dir / f"{base_name}.md"

        if extracted_file.exists():
            # Get file sizes
            extracted_size = extracted_file.stat().st_size
            summary_size = summary_file.stat().st_size
            compression_ratio = (summary_size / extracted_size) * 100

            # Count words
            extracted_text = extracted_file.read_text(encoding='utf-8')
            summary_text = summary_file.read_text(encoding='utf-8')
            extracted_words = len(extracted_text.split())
            summary_words = len(summary_text.split())

            compressions.append(compression_ratio)
            word_counts.append(extracted_words)
            summary_word_counts.append(summary_words)

if compressions:
    print(f"\nCompression Statistics:")
    print(f"  Average compression: {statistics.mean(compressions):.1f}%")
    print(f"  Min compression: {min(compressions):.1f}%")
    print(f"  Max compression: {max(compressions):.1f}%")
    print(f"  Std deviation: {statistics.stdev(compressions):.1f}%" if len(compressions) > 1 else "  Std deviation: N/A")

    print(f"\nWord Count Statistics:")
    print(f"  Average original: {statistics.mean(word_counts):.0f} words")
    print(f"  Average summary: {statistics.mean(summary_word_counts):.0f} words")

    # Check how many are in target range (10-25%)
    in_range = sum(1 for c in compressions if 10 <= c <= 25)
    print(f"\nTarget Range Analysis (10-25%):")
    print(f"  In range: {in_range}/{len(compressions)} ({in_range/len(compressions)*100:.1f}%)")
    print(f"  Below range: {sum(1 for c in compressions if c < 10)}")
    print(f"  Above range: {sum(1 for c in compressions if c > 25)}")
else:
    print("No compression data available")
EOF

# Phase 4: Performance Summary
echo -e "\n\nPERFORMANCE SUMMARY" | tee -a $LOG_FILE
echo "===================" | tee -a $LOG_FILE
TOTAL_TIME=$((END_SUMMARY - START_EXTRACT))

echo "Total processing time: $TOTAL_TIME seconds ($((TOTAL_TIME/60)) minutes)" | tee -a $LOG_FILE
echo "Extraction phase: $EXTRACT_TIME seconds" | tee -a $LOG_FILE
echo "Summarization phase: $SUMMARY_TIME seconds" | tee -a $LOG_FILE
echo "Average time per file: $((TOTAL_TIME/TOTAL_COUNT)) seconds" | tee -a $LOG_FILE

# Check for failures
echo -e "\nChecking for failures..." | tee -a $LOG_FILE
FAILED_EXTRACT=$((TOTAL_COUNT - EXTRACTED_COUNT))
FAILED_SUMMARY=$((EXTRACTED_COUNT - SUMMARY_COUNT))

if [ $FAILED_EXTRACT -gt 0 ]; then
    echo "WARNING: $FAILED_EXTRACT files failed during extraction" | tee -a $LOG_FILE
fi

if [ $FAILED_SUMMARY -gt 0 ]; then
    echo "WARNING: $FAILED_SUMMARY files failed during summarization" | tee -a $LOG_FILE
fi

# List any error patterns
echo -e "\nScanning for error patterns..." | tee -a $LOG_FILE
grep -i "error\|failed\|timeout\|rate.*limit" $LOG_FILE | sort | uniq -c | head -10 | tee -a $LOG_FILE

# Final status
echo -e "\n\nFINAL STATUS" | tee -a $LOG_FILE
echo "============" | tee -a $LOG_FILE
echo "End time: $(date)" | tee -a $LOG_FILE
echo "Log file: $LOG_FILE" | tee -a $LOG_FILE
echo "Extracted files: $INPUT_DIR/extracted/" | tee -a $LOG_FILE
echo "Summary files: $INPUT_DIR/summaries/" | tee -a $LOG_FILE

# Create a summary report
REPORT_FILE="drones_summary_report_${TIMESTAMP}.md"
cat > $REPORT_FILE << EOF
# Drones Papers Processing Report

Generated: $(date)

## Overview
- **Input Directory**: $INPUT_DIR
- **Total Files**: $TOTAL_COUNT
- **Successfully Extracted**: $EXTRACTED_COUNT
- **Successfully Summarized**: $SUMMARY_COUNT
- **Total Processing Time**: $((TOTAL_TIME/60)) minutes

## File Types
- HTML/HTM: $HTML_COUNT
- PDF: $PDF_COUNT
- XML: $XML_COUNT

## Performance
- Extraction Time: $EXTRACT_TIME seconds
- Summarization Time: $SUMMARY_TIME seconds
- Average per File: $((TOTAL_TIME/TOTAL_COUNT)) seconds

## Success Rate
- Extraction: $((EXTRACTED_COUNT*100/TOTAL_COUNT))%
- Summarization: $((SUMMARY_COUNT*100/EXTRACTED_COUNT))%

## Output Locations
- Extracted: $INPUT_DIR/extracted/
- Summaries: $INPUT_DIR/summaries/
- Log File: $LOG_FILE
EOF

echo -e "\nProcessing complete! Summary report saved to: $REPORT_FILE" | tee -a $LOG_FILE
echo "Sweet dreams! The results will be waiting for you." | tee -a $LOG_FILE
