# Claude Code Guardrails Template Improvements

Based on real-world experience with deep-biblio-tools repository refactoring.

## 🚨 Critical Missing Features

### 1. Repository Maturity-Based Behavior Adaptation
**Problem**: Template treats all repos the same - sandbox experiments get same caution as production systems.

**Solution**: Add `.claude/repo-maturity.yaml`
```yaml
maturity_level: "sandbox|development|staging|production"
behavior_modes:
  production:
    risk_tolerance: zero
    max_files_per_response: 1
    require_explanation_first: true
    ai_personality: "Senior engineer - every change needs justification"
```

**Benefits**:
- AI adapts behavior to repository state
- Prevents reckless changes in mature repos
- Allows experimentation in sandboxes

### 2. Incremental Development Enforcement
**Problem**: AI tries to do too much at once, loses focus on guardrails.

**Solution**: Add `.claude/incremental-development.yaml`
- Enforce smaller steps with tighter guardrail focus
- Limit files/lines per response based on risk
- Mandatory pauses for production repos

### 3. Automatic Pre-commit Enforcement
**Problem**: Guardrails are advisory, not enforced.

**Solution**: Generate comprehensive pre-commit hooks:
```yaml
- id: check-guardrails
- id: no-regex-parser
- id: validate-imports
- id: check-decision-docs
```

### 4. Decision Documentation System (ADRs)
**Problem**: No institutional memory of why decisions were made.

**Solution**:
- Generate `docs/decisions/` directory
- ADR template and enforcement
- Check for ADRs on significant changes

### 5. Guardrail Reading Priority System
**Problem**: AI reads guardrails "when convenient", not first.

**Solution**: Modify template to enforce:
```python
# In post_gen_project.py
create_guardrail_priority_config():
    """
    .claude/ai-behavior.yaml:
    mandatory_actions:
      - "ALWAYS read .claude/CLAUDE.md before ANY coding"
      - "CHECK repo-maturity.yaml for current mode"
      - "LIMIT scope based on incremental-development.yaml"
    """
```

## 🎯 Template CLAUDE.md Improvements

### Add Section: "Attention Management"
```markdown
## Attention Management Based on Repository Maturity

### Production Repositories
- **READ guardrails FIRST** - Not optional
- **ONE file at a time** - No exceptions
- **EXPLAIN before doing** - Always
- **DOCUMENT decisions** - In ADRs

### Development Repositories
- **CHECK guardrails** - Before major changes
- **2-3 files maximum** - Stay focused
- **EXPLAIN significant changes** - Brief is OK

### Sandbox Repositories
- **KNOW the guardrails** - General awareness
- **Experiment freely** - Within reason
```

### Add Section: "Incremental Development"
```markdown
## Incremental Development Requirements

Claude MUST trade speed for quality based on repo maturity:
- **Production**: 1 file, 50 lines max, explain first
- **Staging**: 2 files, 100 lines max
- **Development**: 3 files, 200 lines max
- **Sandbox**: 5 files, 500 lines max

User explicitly accepts smaller steps for better compliance.
```

### Add Section: "Self-Enforcement"
```markdown
## Self-Enforcement Checklist

Before EVERY code change:
□ Have I read the guardrails today?
□ What is the repo maturity level?
□ Am I within file/line limits?
□ Do I need to document this decision?
□ Have I run linters?
```

## 🔧 Generated Script Improvements

### 1. `scripts/check_guardrails.py`
Already good, but add:
- Check for repo maturity config
- Validate incremental limits
- Ensure ADR compliance

### 2. `scripts/enforce_incremental_development.py`
New script to add - enforces step limits based on maturity.

### 3. `scripts/check_maturity_compliance.py`
New script to add - validates changes against maturity level.

### 4. `scripts/ai_attention_monitor.py`
New script to track if AI is following guardrails vs doing tasks.

## 📊 Template Generation Improvements

### In `hooks/post_gen_project.py`:

```python
def create_maturity_based_guardrails():
    """Generate maturity-aware configuration."""

    # Detect if new project or existing
    if is_existing_project():
        maturity = detect_project_maturity()
    else:
        maturity = "sandbox"

    # Generate appropriate configs
    generate_repo_maturity_yaml(maturity)
    generate_incremental_limits(maturity)
    generate_pre_commit_hooks(maturity)
    generate_adr_structure()
```

## 🧠 Behavioral Psychology Integration

### Problem: AI "Forgets" Due to Optimization
LLMs optimize for task completion over rule following.

### Solution: Multiple Reinforcement Layers
1. **Visual Cues**: Status badges in CLAUDE.md
2. **Forced Pauses**: Mandatory stops in production
3. **Positive Feedback**: "Good job checking guardrails!"
4. **Automated Checks**: Can't proceed without compliance

## 🚀 Implementation Priority

### Phase 1: Core Behavior Control
1. Add repo maturity system
2. Add incremental development limits
3. Update CLAUDE.md with new sections

### Phase 2: Automation
1. Generate pre-commit hooks
2. Add enforcement scripts
3. Create ADR system

### Phase 3: Advanced Features
1. AI attention monitoring
2. Learning from violations
3. Automatic rule updates

## 📝 Key Insight

**The core problem isn't that guardrails don't exist - it's that AI assistants naturally optimize for task completion over compliance.**

The solution is multi-layered enforcement that makes compliance easier than non-compliance:
- Automatic checks catch violations
- Smaller steps keep focus
- Maturity levels set expectations
- Documentation creates accountability

## 🎓 Lessons for Template

1. **Don't rely on AI memory** - Enforce through automation
2. **Accept trade-offs** - Users prefer quality over speed
3. **Layer the enforcement** - Multiple checks catch more
4. **Make compliance easy** - Automation > willpower
5. **Document everything** - Future you will thank you
