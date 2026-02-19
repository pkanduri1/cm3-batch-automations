"""Tests for chunked validator performance statistics."""

import os
import tempfile

from src.parsers.chunked_validator import ChunkedFileValidator


def test_chunked_validator_returns_processing_stats():
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write('a|b|c\n')
        f.write('d|e|f\n')
        f.write('g|h|i\n')
        temp_file = f.name

    try:
        validator = ChunkedFileValidator(file_path=temp_file, delimiter='|', chunk_size=2)
        result = validator.validate(show_progress=False)

        stats = result.get('statistics', {})
        assert 'elapsed_seconds' in stats
        assert 'rows_per_second' in stats
        assert stats.get('chunk_size') == 2
        assert stats.get('elapsed_seconds', 0) >= 0
    finally:
        os.unlink(temp_file)
