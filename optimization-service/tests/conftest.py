"""
Shared fixtures for optimization-service tests.

Engine tests (inner_calculator, master_optimizer, pipeline) need no DB or app.
JWT helpers are provided for future API-level tests.
"""
from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub heavy optional deps so the engine modules can be imported without
# the full Docker environment (plotly, reportlab, etc.)
# ---------------------------------------------------------------------------
for mod in [
    "plotly", "plotly.graph_objects", "plotly.io",
    "reportlab", "reportlab.lib", "reportlab.lib.pagesizes",
    "reportlab.lib.units", "reportlab.platypus",
    "reportlab.platypus.flowables", "reportlab.lib.utils",
    "matplotlib", "matplotlib.patches", "matplotlib.pyplot",
    "PIL", "PIL.Image",
]:
    sys.modules.setdefault(mod, MagicMock())

