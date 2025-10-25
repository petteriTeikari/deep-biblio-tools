# Regex Removal Best Practices

## Executive Summary

This document captures best practices for systematically removing regex usage from Python codebases, based on the successful elimination of 200+ regex patterns from deep-biblio-tools. These practices ensure maintainable, readable, and performant code without regex dependencies.

## Strategic Framework

### Decision Matrix: When to Remove Regex

| Factor | Remove Regex | Consider Keeping |
|--------|-------------|------------------|
| **Pattern Complexity** | Simple patterns (prefix, suffix, contains) | Extremely complex with proven performance needs |
| **Maintenance Frequency** | Code changed often | Legacy code rarely touched |
| **Team Expertise** | Team has low regex skills | Team has regex experts |
| **Performance Critical** | Non-critical paths | Proven performance bottlenecks |
| **Error Rate** | High bug reports | Stable, tested patterns |
| **Readability** | Regex obfuscates logic | Simple, well-documented patterns |

### Cost-Benefit Analysis Template

```python
# Before making the decision, evaluate:
class RegexRemovalAssessment:
    def __init__(self, pattern, usage_context):
        self.complexity_score = self.assess_complexity(pattern)
        self.maintenance_burden = self.assess_maintenance(usage_context)
        self.performance_impact = self.benchmark_alternatives(pattern)
        self.team_readability = self.survey_team_understanding(pattern)

    def should_remove(self) -> bool:
        """Decide whether to remove regex based on weighted factors."""
        return (
            self.complexity_score < 7 and  # Not too complex to replace
            self.maintenance_burden > 5 and  # High maintenance cost
            self.performance_impact < 1.5 and  # <50% performance loss
            self.team_readability < 6  # Team struggles with regex
        )
```

## Implementation Methodology

### Phase 1: Discovery and Inventory
```bash
#!/bin/bash
# discovery_script.sh - Comprehensive regex inventory

echo "=== REGEX DISCOVERY REPORT ==="
echo "Generated: $(date)"
echo

echo "🔍 Finding all regex imports..."
echo "Files with 'import re':"
grep -r "import re" --include="*.py" . | grep -v "# Banned" | wc -l
echo

echo "🔍 Finding all regex method calls..."
echo "Total re. method calls:"
grep -r "re\." --include="*.py" . | grep -v "# TODO" | grep -v "#.*re\." | wc -l
echo

echo "🔍 Most common patterns:"
grep -roh "re\.[a-zA-Z_]*" --include="*.py" . | sort | uniq -c | sort -nr | head -10
echo

echo "🔍 Files by regex density:"
for file in $(find . -name "*.py" -exec grep -l "re\." {} \;); do
    count=$(grep -c "re\." "$file")
    echo "$count patterns in $file"
done | sort -nr | head -10
```

### Phase 2: Classification System

#### Simple Patterns (Quick Wins)
```python
# Pattern classification examples
SIMPLE_REPLACEMENTS = {
    r'^\w+': 'text.startswith() and text[0].isalpha()',
    r'\d+': 'any(c.isdigit() for c in text)',
    r'[,;]': "text.replace(';', ',').split(',')",
    r'^\s*$': 'not text.strip()',
    r'\.txt$': "text.endswith('.txt')"
}

COMPLEX_PATTERNS = {
    r'\\cite(?:p|t)?\{([^}]+)\}': 'manual_brace_parsing',
    r'@(\w+)\s*\{([^,]+),': 'character_by_character_parser',
    r'(?:(?!pattern).)*': 'ast_parser_recommended'
}
```

