# KB Validator Test Plan - Phased Approach

**Based on**: OpenAI suggestions + critical assessment
**Priority**: Catch October 26 patterns FIRST, add robustness LATER

---

## Phase 1: MVP Tests (4 hours) - MUST IMPLEMENT

### Test File: `tests/kb_quality/test_format_validation_mvp.py`

```python
"""
MVP test suite focusing on format validation.

These tests catch the October 26 incident patterns WITHOUT network access.
Fast, reliable, suitable for pre-commit hooks.
"""

import pytest
from pathlib import Path
from src.kb_quality.url_validator import (
    MarkdownKBValidator,
    ValidationIssue,
)


@pytest.fixture
def validator():
    """Fast validator - format validation only, no network."""
    return MarkdownKBValidator(enable_network_checks=False)


class TestOctober26Regression:
    """
    Regression tests for October 26 incident.

    The root cause was non-numeric arXiv IDs that bypassed validation.
    These tests ensure they can NEVER slip through again.
    """

    @pytest.mark.parametrize("bad_url", [
        "https://arxiv.org/abs/2025.mcp.taxonomy",
        "https://arxiv.org/abs/2025.mcp.privilege",
        "https://arxiv.org/abs/2025.mpma",
    ])
    def test_blocks_exact_october_26_urls(self, validator, bad_url):
        """Block the exact URLs that caused the October 26 incident."""
        issue = validator._validate_arxiv_url(bad_url, f"[Test]({bad_url})", 1)

        assert issue is not None, f"FAILED TO BLOCK: {bad_url}"
        assert issue.severity == "CRITICAL"
        assert "Invalid arXiv ID format" in issue.message

    def test_october_26_full_document(self, validator, tmp_path):
        """Test with actual October 26 document structure."""
        markdown = tmp_path / "october26_incident.md"
        markdown.write_text("""
# MCP Security Analysis

Recent security research reveals concerning patterns:

[Zhao et al., 2025](https://arxiv.org/abs/2025.mcp.taxonomy) analyzed
vulnerability taxonomy across MCP deployments.

[Li et al., 2025](https://arxiv.org/abs/2025.mcp.privilege) examined
privilege escalation patterns.

[Wang et al., 2025](https://arxiv.org/abs/2025.mpma) studied preference
manipulation attacks.
""")

        issues = validator.validate_file(markdown)

        # ALL THREE must be caught
        assert len(issues) == 3, f"Expected 3 issues, got {len(issues)}"

        # All must be CRITICAL
        assert all(i.severity == "CRITICAL" for i in issues)

        # Verify line numbers are captured
        assert all(i.line_number > 0 for i in issues)

        # Verify specific URLs are flagged
        flagged_urls = " ".join([i.url for i in issues])
        assert "2025.mcp.taxonomy" in flagged_urls
        assert "2025.mcp.privilege" in flagged_urls
        assert "2025.mpma" in flagged_urls


class TestArxivFormatValidation:
    """arXiv format validation (primary validation layer)."""

    def test_valid_arxiv_formats(self, validator):
        """Valid arXiv IDs should pass."""
        valid_urls = [
            "https://arxiv.org/abs/2412.02646",      # New format
            "https://arxiv.org/abs/2412.02646v1",    # With version
            "https://arxiv.org/abs/1234.5678",       # Old format
            "https://arxiv.org/abs/0704.0001",       # Very old
        ]

        for url in valid_urls:
            issue = validator._validate_arxiv_url(url, f"[Test]({url})", 1)
            assert issue is None, f"False positive: {url}"

    def test_invalid_arxiv_formats(self, validator):
        """Invalid arXiv IDs should be caught."""
        invalid_urls = [
            "https://arxiv.org/abs/2025.mcp.taxonomy",  # Non-numeric
            "https://arxiv.org/abs/2025.mpma",          # Too short
            "https://arxiv.org/abs/9999.12345",         # Invalid year
            "https://arxiv.org/abs/2513.12345",         # Invalid month
        ]

        for url in invalid_urls:
            issue = validator._validate_arxiv_url(url, f"[Test]({url})", 1)
            assert issue is not None, f"Failed to catch: {url}"
            assert issue.severity == "CRITICAL"


class TestDOIValidation:
    """DOI format validation."""

    def test_valid_doi_formats(self, validator):
        """Valid DOIs should pass."""
        valid_dois = [
            "https://doi.org/10.1000/182",
            "https://doi.org/10.1234/example",
            "https://doi.org/10.1038/s43017-020-0039-9",
        ]

        for url in valid_dois:
            issue = validator._validate_doi_url(url, f"[Test]({url})", 1)
            assert issue is None, f"False positive: {url}"

    def test_invalid_doi_formats(self, validator):
        """Invalid DOIs should be caught."""
        invalid_dois = [
            "https://doi.org/notadoi",
            "https://doi.org/10",
            "https://doi.org/",
        ]

        for url in invalid_dois:
            issue = validator._validate_doi_url(url, f"[Test]({url})", 1)
            assert issue is not None, f"Failed to catch: {url}"


class TestPerformance:
    """Validation should be FAST (pre-commit requirement)."""

    def test_single_file_speed(self, validator, tmp_path):
        """Single file with 100 citations should validate in <100ms."""
        import time

        file = tmp_path / "test.md"
        content = "\n".join([
            f"[Ref {i}](https://arxiv.org/abs/24{i//10:02d}.{i:05d})"
            for i in range(100)
        ])
        file.write_text(content)

        start = time.time()
        issues = validator.validate_file(file)
        duration = time.time() - start

        assert duration < 0.1, f"Too slow: {duration:.3f}s"

    def test_large_kb_speed(self, validator, tmp_path):
        """100 files (1000 citations) should validate in <5 seconds."""
        import time

        kb = tmp_path / "large_kb"
        kb.mkdir()

        for i in range(100):
            file = kb / f"file_{i}.md"
            content = "\n".join([
                f"[Ref {j}](https://arxiv.org/abs/24{i:02d}.{j:05d})"
                for j in range(10)
            ])
            file.write_text(content)

        start = time.time()
        results = {}
        for f in kb.glob("*.md"):
            results[f.name] = validator.validate_file(f)
        duration = time.time() - start

        assert duration < 5.0, f"Too slow for large KB: {duration:.3f}s"
        assert len(results) == 100


class TestCLIIntegration:
    """CLI must exit with correct codes for CI/CD."""

    def test_cli_exits_0_on_clean_kb(self, tmp_path):
        """Clean KB should exit 0."""
        import subprocess
        import sys

        file = tmp_path / "clean.md"
        file.write_text("[Valid](https://arxiv.org/abs/2412.02646)")

        cmd = [sys.executable, "-m", "src.kb_quality.cli", str(file)]
        result = subprocess.run(cmd, capture_output=True, text=True)

        assert result.returncode == 0
        assert "✅" in result.stdout or "Validation complete" in result.stdout

    def test_cli_exits_1_on_invalid_kb(self, tmp_path):
        """KB with invalid citations should exit 1."""
        import subprocess
        import sys

        file = tmp_path / "invalid.md"
        file.write_text("[Bad](https://arxiv.org/abs/2025.mcp.taxonomy)")

        cmd = [sys.executable, "-m", "src.kb_quality.cli", str(file)]
        result = subprocess.run(cmd, capture_output=True, text=True)

        assert result.returncode == 1
        assert "❌" in result.stdout or "issues" in result.stdout.lower()

    def test_cli_report_includes_line_numbers(self, tmp_path):
        """Report must include line numbers for actionability."""
        import subprocess
        import sys

        file = tmp_path / "test.md"
        file.write_text("""Line 1
Line 2
Line 3: [Bad](https://arxiv.org/abs/2025.mcp.taxonomy)
Line 4
""")

        cmd = [sys.executable, "-m", "src.kb_quality.cli", str(file)]
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Must show line number
        assert "Line 3" in result.stdout or "line 3" in result.stdout.lower()


class TestDirectoryScanning:
    """Must handle directory validation correctly."""

    def test_scans_all_markdown_files(self, validator, tmp_path):
        """Should find all .md files recursively."""
        kb = tmp_path / "kb"
        (kb / "docs").mkdir(parents=True)
        (kb / "posts").mkdir(parents=True)

        # Create files in different directories
        (kb / "root.md").write_text("[Valid](https://arxiv.org/abs/2412.02646)")
        (kb / "docs" / "doc.md").write_text("[Valid](https://doi.org/10.1000/xyz)")
        (kb / "posts" / "post.md").write_text("[Bad](https://arxiv.org/abs/2025.mcp.taxonomy)")

        # Scan recursively
        all_files = list(kb.rglob("*.md"))
        assert len(all_files) == 3

        # Validate each
        results = {}
        for f in all_files:
            results[f.name] = validator.validate_file(f)

        # Should find 1 issue in post.md
        assert len(results["post.md"]) == 1
        assert len(results["root.md"]) == 0
        assert len(results["doc.md"]) == 0


class TestReportGeneration:
    """Reports must be human-readable and actionable."""

    def test_report_groups_by_severity(self, tmp_path):
        """Report should separate CRITICAL from WARNING."""
        from src.kb_quality.url_validator import CitationIssue, generate_report

        issues = [
            CitationIssue(
                line_number=3,
                url="https://arxiv.org/abs/2025.mcp.taxonomy",
                citation_text="[Bad](https://arxiv.org/abs/2025.mcp.taxonomy)",
                issue_type=ValidationIssue.INVALID_ARXIV_FORMAT,
                severity="CRITICAL",
                message="Invalid arXiv ID format"
            ),
        ]

        report = generate_report(issues, total_citations=10)

        assert "CRITICAL" in report
        assert "taxonomy" in report
        assert "Line 3" in report or "line 3" in report.lower()

    def test_report_shows_zero_issues(self):
        """Report should clearly show success when clean."""
        from src.kb_quality.url_validator import generate_report

        report = generate_report([], total_citations=100)

        assert "✅" in report or "All citations validated" in report
        assert "0 issues" in report.lower() or "no issues" in report.lower()
```

