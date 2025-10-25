#!/bin/bash
# Run compression regression test

export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}"

echo "Running Compression Regression Test"
echo "==================================="

# Check if we need to save baseline
if [ "$1" == "--save-baseline" ]; then
    echo "Saving new baseline..."
    python3 tests/test_compression_regression.py --save-baseline
else
    python3 tests/test_compression_regression.py
fi

echo -e "\nTest complete!"

# Show baseline if it exists
if [ -f "tests/compression_baseline.json" ]; then
    echo -e "\nCurrent baseline:"
    cat tests/compression_baseline.json | python3 -m json.tool | head -20
fi