#### Complexity Assessment Rubric
```python
def assess_pattern_complexity(regex_pattern):
    """Score regex complexity (1-10, higher = more complex)."""
    complexity = 1

    # Basic complexity indicators
    if '?' in regex_pattern: complexity += 1  # Optional groups
    if '*' in regex_pattern: complexity += 1  # Zero or more
    if '+' in regex_pattern: complexity += 1  # One or more
    if '|' in regex_pattern: complexity += 1  # Alternation
    if '(?:' in regex_pattern: complexity += 2  # Non-capturing groups
    if '(?=' in regex_pattern: complexity += 3  # Lookahead
    if '(?!' in regex_pattern: complexity += 3  # Negative lookahead
    if '\\' in regex_pattern: complexity += 1  # Escape sequences
    if '{' in regex_pattern: complexity += 1  # Quantifiers
    if '[' in regex_pattern: complexity += 1  # Character classes

    # Advanced complexity
    if len(regex_pattern) > 50: complexity += 2  # Length penalty
    if regex_pattern.count('(') > 3: complexity += 2  # Multiple groups
    if 'DOTALL' in str(regex_pattern): complexity += 2  # Multiline

    return min(complexity, 10)
```

### Phase 3: Systematic Replacement

#### Template for String Method Replacement
```python
def replace_simple_regex_template(old_regex, text):
    """Template for replacing simple regex patterns."""
    # Step 1: Analyze what the regex does
    # old_regex: r'^prefix.*suffix$'
    # Meaning: starts with 'prefix', ends with 'suffix'

    # Step 2: Translate to string methods
    return text.startswith('prefix') and text.endswith('suffix')

def replace_complex_regex_template(old_regex, text):
    """Template for replacing complex regex patterns."""
    # Step 1: Break down the regex into components
    # old_regex: r'\\cite\{([^}]+)\}'
    # Components: literal '\cite', opening brace, capture group, closing brace

    # Step 2: Implement state machine
    results = []
    i = 0
    while i < len(text):
        if text[i:i+5] == '\\cite' and i+5 < len(text) and text[i+5] == '{':
            # Found start pattern
            j = i + 6  # After opening brace
            brace_count = 1
            start = j

            # Find matching closing brace
            while j < len(text) and brace_count > 0:
                if text[j] == '{':
                    brace_count += 1
                elif text[j] == '}':
                    brace_count -= 1
                j += 1

            if brace_count == 0:
                # Extract content
                content = text[start:j-1]
                results.append(content)
                i = j
                continue

        i += 1

    return results
```

#### State Machine Pattern for Complex Parsing
```python
class TextParser:
    """Generic state machine for complex text parsing."""

    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.results = []

    def parse(self):
        """Main parsing loop."""
        while self.pos < len(self.text):
            if self.match_pattern():
                self.extract_match()
            else:
                self.pos += 1
        return self.results

    def match_pattern(self):
        """Check if current position matches target pattern."""
        # Override in subclasses
        raise NotImplementedError

    def extract_match(self):
        """Extract and store the matched content."""
        # Override in subclasses
        raise NotImplementedError

class LaTeXCitationParser(TextParser):
    """Specific parser for LaTeX citations."""

    def match_pattern(self):
        return (self.pos + 5 < len(self.text) and
                self.text[self.pos:self.pos+5] == '\\cite')

    def extract_match(self):
        # Implementation for citation extraction
        start = self.pos
        self.pos += 5

        # Handle variations (\citep, \citet)
        if self.pos < len(self.text) and self.text[self.pos] in 'pt':
            self.pos += 1

        # Find and extract braced content
        content = self.extract_braced_content()
        if content:
            self.results.append({
                'type': 'citation',
                'content': content,
                'position': start
            })
```

### Phase 4: Validation and Testing

