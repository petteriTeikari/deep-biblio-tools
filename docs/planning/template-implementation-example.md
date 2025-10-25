# Concrete Implementation for Template Enhancement

## Ready-to-Use Code for claude-code-guardrails-template

### 1. Enhanced `hooks/post_gen_project.py` Addition

```python
def create_maturity_based_guardrails():
    """Create repository maturity-based behavior system."""

    # Create .claude/repo-maturity.yaml
    maturity_config = {
        "maturity_level": "{{ cookiecutter.project_maturity }}",
        "behavior_modes": {
            "sandbox": {
                "risk_tolerance": "high",
                "documentation_required": "minimal",
                "testing_required": False,
                "guardrails_enforcement": "relaxed",
                "refactoring_allowed": "aggressive",
                "ai_personality": "Move fast, experiment freely"
            },
            "development": {
                "risk_tolerance": "medium",
                "documentation_required": "basic",
                "testing_required": True,
                "guardrails_enforcement": "standard",
                "refactoring_allowed": "moderate",
                "ai_personality": "Balance speed with quality"
            },
            "staging": {
                "risk_tolerance": "low",
                "documentation_required": "comprehensive",
                "testing_required": True,
                "guardrails_enforcement": "strict",
                "refactoring_allowed": "conservative",
                "ai_personality": "Quality first, document everything"
            },
            "production": {
                "risk_tolerance": "zero",
                "documentation_required": "exhaustive",
                "testing_required": "mandatory",
                "guardrails_enforcement": "paranoid",
                "refactoring_allowed": "minimal",
                "ai_personality": "Senior engineer: Every change needs justification"
            }
        },
        "current_rules": [
            "ALWAYS read guardrails before coding",
            "DOCUMENT every significant decision",
            "NO shortcuts or 'quick fixes'",
            "TEST everything that changes",
            "EXPLAIN rationale before acting"
        ]
    }

    # Write the config
    claude_dir = Path(".claude")
    with open(claude_dir / "repo-maturity.yaml", "w", encoding="utf-8") as f:
        yaml.dump(maturity_config, f, default_flow_style=False)

    # Create incremental development config
    incremental_config = {
        "step_limits": {
            "production": {
                "max_files_per_response": 1,
                "max_lines_per_change": 50,
                "require_explanation_first": True,
                "require_linting_after_each_file": True,
                "checklist_before_action": [
                    "Have I read the guardrails?",
                    "Is this change deterministic?",
                    "Do I need an ADR?",
                    "Will this need tests?",
                    "Have I documented why?"
                ]
            },
            "staging": {
                "max_files_per_response": 2,
                "max_lines_per_change": 100,
                "require_explanation_first": True,
                "require_linting_after_each_file": True,
                "checklist_before_action": [
                    "Have I checked guardrails?",
                    "Is this the minimal change?",
                    "Are tests affected?"
                ]
            },
            "development": {
                "max_files_per_response": 3,
                "max_lines_per_change": 200,
                "require_explanation_first": False,
                "require_linting_after_each_file": False,
                "checklist_before_action": [
                    "Does this follow patterns?"
                ]
            },
            "sandbox": {
                "max_files_per_response": 5,
                "max_lines_per_change": 500,
                "require_explanation_first": False,
                "require_linting_after_each_file": False,
                "checklist_before_action": []
            }
        }
    }

    with open(claude_dir / "incremental-development.yaml", "w", encoding="utf-8") as f:
        yaml.dump(incremental_config, f, default_flow_style=False)


def create_enhanced_pre_commit_config():
    """Create comprehensive pre-commit configuration."""

    pre_commit_config = """repos:
  # Standard hooks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict

  # Language-specific hooks
{%- if cookiecutter.primary_language == "python" %}
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
{%- endif %}

  # Guardrail enforcement hooks
  - repo: local
    hooks:
      - id: check-guardrails
        name: Check Claude guardrails compliance
        entry: {{ cookiecutter.primary_language_command }} scripts/check_guardrails.py
        language: system
        always_run: true
        pass_filenames: false

      - id: check-maturity-compliance
        name: Check repository maturity compliance
        entry: {{ cookiecutter.primary_language_command }} scripts/check_maturity_compliance.py
        language: system
        always_run: true
        pass_filenames: false

      - id: validate-incremental-limits
        name: Validate incremental development limits
        entry: {{ cookiecutter.primary_language_command }} scripts/enforce_incremental_development.py --summary
        language: system
        always_run: true
        pass_filenames: false
"""

    with open(".pre-commit-config.yaml", "w", encoding="utf-8") as f:
        f.write(pre_commit_config)


def create_adr_structure():
    """Create Architecture Decision Records structure."""

    # Create directories
    decisions_dir = Path("docs/decisions")
    decisions_dir.mkdir(parents=True, exist_ok=True)

    # Create template
    adr_template = """# ADR-[NUMBER]: [Title]

## Status
[Proposed | Accepted | Deprecated | Superseded by ADR-XXX]

## Context
[Describe the issue motivating this decision and any context that influences it]

## Decision
[Describe the decision and the reasoning behind it]

## Consequences

### Positive
- [Positive outcome 1]
- [Positive outcome 2]

### Negative
- [Negative outcome 1]
- [Negative outcome 2]

### Neutral
- [Neutral outcome 1]

## Alternatives Considered
- **[Alternative 1]**: [Why not chosen]
- **[Alternative 2]**: [Why not chosen]

## References
- [Link to relevant documentation]
- [Link to related issue/PR]
"""

    with open(decisions_dir / "ADR-000-template.md", "w", encoding="utf-8") as f:
        f.write(adr_template)

    # Create first ADR about guardrails
    first_adr = """# ADR-001: Repository Maturity-Based Guardrails

## Status
Accepted

## Context
AI coding assistants like Claude Code struggle with consistent rule compliance, especially as repositories mature. They tend to optimize for task completion over guardrail adherence.

## Decision
Implement a multi-layered enforcement system that adapts AI behavior based on repository maturity level (sandbox → development → staging → production).

## Consequences

### Positive
- Higher code quality in production repositories
- Faster experimentation in sandbox environments
- Consistent AI behavior aligned with project needs
- Better documentation and decision tracking

### Negative
- Slower development in mature repositories
- More configuration to maintain
- Learning curve for the system

### Neutral
- Changes how developers interact with AI assistants

## Alternatives Considered
- **Single behavior mode**: Too rigid, doesn't adapt to project needs
- **Manual enforcement only**: Too inconsistent, relies on human memory
- **No enforcement**: Leads to quality issues in production code

## References
- [Claude Guardrails Documentation](.claude/CLAUDE.md)
- [Repository Maturity Configuration](.claude/repo-maturity.yaml)
"""

    with open(decisions_dir / "ADR-001-maturity-based-guardrails.md", "w", encoding="utf-8") as f:
        f.write(first_adr)
```

