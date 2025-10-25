# Claude Session Management

This directory manages Claude conversation sessions and maintains context continuity across interactions.

## Session Files

- **current-session.md** - Active session context and ongoing work
- **learnings.md** - Accumulated patterns and insights from successful interactions
- **session-history/** - Archived completed sessions

## Session Workflow

### Starting a New Session
```bash
scripts/guardrails/claude-guard session start "implementing user authentication"
```

### Continuing a Session
```bash
scripts/guardrails/claude-guard session continue
```

### Closing a Session
```bash
scripts/guardrails/claude-guard session close "authentication implementation complete"
```

## Session Continuity

Each session maintains:
- **Context**: What we're working on and why
- **Progress**: What's been completed and what's next
- **Decisions**: Architecture choices and rationale
- **Patterns**: Successful approaches for future reference
- **Blockers**: Issues encountered and solutions

## Integration with Claude

When starting a conversation with Claude, paste the contents of `current-session.md` to provide context about ongoing work and established patterns.