#### Test Coverage Strategy
```python
class RegexReplacementTest:
    """Comprehensive testing for regex replacements."""

    def test_functional_equivalence(self):
        """Ensure new implementation matches old behavior."""
        test_cases = [
            # Edge cases
            "",  # Empty string
            "a",  # Single character
            "a" * 1000,  # Long string
            "special\nchars\t\r",  # Whitespace and control chars
            "unicode: émojis 🎉",  # Unicode support

            # Domain-specific cases
            "\\cite{smith2023}",  # Simple citation
            "\\cite{key1,key2,key3}",  # Multiple citations
            "\\citep[p.~42]{reference}",  # Citation with optional args
        ]

        for test_input in test_cases:
            old_result = self.old_regex_method(test_input)
            new_result = self.new_string_method(test_input)

            assert old_result == new_result, f"Mismatch for: {test_input}"

    def test_performance_regression(self):
        """Ensure performance hasn't degraded significantly."""
        import time

        large_text = self.generate_large_test_text()

        # Benchmark old method
        start = time.time()
        for _ in range(100):
            self.old_regex_method(large_text)
        old_time = time.time() - start

        # Benchmark new method
        start = time.time()
        for _ in range(100):
            self.new_string_method(large_text)
        new_time = time.time() - start

        # Allow up to 50% performance regression
        assert new_time < old_time * 1.5, f"Performance regression: {new_time/old_time:.2f}x"

    def test_edge_cases(self):
        """Test edge cases that regex might handle differently."""
        edge_cases = [
            # Nested structures
            "\\cite{\\emph{nested}}",

            # Escaped characters
            "\\cite{key\\,with\\,commas}",

            # Malformed input
            "\\cite{unclosed",
            "\\cite}no_opening{",

            # Empty matches
            "\\cite{}",
        ]

        for case in edge_cases:
            # Should not crash, behavior may differ but should be documented
            try:
                result = self.new_string_method(case)
                self.validate_edge_case_result(case, result)
            except Exception as e:
                self.handle_edge_case_exception(case, e)
```

#### Performance Benchmarking Framework
```python
import time
import statistics
from typing import Callable, List

def benchmark_implementations(
    old_func: Callable,
    new_func: Callable,
    test_data: List[str],
    iterations: int = 100
) -> dict:
    """Comprehensive performance comparison."""

    old_times = []
    new_times = []

    for data in test_data:
        # Benchmark old implementation
        old_runs = []
        for _ in range(iterations):
            start = time.perf_counter()
            old_func(data)
            old_runs.append(time.perf_counter() - start)
        old_times.extend(old_runs)

        # Benchmark new implementation
        new_runs = []
        for _ in range(iterations):
            start = time.perf_counter()
            new_func(data)
            new_runs.append(time.perf_counter() - start)
        new_times.extend(new_runs)

    return {
        'old_mean': statistics.mean(old_times),
        'old_stdev': statistics.stdev(old_times),
        'new_mean': statistics.mean(new_times),
        'new_stdev': statistics.stdev(new_times),
        'speedup': statistics.mean(old_times) / statistics.mean(new_times),
        'regression': statistics.mean(new_times) / statistics.mean(old_times)
    }
```

## Quality Assurance Framework

### Pre-Commit Validation
```bash
#!/bin/bash
# pre_commit_regex_validation.sh

set -e

echo "🔍 Validating regex removal..."

# Check for any remaining regex imports
if grep -r "import re" src/ scripts/ | grep -v "# Banned"; then
    echo "❌ Found prohibited regex imports"
    exit 1
fi

# Check for regex method calls
if grep -r "re\." src/ scripts/ | grep -v "# TODO" | grep -v "#.*re\."; then
    echo "❌ Found prohibited regex method calls"
    exit 1
fi

# Run comprehensive tests
echo "🧪 Running tests..."
python -m pytest tests/ -v --tb=short

# Run linting
echo "🔧 Running linters..."
ruff check .
ruff format --check .

# Run type checking
echo "🔍 Running type checks..."
mypy src/

echo "✅ All regex removal validations passed"
```

### Continuous Integration Checks
```yaml
# .github/workflows/regex-compliance.yml
name: Regex Compliance Check

on: [push, pull_request]

jobs:
  regex-compliance:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Check for prohibited regex usage
      run: |
        # Fail if any regex imports found (excluding banned comments)
        if grep -r "import re" src/ scripts/ | grep -v "# Banned"; then
          echo "::error::Prohibited regex import found"
          exit 1
        fi

        # Fail if any regex method calls found
        if grep -r "re\." src/ scripts/ | grep -v "# TODO" | grep -v "#.*re\."; then
          echo "::error::Prohibited regex method call found"
          exit 1
        fi

        echo "✅ No regex usage detected"

    - name: Validate functionality
      run: |
        python -m pytest tests/ --tb=short
```