---

## Phase 2: Integration Tests (2 hours) - SHOULD IMPLEMENT

### Test File: `tests/kb_quality/test_integration.py`

```python
"""Integration tests for full workflow."""

import pytest
from pathlib import Path


def test_mixed_file_validation(tmp_path):
    """File with mix of good and bad citations."""
    validator = MarkdownKBValidator(enable_network_checks=False)

    file = tmp_path / "mixed.md"
    file.write_text("""
# Paper Review

Good citations:
- [Author (2024)](https://arxiv.org/abs/2412.02646)
- [Smith (2023)](https://doi.org/10.1000/example)

Bad citations:
- [Zhao (2025)](https://arxiv.org/abs/2025.mcp.taxonomy)
- [Li (2025)](https://arxiv.org/abs/2025.mcp.privilege)
""")

    issues = validator.validate_file(file)

    # Should find exactly 2 bad citations
    assert len(issues) == 2
    assert all(i.severity == "CRITICAL" for i in issues)

    # Line numbers should be correct
    line_numbers = [i.line_number for i in issues]
    assert all(ln > 5 for ln in line_numbers)  # Bad citations are after line 5


def test_pre_commit_hook_simulation(tmp_path):
    """Simulate pre-commit hook catching bad commit."""
    import subprocess

    # Create bad file
    bad_file = tmp_path / "bad_commit.md"
    bad_file.write_text("[Bad](https://arxiv.org/abs/2025.mcp.taxonomy)")

    # Simulate pre-commit hook
    # (In real hook, this would be git diff --cached --name-only)
    cmd = [
        "python", "-m", "src.kb_quality.cli",
        str(bad_file),
        "--fail-on-issues"
    ]

    result = subprocess.run(cmd, capture_output=True)

    # Hook should BLOCK the commit
    assert result.returncode != 0, "Pre-commit hook should block bad commits"
```

