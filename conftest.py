"""Pytest bootstrap: ensure repo root is importable and isolate the journal."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault(
    "ARGUS_JOURNAL", os.path.join(tempfile.gettempdir(), "argus_pytest_journal.jsonl")
)
