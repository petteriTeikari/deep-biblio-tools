"""Debug logging utilities for citation pipeline.

This module provides structured debug logging and artifact generation
for the markdown → LaTeX → PDF pipeline. Each stage produces JSON/text
artifacts for inspection and regression testing.

Usage:
    debugger = PipelineDebugger(output_dir)
    debugger.log_stage(1, "Citation Extraction")
    debugger.dump_json(citations_data, "debug-01-extracted-citations.json")
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PipelineDebugger:
    """Manages debug artifacts for each pipeline stage.

    Attributes:
        output_dir: Directory where debug artifacts are saved
        logger: Logger instance for this debugger
    """

    def __init__(self, output_dir: Path):
        """Initialize debugger with output directory.

        Args:
            output_dir: Path where debug files will be written
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("pipeline_debug")

    def log_stage(self, stage_num: int, stage_name: str) -> None:
        """Log start of pipeline stage with visual separator.

        Args:
            stage_num: Stage number (1-7)
            stage_name: Descriptive name of the stage
        """
        self.logger.info("=" * 80)
        self.logger.info(f"STAGE {stage_num}: {stage_name}")
        self.logger.info("=" * 80)

    def dump_json(self, data: Any, filename: str) -> Path:
        """Save debug data as JSON with pretty printing.

        Args:
            data: Data to serialize (must be JSON-serializable)
            filename: Name of output file (e.g., "debug-01-citations.json")

        Returns:
            Path to saved file
        """
        path = self.output_dir / filename
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            self.logger.info(f"Saved debug JSON: {path}")
            return path
        except (TypeError, ValueError) as e:
            self.logger.error(f"Failed to serialize JSON for {filename}: {e}")
            # Save error info instead
            error_data = {
                "error": str(e),
                "data_type": str(type(data)),
                "data_repr": repr(data)[:500],
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(error_data, f, indent=2)
            return path

    def dump_text(self, content: str, filename: str) -> Path:
        """Save debug data as plain text.

        Args:
            content: Text content to save
            filename: Name of output file (e.g., "debug-02-raw-bibtex.bib")

        Returns:
            Path to saved file
        """
        path = self.output_dir / filename
        path.write_text(content, encoding="utf-8")
        self.logger.info(f"Saved debug text: {path}")
        return path

    def log_stats(self, **kwargs: Any) -> None:
        """Log key-value statistics for current stage.

        Args:
            **kwargs: Arbitrary statistics to log (e.g., total=366, matched=364)
        """
        for key, value in kwargs.items():
            self.logger.info(f"  {key}: {value}")

    def log_sample(
        self, items: list, label: str = "items", max_show: int = 5
    ) -> None:
        """Log first N items from a list for inspection.

        Args:
            items: List of items to sample
            label: Description of what's being sampled
            max_show: Maximum number of items to show
        """
        total = len(items)
        shown = min(total, max_show)
        self.logger.info(f"Sample {label} (showing {shown}/{total}):")

        for i, item in enumerate(items[:max_show], 1):
            # Handle different item types
            if hasattr(item, "__dict__"):
                # Objects with __dict__
                item_repr = {
                    k: v
                    for k, v in item.__dict__.items()
                    if not k.startswith("_")
                }
                self.logger.info(f"  [{i}] {item_repr}")
            elif isinstance(item, dict):
                # Dictionaries
                self.logger.info(f"  [{i}] {item}")
            else:
                # Primitive types
                self.logger.info(f"  [{i}] {item}")