---

## Phase 3: Network Tests (2 hours) - OPTIONAL

**Only implement AFTER Phases 1-2 are complete and working.**

### Test File: `tests/kb_quality/test_network_optional.py`

```python
"""
OPTIONAL network validation tests.

These tests are SLOW and require network mocking.
Only run when --network flag is passed to validator.
"""

import pytest
import responses


@pytest.mark.network  # Mark as network test
@responses.activate
def test_detects_404_urls():
    """Network check can detect broken links."""
    validator = MarkdownKBValidator(enable_network_checks=True)

    url = "https://example.com/404"
    responses.add(responses.HEAD, url, status=404)

    exists, msg = validator._check_url_existence(url)

    assert not exists
    assert "404" in msg


@pytest.mark.network
@responses.activate
def test_skips_network_when_disabled():
    """Network checks should be skippable."""
    validator = MarkdownKBValidator(enable_network_checks=False)

    # This would 404, but should be skipped
    url = "https://example.com/broken"
    responses.add(responses.HEAD, url, status=404)

    # Should not call network
    issue = validator._validate_url(url, f"[Test]({url})", 1)

    # Should only check format, not network
    assert issue is None  # URL format is valid
    assert len(responses.calls) == 0  # No network call made
```

---

## Running the Tests

### Phase 1 Only (Fast - suitable for pre-commit)
```bash
pytest tests/kb_quality/test_format_validation_mvp.py -v
# Expected: <2 seconds
```

### Phase 1 + 2 (Full validation)
```bash
pytest tests/kb_quality/ -v --ignore=test_network_optional.py
# Expected: <5 seconds
```

### All Tests (Including optional network)
```bash
pytest tests/kb_quality/ -v -m network
# Expected: ~10 seconds (with mocks)
```

---

## Success Criteria by Phase

### Phase 1 (MVP)
- ✅ All October 26 patterns caught (100% success rate)
- ✅ Format validation <100ms per file
- ✅ CLI exits with correct codes
- ✅ Reports include line numbers

### Phase 2 (Integration)
- ✅ Mixed files validated correctly
- ✅ Directory scanning works
- ✅ Pre-commit hook simulation passes

### Phase 3 (Optional Network)
- ✅ 404 detection works (when enabled)
- ✅ Network checks skippable
- ✅ No impact on Phase 1/2 speed

---

## Key Differences from OpenAI's Plan

| Aspect | OpenAI | Our Plan | Why |
|--------|--------|----------|-----|
| **Network checks** | Default enabled | Default DISABLED | Pre-commit speed |
| **Retry logic** | Included | Deferred | Premature optimization |
| **JSON reports** | Included | Deferred | Not MVP |
| **October 26 focus** | Implicit | Explicit test class | Prevent regression |
| **Performance tests** | Missing | Required | Pre-commit requirement |
| **Phase separation** | Mixed | Clear 1/2/3 | Incremental delivery |

**Core principle**: Catch the October 26 patterns FIRST (format validation), add robustness LATER.
