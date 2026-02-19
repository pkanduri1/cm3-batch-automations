"""Tests for pipeline runner scaffold."""

import json
import os
import tempfile

from src.pipeline.runner import PipelineRunner


def _tmp_profile(profile: dict) -> str:
    f = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
    f.write(json.dumps(profile))
    f.close()
    return f.name


def test_pipeline_runner_dry_run_positive():
    p = _tmp_profile({
        'source_system': 'SRC_X',
        'stages': {
            'ingest': {'enabled': True, 'command': 'echo ingest'},
            'sqlloader': {'enabled': False},
            'java_batch': {'enabled': True, 'command': 'echo java'},
            'output_validation': {'enabled': True, 'command': 'echo validate'}
        }
    })
    try:
        out = PipelineRunner(p).run(dry_run=True)
        assert out['status'] == 'passed'
        assert any(s['status'] == 'dry_run' for s in out['steps'])
    finally:
        os.unlink(p)


def test_pipeline_runner_negative_missing_required_top_level():
    p = _tmp_profile({'stages': {}})
    try:
        try:
            PipelineRunner(p).run(dry_run=True)
            assert False, 'expected ValueError'
        except ValueError as e:
            assert 'Missing required top-level keys' in str(e)
    finally:
        os.unlink(p)
