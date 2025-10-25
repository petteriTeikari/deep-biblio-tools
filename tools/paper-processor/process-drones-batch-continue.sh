#!/bin/bash
# Continue processing drones papers (extraction already done, just summarize)

export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}"

INPUT_DIR="/home/petteri/Dropbox/LABs/KusiKasa/papers/scan2bim/biblio/drones"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="drones_processing_continue_${TIMESTAMP}.log"

echo "Continuing batch processing of drones papers (summarization)" | tee $LOG_FILE
echo "============================================================" | tee -a $LOG_FILE
echo "Start time: $(date)" | tee -a $LOG_FILE
echo "Input directory: $INPUT_DIR" | tee -a $LOG_FILE

# Count extracted files
EXTRACTED_COUNT=$(find "$INPUT_DIR/extracted" -name "*.md" 2>/dev/null | wc -l)
echo -e "\nFound $EXTRACTED_COUNT extracted files ready for summarization" | tee -a $LOG_FILE

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

python3 - << 'EOF' 2>&1 | tee -a $LOG_FILE
import os
from pathlib import Path
import statistics

input_dir = Path("/home/petteri/Dropbox/LABs/KusiKasa/papers/scan2bim/biblio/drones")
extracted_dir = input_dir / "extracted"
summaries_dir = input_dir / "summaries"

compressions = []
word_counts = []
summary_word_counts = []
file_details = []

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
            try:
                extracted_text = extracted_file.read_text(encoding='utf-8')
                summary_text = summary_file.read_text(encoding='utf-8')
                extracted_words = len(extracted_text.split())
                summary_words = len(summary_text.split())

                compressions.append(compression_ratio)
                word_counts.append(extracted_words)
                summary_word_counts.append(summary_words)

                file_details.append({
                    'name': base_name[:50] + '...' if len(base_name) > 50 else base_name,
                    'original_words': extracted_words,
                    'summary_words': summary_words,
                    'compression': compression_ratio
                })
            except Exception as e:
                print(f"Error processing {base_name}: {e}")

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
    print(f"  Below range (<10%): {sum(1 for c in compressions if c < 10)}")
    print(f"  Above range (>25%): {sum(1 for c in compressions if c > 25)}")

    print(f"\nPer-File Details:")
    print(f"{'File':<52} {'Original':>10} {'Summary':>10} {'Compression':>12}")
    print("-" * 86)
    for detail in sorted(file_details, key=lambda x: x['compression']):
        print(f"{detail['name']:<52} {detail['original_words']:>10,} {detail['summary_words']:>10,} {detail['compression']:>11.1f}%")
else:
    print("No compression data available")
EOF

# Performance Summary
echo -e "\n\nPERFORMANCE SUMMARY" | tee -a $LOG_FILE
echo "===================" | tee -a $LOG_FILE

echo "Summarization time: $SUMMARY_TIME seconds" | tee -a $LOG_FILE
echo "Files summarized: $SUMMARY_COUNT" | tee -a $LOG_FILE
if [ $SUMMARY_COUNT -gt 0 ]; then
    echo "Average time per summary: $((SUMMARY_TIME/SUMMARY_COUNT)) seconds" | tee -a $LOG_FILE
fi

# Check for failures
echo -e "\nChecking for failures..." | tee -a $LOG_FILE
FAILED_SUMMARY=$((EXTRACTED_COUNT - SUMMARY_COUNT))

if [ $FAILED_SUMMARY -gt 0 ]; then
    echo "WARNING: $FAILED_SUMMARY files failed during summarization" | tee -a $LOG_FILE
fi

# List any error patterns
echo -e "\nScanning for error patterns..." | tee -a $LOG_FILE
grep -i "error\|failed\|timeout\|rate.*limit" $LOG_FILE | grep -v "Scanning for error" | sort | uniq -c | head -10

# Final status
echo -e "\n\nFINAL STATUS" | tee -a $LOG_FILE
echo "============" | tee -a $LOG_FILE
echo "End time: $(date)" | tee -a $LOG_FILE
echo "Log file: $LOG_FILE" | tee -a $LOG_FILE
echo "Summary files: $INPUT_DIR/summaries/" | tee -a $LOG_FILE

# Create final report
REPORT_FILE="drones_final_report_${TIMESTAMP}.md"
cat > $REPORT_FILE << EOF
# Drones Papers Processing Final Report

Generated: $(date)

## Summary Results
- **Total Extracted Files**: $EXTRACTED_COUNT
- **Successfully Summarized**: $SUMMARY_COUNT
- **Failed**: $FAILED_SUMMARY
- **Processing Time**: $SUMMARY_TIME seconds

## Output
- Summary Files: $INPUT_DIR/summaries/
- Log File: $LOG_FILE

## Notes
- One file was renamed due to excessive length
- Check renamed_files_mapping.txt for details
EOF

echo -e "\nProcessing complete! Final report saved to: $REPORT_FILE" | tee -a $LOG_FILE
echo "Sweet dreams! The results are ready for your review." | tee -a $LOG_FILE
