# Table Width Calculation Error in LaTeX Output

## Problem Description

When converting markdown tables to LaTeX, especially tables with many columns, the generated LaTeX often fails to compile with the error:
```
! Missing number, treated as zero.
<to be read again>
                   (
```

## Root Cause Analysis

The issue occurs in tables where pandoc generates column specifications like:
```latex
\begin{tabular}[]{@{}
  >{\raggedright\arraybackslash}p{(0.5\textwidth - 16\tabcolsep) * 0.1111}
  >{\raggedright\arraybackslash}p{(0.5\textwidth - 16\tabcolsep) * 0.1111}
  ...
```

### Problems:
1. **Negative widths**: When `16\tabcolsep` is greater than `0.5\textwidth`, the calculation becomes negative
2. **Too many columns**: With 9 columns, each getting 0.1111 (11.11%) of the width, the total exceeds 100%
3. **Two-column mode**: In two-column documents, `0.5\textwidth` is already narrow, making the problem worse

## Example Case

From UADReview_v4d.md conversion:
- Table with 9 columns
- Each column width: `(0.5\textwidth - 16\tabcolsep) * 0.1111`
- Total width: 9 × 11.11% = 99.99% of (0.5\textwidth - 16\tabcolsep)
- When 16\tabcolsep > 0.5\textwidth, LaTeX sees negative numbers

## Solution Approaches

### 1. Use longtable for wide tables
Instead of regular tabular, use longtable which handles column widths better:
```latex
\begin{longtable}[]{@{}lllllllll@{}}
```

### 2. Override pandoc's column width calculations
Post-process the LaTeX to replace problematic width calculations with simpler ones:
- Replace `p{(0.5\textwidth - 16\tabcolsep) * X}` with `p{X\textwidth}`
- Or use fixed widths for narrow columns

### 3. Detect wide tables and use different strategies
- Tables with >6 columns: use longtable with 'l' columns
- Tables with 4-6 columns: use calculated widths
- Tables with <4 columns: use pandoc defaults

## Temporary Workaround

Currently, users need to manually edit the generated .tex file to fix table specifications.

## Permanent Fix Required

The LaTeX builder needs to:
1. Detect problematic table specifications
2. Calculate safe column widths based on actual column count and document layout
3. Use appropriate table environments (tabular vs longtable) based on table characteristics
