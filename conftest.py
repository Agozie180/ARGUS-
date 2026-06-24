"""Pytest bootstrap: ensure repo root is importable and isolate the journal."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault(
    "ARGUS_JOURNAL", os.path.join(tempfile.gettempdir(), "argus_pytest_journal.jsonl")
)
# Keep the suite offline and deterministic: force the synthetic feed so tests
# never depend on Bitget being reachable. The live path is exercised manually
# via the Live Bitget Example page and the live_bitget unit tests.
os.environ.setdefault("ARGUS_LIVE_DATA", "false")
