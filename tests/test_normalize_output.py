import json
from pathlib import Path

from src.extraction.normalize_output import normalize_invoice

def load_json(path: Path):
    """Small helper to read JSON from a file."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_normalize_matches_example():
    """
    Given a sample raw Azure DI output (from samples/raw_output_example.json),
    normalize_invoice() should produce exactly the normalized JSON
    we saved in samples/normalized_output_example.json.
    """
    # Find project root (one level up from this tests/ folder)
    root = Path(__file__).resolve().parents[1]

    raw_path = root / "samples" / "raw_output_example.json"
    expected_path = root / "samples" / "normalized_output_example.json"

    raw = load_json(raw_path)
    expected = load_json(expected_path)

    # Call your normalization logic
    normalized = normalize_invoice(raw)

    # Check that the result matches what we expect
    assert normalized == expected