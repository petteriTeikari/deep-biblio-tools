# AIDEV Local Anchoring System

This document describes the AIDEV tag system for enhanced Claude collaboration through local context anchoring, based on the approach from [Diwank's field notes](https://diwank.space/field-notes-from-shipping-real-code-with-claude).

## Overview

The AIDEV tag system provides **local anchoring** - a way to embed contextual information directly in your code where Claude needs it most. Unlike global instructions in `CLAUDE.md`, these tags provide hyper-local context at specific code locations.

## Tag Types

### ✨ `AIDEV-IMMUTABLE`
**Purpose**: Mark code sections that should never be modified by AI
**Usage**: Critical business logic, security functions, payment processing

```python
# AIDEV-IMMUTABLE-START: Payment Processing Logic
def process_payment(amount, user_id):
    # CRITICAL: This handles financial transactions
    if not validate_amount(amount):
        raise ValueError("Invalid payment amount")
    return payment_gateway.charge(user_id, amount)
# AIDEV-IMMUTABLE-END
```

### ✨ `AIDEV-NOTE`
**Purpose**: Provide guidance and context for Claude
**Usage**: Explain design decisions, performance considerations, dependencies

```python
# AIDEV-NOTE: This function uses caching for performance - don't add logging
def get_user_data(user_id):
    return cache.get_or_set(f"user:{user_id}", lambda: db.get_user(user_id))

# AIDEV-NOTE: Always validate input before processing in this module
class DataProcessor:
    pass
```

### ✨ `AIDEV-TODO`
**Purpose**: Mark items that need to be addressed
**Usage**: Missing features, optimizations, refactoring needs

```python
# AIDEV-TODO: Add error handling for network failures
def fetch_data(url):
    return requests.get(url).json()

# AIDEV-TODO: Optimize this algorithm for large datasets
def process_items(items):
    return [expensive_operation(item) for item in items]
```

### ✨ `AIDEV-QUESTION`
**Purpose**: Ask questions for human review or clarification
**Usage**: Architecture decisions, unclear requirements, performance trade-offs

```python
# AIDEV-QUESTION: Should we use async here for better performance?
def handle_multiple_requests(requests):
    results = []
    for req in requests:
        results.append(process_request(req))
    return results
```

### ℹ✨ `AIDEV-ANSWER`
**Purpose**: Provide answers to previously asked questions
**Usage**: Document decisions, provide context for future changes

```python
# AIDEV-QUESTION: Should we use async here for better performance?
# AIDEV-ANSWER: No, sync is fine - requests are small and latency isn't critical
def handle_multiple_requests(requests):
    results = []
    for req in requests:
        results.append(process_request(req))
    return results
```

### ✨ `AIDEV-REPLACEMENT-TODO`
**Purpose**: Mark temporary code that must be replaced before production
**Usage**: Mock data, hardcoded values, placeholder implementations

```python
# AIDEV-REPLACEMENT-TODO: Replace with real API endpoint
API_ENDPOINT = "http://localhost:3000/mock-api"

# AIDEV-REPLACEMENT-TODO: Use proper config management
def get_database_url():
    return "sqlite:///test.db"  # Temporary for development
```

### ✨ `AIDEV-GENERATED-TEST`
**Purpose**: Mark AI-generated tests that need human review
**Usage**: Ensure test quality, validate test scenarios, add edge cases

```python
# AIDEV-GENERATED-TEST: test_payment_validation
def test_payment_validation():
    # AI-generated test - needs human review
    assert validate_payment_amount(100.50) == True
    assert validate_payment_amount(-10) == False
```

## Best Practices

### 1. **Be Specific and Contextual**
```python
# Good
# AIDEV-NOTE: Cache TTL is 5 minutes to balance freshness with performance

# Avoid
# AIDEV-NOTE: Uses caching
```

### 2. **Use Q&A Pairs for Complex Decisions**
```python
# AIDEV-QUESTION: Why do we validate amounts twice?
def process_order(order):
    validate_order_amount(order.amount)  # First validation
    # ... other processing ...
    validate_payment_amount(order.amount)  # Second validation

# AIDEV-ANSWER: Legacy requirement from payment provider migration 2023
```

### 3. **Mark Temporary Code Clearly**
```python
# AIDEV-REPLACEMENT-TODO: Replace with environment variable
SECRET_KEY = "dev-key-12345"  # Only for development!
```

### 4. **Protect Critical Sections**
```python
# AIDEV-IMMUTABLE-START: Auth Token Validation
def validate_jwt_token(token):
    # Security-critical logic - do not modify
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload.get('user_id')
    except jwt.InvalidTokenError:
        return None
# AIDEV-IMMUTABLE-END
```

## Management Tools

### CLI Tool Usage
The generated projects include an `aidev` CLI tool for managing tags:

```bash
# Scan codebase for all AIDEV tags
./scripts/guardrails/aidev scan

# Generate comprehensive report
./scripts/guardrails/aidev report

# Show Q&A pairs
./scripts/guardrails/aidev questions

# Clean up resolved REPLACEMENT-TODO tags
./scripts/guardrails/aidev cleanup

# Add new tag to a file
./scripts/guardrails/aidev add src/main.py AIDEV-NOTE "This function is performance-critical"

# Show usage examples
./scripts/guardrails/aidev examples
```

### Git Integration
The git hooks automatically check for:
- Modifications to `AIDEV-IMMUTABLE` sections (blocked)
- `AIDEV-REPLACEMENT-TODO` markers before push (warning)
- `AIDEV-GENERATED-TEST` markers requiring review (info)

### Validation
Run comprehensive validation:
```bash
python scripts/validate_claude_constraints.py
```

## Integration with Claude

When working with Claude, the AIDEV tags provide:

1. **Context Preservation**: Tags travel with code during refactoring
2. **Decision History**: Q&A pairs document why choices were made
3. **Safety Boundaries**: Immutable blocks prevent accidental modifications
4. **Progress Tracking**: TODO and REPLACEMENT-TODO show what needs attention

## File Patterns

### Python
```python
# AIDEV-NOTE: Comment explaining context
# AIDEV-TODO: Description of what needs to be done
# AIDEV-QUESTION: What should we do here?
# AIDEV-ANSWER: Explanation of the decision
```

### JavaScript/TypeScript
```javascript
// AIDEV-NOTE: Comment explaining context
// AIDEV-TODO: Description of what needs to be done
// AIDEV-QUESTION: What should we do here?
// AIDEV-ANSWER: Explanation of the decision
```

### Other Languages
The system adapts comment styles based on file extensions:
- `.py`: `#`
- `.js/.ts/.jsx/.tsx`: `//`
- `.go/.rs/.java/.swift/.cpp/.h`: `//`

## Workflow Integration

### 1. Development Phase
- Add `AIDEV-NOTE` for context
- Use `AIDEV-TODO` for planned improvements
- Mark temporary code with `AIDEV-REPLACEMENT-TODO`

### 2. Code Review Phase
- Address `AIDEV-QUESTION` tags
- Review `AIDEV-GENERATED-TEST` markers
- Validate `AIDEV-IMMUTABLE` boundaries

### 3. Production Preparation
- Resolve all `AIDEV-REPLACEMENT-TODO` markers
- Ensure `AIDEV-QUESTION` tags have answers
- Verify test coverage for critical sections

This system creates a collaborative environment where Claude understands not just what the code does, but why it was written that way and what constraints apply to changes.
