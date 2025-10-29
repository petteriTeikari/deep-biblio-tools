# LaTeX Citation Commands Guide

## Overview
LaTeX provides different citation commands for different contexts. Using the wrong command results in incorrect formatting (e.g., double parentheses). This guide explains when to use `\cite` vs `\citep`.

## Citation Commands

### `\cite{}` - Textual Citation (No Parentheses)
Use when the citation is part of the sentence flow and you DON'T want parentheses around it.

**Examples:**
- ✅ "as documented by \cite{wu2015}" → "as documented by Wu et al. (2015)"
- ✅ "According to \cite{smith2020}, the results..." → "According to Smith (2020), the results..."
- ✅ "\cite{jones2019} found that..." → "Jones (2019) found that..."

### `\citep{}` - Parenthetical Citation (With Parentheses)
Use when the citation is a parenthetical reference and you WANT parentheses around it.

**Examples:**
- ✅ "algorithmic accountability \citep{diakopoulos2015}" → "algorithmic accountability (Diakopoulos, 2015)"
- ✅ "Previous studies \citep{brown2018} showed..." → "Previous studies (Brown, 2018) showed..."
- ✅ "This phenomenon is well-documented \citep{lee2021}." → "This phenomenon is well-documented (Lee, 2021)."

## Common Mistakes and Fixes

### 1. Double Parentheses
**Wrong:** "algorithmic accountability (\citep{diakopoulos2015})"
**Result:** "algorithmic accountability ((Diakopoulos, 2015))" ❌
**Fix:** "algorithmic accountability \citep{diakopoulos2015}"
**Result:** "algorithmic accountability (Diakopoulos, 2015)" ✅

### 2. Missing Parentheses
**Wrong:** "as documented by \citep{wu2015}"
**Result:** "as documented by (Wu et al., 2015)" ❌
**Fix:** "as documented by \cite{wu2015}"
**Result:** "as documented by Wu et al. (2015)" ✅

### 3. Multiple Sequential Citations
**Wrong:** "(\citep{akerlof1970}; \citep{stiglitz2000})"
**Result:** "((Akerlof, 1970); (Stiglitz, 2000))" ❌
**Fix:** "\citep{akerlof1970, stiglitz2000}"
**Result:** "(Akerlof, 1970; Stiglitz, 2000)" ✅

## Automatic Conversion Rules

1. **Remove existing parentheses around \citep:**
   - `(\citep{key})` → `\citep{key}`
   - `[\citep{key}]` → `\citep{key}`

2. **Convert \citep to \cite when preceded by prepositions:**
   - `by \citep{key}` → `by \cite{key}`
   - `from \citep{key}` → `from \cite{key}`
   - `according to \citep{key}` → `according to \cite{key}`
   - `following \citep{key}` → `following \cite{key}`

3. **Combine multiple adjacent citations:**
   - `\citep{key1}; \citep{key2}` → `\citep{key1, key2}`
   - `(\citep{key1}; \citep{key2})` → `\citep{key1, key2}`
   - `\citep{key1}, \citep{key2}` → `\citep{key1, key2}`

## Bibliography Style Compatibility
These rules apply to natbib-compatible styles including:
- `spbasic_pt` (our default)
- `plainnat`
- `abbrvnat`
- Other natbib styles

## Implementation Note
When processing markdown to LaTeX, the converter should:
1. Default to `\citep{}` for all citations initially
2. Apply the automatic conversion rules above
3. Preserve any manually specified `\cite{}` commands
