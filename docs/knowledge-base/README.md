# Knowledge Base

This directory contains institutional knowledge, domain expertise, and accumulated wisdom about bibliography processing and the Deep Biblio Tools project.

## 📚 Core Knowledge Documents

- **[README Institutional Knowledge](readme-institutional-knowledge.md)** - Essential knowledge about project documentation and README maintenance
- **[Hardcoded Bibliography Knowledge](hardcode-biblio.md)** - Domain expertise for handling hardcoded bibliographies

## 🧠 Knowledge Areas

### Bibliography Processing
- Common LLM hallucination patterns
- Author name formatting conventions
- Citation style variations
- DOI and arXiv ID patterns
- Journal abbreviation standards

### Technical Implementation
- Deterministic processing requirements
- AST parsing best practices
- API rate limiting strategies
- Caching optimization techniques
- Batch processing patterns

### Project Management
- Documentation standards
- Code review practices
- Testing strategies
- CI/CD workflows
- Collaboration guidelines

## 💡 Contributing to Knowledge Base

When adding knowledge documents:
1. **Document Context** - Explain when and why this knowledge applies
2. **Include Examples** - Concrete examples make concepts clearer
3. **Reference Sources** - Link to authoritative sources when possible
4. **Keep Updated** - Review and update as understanding evolves
5. **Be Practical** - Focus on actionable knowledge

## 🔍 Quick Reference

### Common Issues and Solutions
- **LLM Hallucinations**: Check for "et al." abuse, generic titles, suspicious dates
- **Author Parsing**: Handle prefixes (van, de, von), suffixes (Jr., III), and complex names
- **Citation Matching**: Use fuzzy matching with 85% threshold for titles
- **API Failures**: Implement exponential backoff and caching

### Best Practices
- Always validate against authoritative sources (CrossRef, arXiv)
- Maintain audit trails for all processing decisions
- Use batch processing for multiple API calls
- Cache aggressively but deterministically
- Test with real-world edge cases

## 📈 Learning from Experience

This knowledge base grows through:
- Production issues and their resolutions
- User feedback and feature requests
- Code review discussions
- Performance optimization discoveries
- Integration challenges and solutions

Remember: Every problem solved is knowledge gained. Document it here!
