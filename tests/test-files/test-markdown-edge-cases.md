# Edge Cases for Markdown Validation Testing

This file contains intentionally problematic markdown patterns to test validation.

## Test 1: Valid Citations (Should Pass)

Recent work by [Abaza et al. (2024)](https://doi.org/10.1145/3626091) shows timing jitters.
The study by [Alqudsi and Makaraci (2025)](https://doi.org/10.1234/example) discusses UAV swarms.

## Test 2: Unmatched Brackets (Should Fail)

This citation is missing closing bracket: [Abaza et al. (2024](https://doi.org/10.1145/3626091)

This citation is missing closing parenthesis: [Abaza et al. (2024](https://doi.org/10.1145/3626091

## Test 3: Valid Table (Should Pass)

| Method | Accuracy | Speed  |
|--------|----------|--------|
| A      | 95%      | Fast   |
| B      | 92%      | Slow   |
| C      | 98%      | Medium |

## Test 4: Malformed Table - Column Count Mismatch (Should Fail)

| Method | Accuracy | Speed  |
|--------|----------|--------|
| A      | 95%      | Fast   |
| B      | 92%      |        |  <!-- Missing Speed column -->
| C      | 98%      | Medium | Extra |  <!-- Extra column -->

## Test 5: Malformed Table - Missing Header Separator (Should Fail)

| Method | Accuracy | Speed  |
| A      | 95%      | Fast   |
| B      | 92%      | Slow   |

## Test 6: Valid Nested Lists (Should Pass - Level 3 or Less)

- Level 1
  - Level 2
    - Level 3
      - This should still be acceptable

## Test 7: Special Characters That Need Escaping

Currency: $50-200 should be escaped as \$50-200
Percentages: 95% accuracy
Underscores: variable_name should be variable\_name
Ampersands: A & B should be A \& B

## Test 8: Empty Citation Link (Should Fail)

This is an empty citation: [Author (2024)]()

## Test 9: Citation with Invalid URL (Should Warn)

This has invalid URL: [Author (2024)](not-a-valid-url)

## Test 10: Unicode Characters (Should Be Handled)

Em dash: — should convert to ---
En dash: – should convert to --
Smart quotes: "text" should convert to ``text''
Less than or equal: ≤ should convert to \leq
Multiplication: × should convert to \times
