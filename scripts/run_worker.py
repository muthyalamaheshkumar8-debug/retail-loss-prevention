"""Run the worker from the repository root so it shares the API's .env and paths."""

import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
runpy.run_module("app.worker", run_name="__main__")
