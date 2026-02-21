"""Chunked file validator for memory-efficient validation."""

import json
import time
import pandas as pd
from typing import Dict, Any, List, Optional
from .chunked_parser import ChunkedFileParser
from ..utils.progress import ProgressTracker
from ..utils.memory_monitor import MemoryMonitor
from ..utils.logger import get_logger
from ..validators.rule_engine import RuleEngine


class ChunkedFileValidator:
    """Validate large files in chunks."""
    
    def __init__(self, file_path: str, delimiter: str = '|',
                 chunk_size: int = 100000, parser: Optional[ChunkedFileParser] = None,
                 rules_config_path: Optional[str] = None,
                 expected_row_length: Optional[int] = None):
        """Initialize chunked validator.
        
        Args:
            file_path: Path to file to validate
            delimiter: Field delimiter
            chunk_size: Rows per chunk
            parser: Optional preconfigured chunked parser (e.g., fixed-width parser)
        """
        self.file_path = file_path
        self.delimiter = delimiter
        self.chunk_size = chunk_size
        self.parser = parser
        self.logger = get_logger(__name__)
        self.memory_monitor = MemoryMonitor()
        self.rule_engine: Optional[RuleEngine] = None
        self._total_rows_for_rules = 0
        self.expected_row_length = expected_row_length

        if rules_config_path:
            try:
                with open(rules_config_path, 'r') as f:
                    rules_cfg = json.load(f)
                self.rule_engine = RuleEngine(rules_cfg)
            except Exception as e:
                self.logger.warning(f"Failed to load business rules: {e}")
    
    def validate(self, show_progress: bool = True) -> Dict[str, Any]:
        """Validate file in chunks.
        
        Args:
            show_progress: Show progress bar
            
        Returns:
            Validation results dictionary
        """
        self.logger.info(f"Starting chunked validation: {self.file_path}")
        self.memory_monitor.log_memory_usage("validation start")
        start_ts = time.time()

        errors = []
        warnings = []
        info = []
        
        # Validate structure first
        parser = self.parser or ChunkedFileParser(self.file_path, self.delimiter, self.chunk_size)
        structure_result = parser.validate_structure()
        
        if not structure_result['valid']:
            return structure_result
        
        # Add structure warnings
        warnings.extend(structure_result.get('warnings', []))

        # Fixed-width row-length validation (captures row-level defects)
        if self.expected_row_length:
            mismatch_count, length_issues, scanned_rows = self._scan_fixed_width_row_lengths()
            errors.extend(length_issues)
            if mismatch_count > len(length_issues):
                warnings.append(
                    f"Found {mismatch_count:,} row-length mismatches; showing first {len(length_issues):,} details"
                )

        # Initialize statistics
        total_rows = 0
        total_nulls = {}
        total_empty_strings = {}
        duplicate_count = 0
        seen_rows = set()  # For duplicate detection (memory-limited)
        max_seen_rows = 100000  # Limit duplicate tracking

        business_violations: list[dict] = []
        
        # Parse and validate chunks
        progress = ProgressTracker(parser.count_rows(), "Validating") if show_progress else None
        
        try:
            for chunk_num, chunk in enumerate(parser.parse_chunks(), 1):
                # Validate chunk
                chunk_errors, chunk_warnings, chunk_stats = self._validate_chunk(
                    chunk, chunk_num, seen_rows, max_seen_rows
                )
                
                errors.extend(chunk_errors)
                warnings.extend(chunk_warnings)
                
                # Update statistics
                total_rows += len(chunk)
                duplicate_count += chunk_stats['duplicates']

                # Optional business-rule validation
                if self.rule_engine is not None:
                    self.rule_engine.set_total_rows(total_rows)
                    violations = self.rule_engine.validate(chunk)
                    for v in violations:
                        vdict = v.to_dict()
                        business_violations.append(vdict)
                        issue = {
                            'severity': v.severity,
                            'category': 'business_rule',
                            'message': v.message,
                            'row': v.row_number,
                            'field': v.field,
                            'rule_id': v.rule_id,
                            'rule_name': v.rule_name,
                        }
                        if v.severity == 'error':
                            errors.append(issue)
                        elif v.severity == 'warning':
                            warnings.append(issue)
                        else:
                            info.append(issue)
                
                # Aggregate null counts
                for col, count in chunk_stats['nulls'].items():
                    total_nulls[col] = total_nulls.get(col, 0) + count
                
                # Aggregate empty string counts
                for col, count in chunk_stats['empty_strings'].items():
                    total_empty_strings[col] = total_empty_strings.get(col, 0) + count
                
                if progress:
                    progress.update(total_rows)
                
                # Periodic garbage collection
                if chunk_num % 10 == 0:
                    self.memory_monitor.force_garbage_collection()
            
            if progress:
                progress.finish()
            
            # Generate warnings for nulls and empty strings
            for col, count in total_nulls.items():
                if count > 0:
                    pct = (count / total_rows) * 100
                    warnings.append(
                        f"Column '{col}' has {count:,} null values ({pct:.1f}%)"
                    )
            
            for col, count in total_empty_strings.items():
                if count > 0:
                    pct = (count / total_rows) * 100
                    warnings.append(
                        f"Column '{col}' has {count:,} empty strings ({pct:.1f}%)"
                    )
            
            if duplicate_count > 0:
                warnings.append(
                    f"Found {duplicate_count:,} duplicate rows "
                    f"(limited to first {max_seen_rows:,} rows checked)"
                )
            
            self.logger.info(
                f"Validation complete: {total_rows:,} rows validated, "
                f"{len(errors)} errors, {len(warnings)} warnings"
            )
            self.memory_monitor.log_memory_usage("validation complete")
            
            elapsed = max(time.time() - start_ts, 0.0)
            rows_per_second = (total_rows / elapsed) if elapsed > 0 else 0.0

            business_stats = {
                'total_rules': len(self.rule_engine.rules) if self.rule_engine else 0,
                'enabled_rules': len(self.rule_engine.enabled_rules) if self.rule_engine else 0,
                'total_violations': len(business_violations),
            }

            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'info': info,
                'file_path': self.file_path,
                'total_rows': total_rows,
                'statistics': {
                    'null_counts': total_nulls,
                    'empty_string_counts': total_empty_strings,
                    'duplicate_count': duplicate_count,
                    'duplicate_check_limited': len(seen_rows) >= max_seen_rows,
                    'elapsed_seconds': round(elapsed, 6),
                    'rows_per_second': round(rows_per_second, 2),
                    'chunk_size': self.chunk_size,
                },
                'business_rules': {
                    'enabled': self.rule_engine is not None,
                    'violations': business_violations,
                    'statistics': business_stats,
                }
            }
            
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return {
                'valid': False,
                'errors': [f"Validation failed: {str(e)}"],
                'warnings': warnings,
                'file_path': self.file_path
            }
    
    def _scan_fixed_width_row_lengths(self, max_issue_details: int = 200) -> tuple[int, list[dict], int]:
        """Scan file line lengths and return mismatch diagnostics.

        Returns:
            (mismatch_count, sampled_issue_dicts, total_rows_scanned)
        """
        if not self.expected_row_length:
            return 0, [], 0

        mismatch_count = 0
        sampled: list[dict] = []
        total_rows = 0

        with open(self.file_path, 'r', encoding='utf-8', errors='replace') as fh:
            for row_num, line in enumerate(fh, start=1):
                total_rows = row_num
                actual_len = len(line.rstrip('\r\n'))
                if actual_len != self.expected_row_length:
                    mismatch_count += 1
                    if len(sampled) < max_issue_details:
                        sampled.append({
                            'severity': 'error',
                            'category': 'format',
                            'code': 'FW_LEN_001',
                            'message': (
                                f"Row {row_num} length mismatch: expected {self.expected_row_length}, got {actual_len}"
                            ),
                            'row': row_num,
                            'field': None,
                        })

        return mismatch_count, sampled, total_rows

    def _validate_chunk(self, chunk: pd.DataFrame, chunk_num: int,
                       seen_rows: set, max_seen_rows: int) -> tuple:
        """Validate a single chunk.
        
        Args:
            chunk: DataFrame chunk
            chunk_num: Chunk number
            seen_rows: Set of seen row hashes for duplicate detection
            max_seen_rows: Maximum rows to track for duplicates
            
        Returns:
            Tuple of (errors, warnings, statistics)
        """
        errors = []
        warnings = []
        stats = {
            'duplicates': 0,
            'nulls': {},
            'empty_strings': {}
        }
        
        # Check for empty chunk
        if chunk.empty:
            warnings.append(f"Chunk {chunk_num} is empty")
            return errors, warnings, stats
        
        # Check for duplicate rows (memory-limited)
        if len(seen_rows) < max_seen_rows:
            for idx, row in chunk.iterrows():
                row_hash = hash(tuple(row.values))
                if row_hash in seen_rows:
                    stats['duplicates'] += 1
                else:
                    seen_rows.add(row_hash)
        
        # Check for null values
        null_counts = chunk.isnull().sum()
        for col, count in null_counts.items():
            if count > 0:
                stats['nulls'][col] = int(count)
        
        # Check for empty strings
        for col in chunk.columns:
            if chunk[col].dtype == 'object':
                empty_count = (chunk[col] == '').sum()
                if empty_count > 0:
                    stats['empty_strings'][col] = int(empty_count)
        
        return errors, warnings, stats
    
    def validate_with_schema(self, expected_columns: List[str],
                            required_columns: Optional[List[str]] = None,
                            show_progress: bool = True) -> Dict[str, Any]:
        """Validate file against expected schema.
        
        Args:
            expected_columns: List of expected column names
            required_columns: List of required column names
            show_progress: Show progress bar
            
        Returns:
            Validation results dictionary
        """
        required_columns = required_columns or expected_columns
        
        # First validate basic structure
        basic_result = self.validate(show_progress=show_progress)
        
        if not basic_result['valid']:
            return basic_result
        
        errors = list(basic_result.get('errors', []))
        warnings = list(basic_result.get('warnings', []))
        
        # Get actual columns from first chunk
        parser = self.parser or ChunkedFileParser(self.file_path, self.delimiter, self.chunk_size)
        first_chunk = parser.parse_sample(n_rows=10)
        actual_columns = set(first_chunk.columns)
        
        # Check required columns
        expected_set = set(expected_columns)
        required_set = set(required_columns)
        
        missing_required = required_set - actual_columns
        if missing_required:
            errors.append(f"Missing required columns: {sorted(missing_required)}")
        
        # Check for unexpected columns
        unexpected = actual_columns - expected_set
        if unexpected:
            warnings.append(f"Unexpected columns: {sorted(unexpected)}")
        
        # Check for missing optional columns
        missing_optional = expected_set - required_set - actual_columns
        if missing_optional:
            warnings.append(f"Missing optional columns: {sorted(missing_optional)}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'info': basic_result.get('info', []),
            'file_path': self.file_path,
            'total_rows': basic_result.get('total_rows', 0),
            'expected_columns': expected_columns,
            'actual_columns': list(actual_columns),
            'missing_required': list(missing_required),
            'unexpected': list(unexpected),
            'statistics': basic_result.get('statistics', {}),
            'business_rules': basic_result.get('business_rules', {'enabled': False, 'violations': [], 'statistics': {}}),
        }
