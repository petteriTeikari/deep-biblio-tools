# ADR-001: Incremental Development Enforcement

## Status
Accepted

## Context
Claude Code and other AI assistants struggle with consistent guardrail compliance due to:
- Context window limitations forcing attention trade-offs
- Tendency to prioritize task completion over compliance
- Lack of persistent memory between sessions
- Generic training that conflicts with project-specific rules

Users report that AI assistants "forget" guardrails and take shortcuts, especially on larger tasks.

## Decision
Implement a multi-layered enforcement system that:

1. **Forces incremental development** - Smaller steps with tighter guardrail focus
2. **Adapts behavior to repository maturity** - More careful in production repos
3. **Automates compliance checking** - Pre-commit hooks and CI/CD validation
4. **Provides context-aware templates** - Response structures based on risk level

Key components:
- `.claude/repo-maturity.yaml` - Defines repository state and behavior modes
- `.claude/incremental-development.yaml` - Enforces step size limits
- Pre-commit hooks for automatic validation
- Scripts for guardrail compliance checking

## Consequences

### Positive
- **Higher code quality** - Fewer violations slip through
- **Consistent behavior** - AI adapts to repository needs
- **Better documentation** - Forced explanations improve understanding
- **Reduced rework** - Catch issues before commit
- **Learning reinforcement** - Repetition helps AI "remember" rules

### Negative
- **Slower initial development** - Smaller steps take more interactions
- **More configuration** - Additional files to maintain
- **Learning curve** - Developers must understand the system
- **Potential friction** - Enforcement might feel restrictive

### Neutral
- Changes AI interaction patterns significantly
- Requires buy-in from all contributors
- May need tuning based on team feedback

## Alternatives Considered

1. **Manual reminders only** - Rely on developers to remind AI
   - Rejected: Too inconsistent, human error prone

2. **Single global configuration** - One set of rules for all repos
   - Rejected: Different repos have different maturity needs

3. **Post-hoc review only** - Catch issues in code review
   - Rejected: Too late, wastes time on rework

4. **Custom AI fine-tuning** - Train model on our specific patterns
   - Rejected: Not feasible with current Claude Code

## References
- [Automatic Quality Enforcement Plan](../planning/automatic-quality-enforcement-plan.md)
- [Claude Guardrails](.claude/CLAUDE.md)
- [Repository Maturity Configuration](.claude/repo-maturity.yaml)