### Code Review Checklist

#### For Reviewers
```markdown
## Regex Removal Review Checklist

### Functional Correctness
- [ ] New implementation handles all original test cases
- [ ] Edge cases are properly addressed
- [ ] Error handling is equivalent or improved
- [ ] Performance is acceptable (< 2x regression)

### Code Quality
- [ ] No `import re` statements remain
- [ ] No `re.` method calls exist
- [ ] String methods are used appropriately
- [ ] Complex parsing uses state machines or AST parsers
- [ ] Code is more readable than original regex

### Testing
- [ ] Existing tests still pass
- [ ] New tests cover edge cases
- [ ] Performance benchmarks included
- [ ] Documentation updated

### Documentation
- [ ] Replacement rationale explained
- [ ] Complex algorithms commented
- [ ] Performance characteristics noted
- [ ] Migration notes for future developers
```

## Advanced Techniques

### AST Parser Integration Patterns
```python
# Pattern: Wrapper for graceful degradation
class GracefulParser:
    """Parser that falls back to string methods if AST fails."""

    def __init__(self, prefer_ast=True):
        self.prefer_ast = prefer_ast

    def parse(self, content):
        if self.prefer_ast:
            try:
                return self.parse_with_ast(content)
            except Exception as e:
                logger.warning(f"AST parsing failed: {e}, falling back to string methods")
                return self.parse_with_strings(content)
        else:
            return self.parse_with_strings(content)

    def parse_with_ast(self, content):
        # AST parser implementation
        pass

    def parse_with_strings(self, content):
        # String method fallback
        pass
```

### Performance Optimization Techniques
```python
# Technique 1: Precompile common checks
class OptimizedParser:
    def __init__(self):
        # Precompute common prefixes for faster checking
        self.latex_commands = {'\\cite', '\\citep', '\\citet', '\\ref', '\\label'}
        self.max_command_len = max(len(cmd) for cmd in self.latex_commands)

    def find_commands(self, text):
        results = []
        i = 0
        while i < len(text):
            if text[i] == '\\' and i + 1 < len(text):
                # Check all possible command lengths efficiently
                for length in range(2, min(self.max_command_len + 1, len(text) - i + 1)):
                    candidate = text[i:i+length]
                    if candidate in self.latex_commands:
                        results.append((candidate, i))
                        i += length
                        break
                else:
                    i += 1
            else:
                i += 1
        return results

# Technique 2: Memory-efficient streaming
def process_large_file_streaming(filepath):
    """Process large files without loading everything into memory."""
    with open(filepath, 'r') as f:
        buffer = ""
        while True:
            chunk = f.read(8192)  # 8KB chunks
            if not chunk:
                break

            buffer += chunk

            # Process complete patterns in buffer
            while '\\cite{' in buffer:
                start = buffer.find('\\cite{')
                # Find complete citation
                end = find_matching_brace(buffer, start + 5)
                if end != -1:
                    citation = buffer[start:end+1]
                    process_citation(citation)
                    buffer = buffer[end+1:]
                else:
                    break  # Incomplete pattern, need more data
```

## Migration Strategies for Large Codebases

### Incremental Approach
```python
# Strategy: Feature flags for gradual migration
class ConfigurableParser:
    def __init__(self, use_regex=False):
        self.use_regex = use_regex

    def parse(self, content):
        if self.use_regex:
            return self.parse_regex(content)  # Old implementation
        else:
            return self.parse_string(content)  # New implementation

    @deprecated("Will be removed in v2.0, use parse_string instead")
    def parse_regex(self, content):
        # Legacy regex implementation
        pass

    def parse_string(self, content):
        # New string-based implementation
        pass

# Usage with environment variable control
parser = ConfigurableParser(use_regex=os.getenv('USE_REGEX_PARSER', 'false').lower() == 'true')
```

