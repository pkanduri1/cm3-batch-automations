"""Tests for chunked validation result adapter."""

from src.reporting.result_adapter_chunked import adapt_chunked_validation_result


def test_adapt_chunked_validation_result_includes_required_sections():
    chunked_result = {
        'valid': True,
        'timestamp': '2026-02-18T23:00:00',
        'total_rows': 10,
        'actual_columns': ['a', 'b'],
        'errors': [],
        'warnings': [],
        'info': [],
        'statistics': {
            'null_counts': {'a': 1, 'b': 0},
            'empty_string_counts': {'a': 2, 'b': 1},
            'duplicate_count': 1,
            'chunk_size': 500,
            'elapsed_seconds': 0.25,
            'rows_per_second': 40.0,
        }
    }

    model = adapt_chunked_validation_result(chunked_result, file_path='data/sample.txt', mapping='map.json')

    assert 'quality_metrics' in model
    assert 'field_analysis' in model
    assert 'date_analysis' in model
    assert 'business_rules' in model
    assert model['appendix']['validation_config']['mode'] == 'chunked'
    assert model['appendix']['validation_config']['chunk_size'] == 500
    assert model['appendix']['validation_config']['rows_per_second'] == 40.0
