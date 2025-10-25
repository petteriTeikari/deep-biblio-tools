#!/usr/bin/env python3
"""Check status of deep-biblio MCP server modules."""

import sys
from pathlib import Path

# Add server to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from deep_biblio.server import (
    DEEP_BIBLIO_AVAILABLE,
    DEEP_BIBLIO_PATH,
    MODULES_AVAILABLE,
)

print("## deep-biblio MCP Server Status\n")
print(f"**Path**: {DEEP_BIBLIO_PATH}")
print(f"**Exists**: {DEEP_BIBLIO_PATH.exists()}")
print(
    f"**Overall Status**: {'[PASS] Available' if DEEP_BIBLIO_AVAILABLE else '[FAIL] Not Available'}\n"
)

print("### Module Status:\n")
for module, available in MODULES_AVAILABLE.items():
    status_icon = "[PASS]" if available else "[FAIL]"
    print(f"- {status_icon} **{module}**: {available}")

available_count = sum(1 for v in MODULES_AVAILABLE.values() if v)
total_count = len(MODULES_AVAILABLE)

print(f"\n**Summary**: {available_count}/{total_count} modules available")

if available_count == 0:
    print("\n[WARNING]  **Warning**: No modules available!")
    print("Check that deep-biblio-tools is properly installed at:")
    print(f"  {DEEP_BIBLIO_PATH}")
    sys.exit(1)
elif available_count < total_count:
    print("\n[WARNING]  **Note**: Some modules are unavailable")
    print("This may be due to missing dependencies in deep-biblio-tools")
    sys.exit(0)
else:
    print("\n[PASS] **All modules available!**")
    sys.exit(0)