### 2. Update to `cookiecutter.json`

```json
{
    // ... existing fields ...
    "project_maturity": {
        "type": "string",
        "default": "development",
        "choices": ["sandbox", "development", "staging", "production"],
        "help": "Repository maturity level (affects AI behavior and guardrails)"
    },
    "enforce_incremental_development": {
        "type": "boolean",
        "default": true,
        "help": "Enforce smaller steps with tighter guardrail focus"
    },
    "require_adrs": {
        "type": "boolean",
        "default": true,
        "help": "Require Architecture Decision Records for significant changes"
    }
}
```

### 3. Enhanced `.claude/CLAUDE.md` Section

Add after the "Forbidden Actions" section:

```markdown
## 🎯 MANDATORY BEHAVIOR: Attention Management

### Repository Maturity Check (MUST DO FIRST)
Before ANY action, Claude MUST:
1. Read `.claude/repo-maturity.yaml` to determine current maturity level
2. Read `.claude/incremental-development.yaml` for step limits
3. Adjust behavior according to maturity level

### Behavior by Maturity Level

#### Production Mode (risk_tolerance: zero)
- **READ** `.claude/CLAUDE.md` completely before ANY code
- **LIMIT** changes to 1 file, 50 lines maximum
- **EXPLAIN** every change BEFORE implementation
- **DOCUMENT** decisions in `docs/decisions/`
- **RUN** all checks after EVERY file change
- **PAUSE** and ask for confirmation on significant changes

#### Staging Mode (risk_tolerance: low)
- **CHECK** guardrails before starting
- **LIMIT** changes to 2 files, 100 lines maximum
- **EXPLAIN** significant changes
- **TEST** all changes thoroughly

#### Development Mode (risk_tolerance: medium)
- **REVIEW** guardrails for major changes
- **LIMIT** changes to 3 files, 200 lines maximum
- **FOLLOW** established patterns

#### Sandbox Mode (risk_tolerance: high)
- **KNOW** the guardrails exist
- **EXPERIMENT** within reason
- **LIMIT** changes to 5 files, 500 lines maximum

### User Acceptance Statement
"I explicitly prefer smaller, compliant steps over larger, risky changes. I accept the trade-off of more interactions for higher quality."

## 🔄 Self-Enforcement Protocol

Claude MUST use this checklist before EVERY code change:

```
□ Current maturity level: _______
□ Files allowed this response: _______
□ Lines allowed this change: _______
□ Guardrails read this session: YES/NO
□ ADR needed for this change: YES/NO
□ Tests needed for this change: YES/NO
```

If Claude cannot fill this checklist, Claude MUST read configuration files first.
```

### 4. New Enforcement Scripts

Create `{{ cookiecutter.project_slug }}/scripts/ai_behavior_monitor.py`:

```python
#!/usr/bin/env python3
"""Monitor AI compliance with maturity-based behavior rules."""

import json
import sys
from datetime import datetime
from pathlib import Path

def log_ai_action(action_type, compliant, details):
    """Log AI behavior for pattern analysis."""
    log_file = Path(".claude/analytics/ai_behavior.json")
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Load existing logs
    if log_file.exists():
        with open(log_file, encoding="utf-8") as f:
            logs = json.load(f)
    else:
        logs = []

    # Add new entry
    logs.append({
        "timestamp": datetime.utcnow().isoformat(),
        "action_type": action_type,
        "compliant": compliant,
        "details": details
    })

    # Save
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)

    # Alert on non-compliance
    if not compliant:
        print(f"⚠️  Non-compliant behavior detected: {details}")
        return 1

    return 0

if __name__ == "__main__":
    # This would be called by hooks or CI/CD
    sys.exit(log_ai_action(
        action_type=sys.argv[1] if len(sys.argv) > 1 else "unknown",
        compliant=sys.argv[2].lower() == "true" if len(sys.argv) > 2 else False,
        details=sys.argv[3] if len(sys.argv) > 3 else "No details"
    ))
```

## Key Innovation

**The template should generate projects that "train" AI assistants to follow rules through:**

1. **Mandatory configuration reading** - Can't proceed without it
2. **Automatic enforcement** - Violations caught immediately
3. **Positive reinforcement** - Praise for compliance
4. **Clear trade-offs** - Users explicitly accept slower/better
5. **Behavioral adaptation** - Different rules for different contexts

This makes the guardrails system self-reinforcing rather than relying on AI memory.