### Team Coordination
```python
# Document migration progress
class MigrationTracker:
    """Track regex removal progress across team."""

    def __init__(self):
        self.migration_status = {
            'src/core/': 'completed',
            'src/utils/': 'in_progress',
            'src/parsers/': 'planned',
            'scripts/': 'not_started',
            'tests/': 'planned'
        }

    def get_progress_report(self):
        total = len(self.migration_status)
        completed = sum(1 for status in self.migration_status.values() if status == 'completed')
        return f"Migration progress: {completed}/{total} ({completed/total*100:.1f}%)"

    def next_priority(self):
        return [path for path, status in self.migration_status.items() if status == 'in_progress']
```

## Success Metrics and Measurement

### Quantitative Metrics
```python
class RegexRemovalMetrics:
    """Track quantitative success metrics."""

    def __init__(self, before_state, after_state):
        self.before = before_state
        self.after = after_state

    def regex_elimination_rate(self):
        """Percentage of regex patterns successfully removed."""
        before_count = self.before['regex_patterns']
        after_count = self.after['regex_patterns']
        return (before_count - after_count) / before_count * 100

    def performance_impact(self):
        """Performance change ratio (> 1.0 means slower)."""
        return self.after['avg_runtime'] / self.before['avg_runtime']

    def code_complexity_change(self):
        """Change in cyclomatic complexity."""
        return self.after['complexity_score'] - self.before['complexity_score']

    def maintenance_burden_change(self):
        """Change in lines of code and cognitive complexity."""
        return {
            'loc_change': self.after['lines_of_code'] - self.before['lines_of_code'],
            'cognitive_change': self.after['cognitive_complexity'] - self.before['cognitive_complexity']
        }
```

### Qualitative Assessment Framework
```python
# Developer experience survey template
DEVELOPER_SURVEY_QUESTIONS = [
    {
        'question': 'How readable is the new string-based code compared to regex?',
        'scale': '1-10 (1=much worse, 10=much better)',
        'category': 'readability'
    },
    {
        'question': 'How confident are you in debugging the new implementation?',
        'scale': '1-10 (1=not confident, 10=very confident)',
        'category': 'maintainability'
    },
    {
        'question': 'How likely are you to introduce bugs in the new code?',
        'scale': '1-10 (1=very likely, 10=very unlikely)',
        'category': 'reliability'
    }
]

def collect_team_feedback():
    """Systematically collect team feedback on regex removal."""
    responses = []
    for developer in get_team_members():
        for question in DEVELOPER_SURVEY_QUESTIONS:
            response = survey_developer(developer, question)
            responses.append({
                'developer': developer,
                'question': question['question'],
                'score': response,
                'category': question['category']
            })
    return responses
```

## Conclusion and Recommendations

### When Regex Removal is Recommended
1. **High maintenance codebases** with frequent changes
2. **Teams with mixed regex expertise** where not everyone can debug complex patterns
3. **Performance-critical applications** where string methods can be faster for simple patterns
4. **Code quality initiatives** focusing on readability and maintainability
5. **Educational environments** where explicit logic is preferred over pattern matching

### When to Proceed with Caution
1. **Legacy systems** with extensive regex usage and limited test coverage
2. **Performance-critical paths** where regex has been proven optimal
3. **Domain-specific languages** where regex is the standard approach
4. **Teams with strong regex expertise** who can maintain complex patterns effectively

### Long-term Strategy
1. **Policy establishment**: Create and enforce no-regex policies for new code
2. **Tool integration**: Use linters and CI/CD to prevent regex reintroduction
3. **Knowledge transfer**: Document replacement patterns for institutional knowledge
4. **Gradual migration**: Plan systematic removal over multiple releases
5. **Performance monitoring**: Track system performance throughout migration

The systematic removal of regex from deep-biblio-tools demonstrates that even complex text processing can be accomplished effectively with string methods and AST parsers, resulting in more maintainable, readable, and reliable code.
