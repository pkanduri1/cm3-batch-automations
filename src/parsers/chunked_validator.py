"""Chunked file validator for memory-efficient validation."""

import pandas as pd
from typing import Dict, Any, List, Optional
from .chunked_parser import ChunkedFileParser
from ..utils.progress import ProgressTracker
from ..utils.memory_monitor import MemoryMonitor
from ..utils.logger import get_logger


class ChunkedFileValidator:
    """Validate large files in chunks."""
    
    def __init__(self, file_path: str, delimiter: str = '|',
                 chunk_size: int = 100000, parser: Optional[ChunkedFileParser] = None):
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
    
    def validate(self, show_progress: bool = True) -> Dict[str, Any]:
        """Validate file in chunks.
        
        Args:
            show_progress: Show progress bar
            
        Returns:
            Validation results dictionary
        """
        self.logger.info(f"Starting chunked validation: {self.file_path}")
        self.memory_monitor.log_memory_usage("validation start")
        
        errors = []
        warnings = []
        
        # Validate structure first
        parser = self.parser or ChunkedFileParser(self.file_path, self.delimiter, self.chunk_size)
        structure_result = parser.validate_structure()
        
        if not structure_result['valid']:
            return structure_result
        
        # Add structure warnings
        warnings.extend(structure_result.get('warnings', []))
        
        # Initialize statistics
        total_rows = 0
        total_nulls = {}
        total_empty_strings = {}
        duplicate_count = 0
        seen_rows = set()  # For duplicate detection (memory-limited)
        max_seen_rows = 100000  # Limit duplicate tracking
        
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
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'file_path': self.file_path,
                'total_rows': total_rows,
                'statistics': {
                    'null_counts': total_nulls,
                    'empty_string_counts': total_empty_strings,
                    'duplicate_count': duplicate_count,
                    'duplicate_check_limited': len(seen_rows) >= max_seen_rows
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
        basic_result = self.validate(show_progress=False)
        
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
            'file_path': self.file_path,
            'total_rows': basic_result.get('total_rows', 0),
            'expected_columns': expected_columns,
            'actual_columns': list(actual_columns),
            'missing_required': list(missing_required),
            'unexpected': list(unexpected),
            'statistics': basic_result.get('statistics', {})
        }
