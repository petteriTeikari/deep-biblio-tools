# Team Analytics Dashboard

Tracks and analyzes Claude collaboration patterns, success rates, and team productivity metrics.

## Metrics Collected

### Collaboration Quality
- **Success Rate**: Percentage of successful Claude interactions
- **Context Efficiency**: How well context is utilized
- **Pattern Recognition**: Identification of successful approaches
- **Learning Velocity**: Rate of pattern accumulation

### Productivity Metrics
- **Session Duration**: Average length of productive sessions
- **Code Quality**: Improvements in code metrics after Claude interactions
- **Problem Resolution**: Time to resolve issues with Claude assistance
- **Knowledge Transfer**: Effective sharing of learnings

## Dashboard Usage

### View Current Metrics
```bash
python .claude/analytics/team-dashboard.py
```

### Export Metrics
```bash
scripts/guardrails/export-team-metrics.sh --days 30 --format json
```

### Generate Reports
```bash
python .claude/analytics/team-dashboard.py --report weekly
```

## Integration

Analytics are automatically collected during:
- Session management operations
- Context server usage
- Validation script runs
- Trust scoring evaluations
