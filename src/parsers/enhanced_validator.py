"""Enhanced file validation with data profiling and quality metrics."""

import os
import re
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime
from .base_parser import BaseParser


class EnhancedFileValidator:
    """Enhanced validator with comprehensive data profiling and quality metrics."""

    def __init__(self, parser: BaseParser, mapping_config: Optional[Dict] = None, 
                 rules_config_path: Optional[str] = None):
        """Initialize enhanced validator.
        
        Args:
            parser: Parser instance to use for validation
            mapping_config: Optional mapping configuration for schema validation
            rules_config_path: Optional path to business rules JSON configuration
        """
        self.parser = parser
        self.mapping_config = mapping_config
        self.rules_config_path = rules_config_path
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.info: List[Dict[str, Any]] = []
        self.rule_engine = None
        
        # Load business rules if provided
        if rules_config_path:
            self.rule_engine = self._load_rule_engine(rules_config_path)

    def validate(self, detailed: bool = True, strict_fixed_width: bool = False, strict_level: str = 'all') -> Dict[str, Any]:
        """Perform comprehensive file validation with data profiling.
        
        Args:
            detailed: Include detailed field-level analysis
        
        Returns:
            Comprehensive validation results dictionary
        """
        self.errors = []
        self.warnings = []
        self.info = []

        # File metadata
        file_metadata = self._get_file_metadata()

        # Check file exists
        if not self._validate_file_exists():
            return self._build_result(False, file_metadata, None)

        # Check file size
        self._validate_file_size()

        # Check file format
        if not self._validate_format():
            return self._build_result(False, file_metadata, None)

        # Parse and analyze data
        try:
            df = self.parser.parse()

            strict_fixed_width_result = None
            if strict_fixed_width:
                strict_fixed_width_result = self._validate_strict_fixed_width(strict_level=strict_level)
            
            # Data quality metrics
            quality_metrics = self._calculate_quality_metrics(df)
            
            # Field-level analysis
            field_analysis = self._analyze_fields(df) if detailed else {}
            
            # Duplicate analysis
            duplicate_analysis = self._analyze_duplicates(df)
            
            # Date field analysis
            date_analysis = self._analyze_date_fields(df) if detailed else {}
            
            # Schema validation (if mapping provided)
            if self.mapping_config:
                self._validate_schema(df)
            
            # Data profiling
            data_profile = self._profile_data(df) if detailed else {}
            
            # Appendix data
            appendix_data = self._build_appendix_data(df, detailed)
            
            # Business rules validation
            business_rules_result = self._validate_business_rules(df) if self.rule_engine else None
            
        except Exception as e:
            self.errors.append({
                'severity': 'critical',
                'category': 'parsing',
                'message': f"Parse error: {str(e)}",
                'row': None,
                'field': None
            })
            return self._build_result(False, file_metadata, None)

        # Build comprehensive result
        return self._build_result(
            valid=len(self.errors) == 0,
            file_metadata=file_metadata,
            df=df,
            quality_metrics=quality_metrics,
            field_analysis=field_analysis,
            duplicate_analysis=duplicate_analysis,
            date_analysis=date_analysis,
            data_profile=data_profile,
            appendix=appendix_data,
            business_rules=business_rules_result,
            strict_fixed_width=strict_fixed_width_result
        )

    def _normalize_cobol_date_format(self, fmt: str) -> str:
        """Normalize common COBOL date tokens to strptime-style formats."""
        if not fmt:
            return fmt
        f = fmt.upper()
        # Order matters
        f = f.replace('YYYY', '%Y').replace('CCYY', '%Y')
        f = f.replace('YY', '%y')
        f = f.replace('MM', '%m')
        f = f.replace('DD', '%d')
        return f

    def _format_to_regex(self, fmt: str) -> Optional[str]:
        """Convert subset of COBOL/picture formats to regex."""
        if not fmt:
            return None
        fmt = fmt.strip().upper()

        if fmt in {'CCYYMMDD', 'YYYYMMDD'}:
            return r'^\d{8}$'

        # Examples: 9(5), +9(12), +9(12)V9(6)
        m = re.fullmatch(r'\+?9\((\d+)\)(V9\((\d+)\))?', fmt)
        if m:
            int_digits = int(m.group(1))
            frac_digits = int(m.group(3)) if m.group(3) else 0
            sign = r'[+-]' if fmt.startswith('+') else ''
            return f'^{sign}\\d{{{int_digits + frac_digits}}}$'

        return None

    def _validate_strict_fixed_width(self, strict_level: str = 'all') -> Dict[str, Any]:
        """Strict fixed-width validation: record length + per-field format checks."""
        result = {
            'enabled': False,
            'strict_level': strict_level,
            'total_records_checked': 0,
            'invalid_records': 0,
            'invalid_row_numbers': [],
            'record_length_errors': 0,
            'format_errors': 0,
            'sample_issues': []
        }

        if not self.mapping_config or 'fields' not in self.mapping_config:
            self.warnings.append({
                'severity': 'warning',
                'category': 'strict_fixed_width',
                'message': 'Strict fixed-width requested but mapping has no fields metadata; skipping strict checks.',
                'row': None,
                'field': None
            })
            return result

        fields = self.mapping_config.get('fields', [])
        if not fields:
            return result

        result['enabled'] = True

        expected_record_length = self.mapping_config.get('total_record_length')
        if not expected_record_length:
            expected_record_length = max(int(f.get('position', 1)) - 1 + int(f.get('length', 0)) for f in fields)

        invalid_rows = set()

        with open(self.parser.file_path, 'r', encoding='utf-8', errors='replace') as fh:
            for row_idx, raw in enumerate(fh, start=1):
                line = raw.rstrip('\n')
                result['total_records_checked'] += 1
                row_has_error = False

                if len(line) != int(expected_record_length):
                    result['record_length_errors'] += 1
                    row_has_error = True
                    issue = {
                        'severity': 'error',
                        'category': 'strict_fixed_width',
                        'message': f"Record length mismatch at row {row_idx}: expected {expected_record_length}, got {len(line)}",
                        'row': row_idx,
                        'field': None,
                        'expected': expected_record_length,
                        'actual': len(line),
                        'code': 'FW_LEN_001'
                    }
                    self.errors.append(issue)
                    if len(result['sample_issues']) < 50:
                        result['sample_issues'].append(issue)

                for f in fields:
                    name = f.get('name')
                    pos = int(f.get('position', 1))
                    flen = int(f.get('length', 0))
                    required = bool(f.get('required', False))
                    fmt = f.get('format')
                    valid_values = f.get('valid_values', [])

                    start = pos - 1
                    segment = line[start:start + flen] if start < len(line) else ''

                    # Preserve spaces; empty means all spaces or blank segment
                    is_empty = (segment.strip() == '')
                    if is_empty:
                        if required:
                            row_has_error = True
                            issue = {
                                'severity': 'error',
                                'category': 'strict_fixed_width',
                                'message': f"Required field '{name}' is empty at row {row_idx}",
                                'row': row_idx,
                                'field': name,
                                'expected': 'non-empty value',
                                'actual': segment,
                                'raw_value': segment,
                                'code': 'FW_REQ_001'
                            }
                            self.errors.append(issue)
                            if len(result['sample_issues']) < 50:
                                result['sample_issues'].append(issue)
                        # Non-required empty is allowed
                        continue

                    if strict_level in ('format', 'all'):
                        # If non-empty, format must be valid when format is provided
                        regex = self._format_to_regex(fmt) if fmt else None
                        if regex and not re.fullmatch(regex, segment):
                            result['format_errors'] += 1
                            row_has_error = True
                            issue = {
                                'severity': 'error',
                                'category': 'strict_fixed_width',
                                'message': f"Field '{name}' invalid format at row {row_idx}. Expected format: {fmt}",
                                'row': row_idx,
                                'field': name,
                                'expected_format': fmt,
                                'actual': segment,
                                'raw_value': segment,
                                'code': 'FW_FMT_001'
                            }
                            self.errors.append(issue)
                            if len(result['sample_issues']) < 50:
                                result['sample_issues'].append(issue)

                        # Allowed-values check: optional empty is allowed, but non-empty must be valid
                        if valid_values:
                            actual_value = segment.strip()
                            if actual_value and actual_value not in valid_values:
                                row_has_error = True
                                issue = {
                                    'severity': 'error',
                                    'category': 'strict_fixed_width',
                                    'message': (
                                        f"Field '{name}' has invalid value at row {row_idx}. "
                                        f"Expected one of: {valid_values}"
                                    ),
                                    'row': row_idx,
                                    'field': name,
                                    'expected_values': valid_values,
                                    'actual': actual_value,
                                    'raw_value': segment,
                                    'code': 'FW_VAL_001'
                                }
                                self.errors.append(issue)
                                if len(result['sample_issues']) < 50:
                                    result['sample_issues'].append(issue)

                if row_has_error:
                    result['invalid_records'] += 1
                    invalid_rows.add(row_idx)

        result['invalid_row_numbers'] = sorted(invalid_rows)
        return result

    def _get_file_metadata(self) -> Dict[str, Any]:
        """Get file metadata."""
        file_path = self.parser.file_path
        
        if not os.path.exists(file_path):
            return {'file_path': file_path, 'exists': False}
        
        stat = os.stat(file_path)
        
        return {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'exists': True,
            'size_bytes': stat.st_size,
            'size_mb': stat.st_size / (1024 * 1024),
            'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'format': self.parser.__class__.__name__.replace('Parser', '').lower()
        }

    def _validate_file_exists(self) -> bool:
        """Check if file exists."""
        if not os.path.exists(self.parser.file_path):
            self.errors.append({
                'severity': 'critical',
                'category': 'file',
                'message': f"File not found: {self.parser.file_path}",
                'row': None,
                'field': None
            })
            return False
        return True

    def _validate_file_size(self) -> None:
        """Check file size."""
        size = os.path.getsize(self.parser.file_path)
        
        if size == 0:
            self.errors.append({
                'severity': 'critical',
                'category': 'file',
                'message': "File is empty",
                'row': None,
                'field': None
            })
        elif size < 10:
            self.warnings.append({
                'severity': 'warning',
                'category': 'file',
                'message': "File is very small (< 10 bytes)",
                'row': None,
                'field': None
            })
        elif size > 1024 * 1024 * 1024:  # 1GB
            self.info.append({
                'severity': 'info',
                'category': 'file',
                'message': f"Large file detected ({size / (1024**3):.2f} GB)",
                'row': None,
                'field': None
            })

    def _validate_format(self) -> bool:
        """Validate file format."""
        try:
            if not self.parser.validate_format():
                self.errors.append({
                    'severity': 'critical',
                    'category': 'format',
                    'message': "Invalid file format",
                    'row': None,
                    'field': None
                })
                return False
            return True
        except Exception as e:
            self.errors.append({
                'severity': 'critical',
                'category': 'format',
                'message': f"Format validation error: {str(e)}",
                'row': None,
                'field': None
            })
            return False

    def _calculate_quality_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate overall data quality metrics."""
        total_cells = df.shape[0] * df.shape[1]
        null_cells = df.isnull().sum().sum()
        filled_cells = total_cells - null_cells
        
        # Completeness
        completeness = (filled_cells / total_cells * 100) if total_cells > 0 else 0
        
        # Uniqueness
        total_rows = len(df)
        unique_rows = len(df.drop_duplicates())
        uniqueness = (unique_rows / total_rows * 100) if total_rows > 0 else 0
        
        # Overall quality score (weighted average)
        quality_score = (completeness * 0.6 + uniqueness * 0.4)
        
        return {
            'total_rows': total_rows,
            'total_columns': df.shape[1],
            'total_cells': total_cells,
            'filled_cells': filled_cells,
            'null_cells': null_cells,
            'completeness_pct': round(completeness, 2),
            'unique_rows': unique_rows,
            'duplicate_rows': total_rows - unique_rows,
            'uniqueness_pct': round(uniqueness, 2),
            'quality_score': round(quality_score, 2)
        }

    def _analyze_fields(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """Perform field-level analysis."""
        field_analysis = {}
        
        for col in df.columns:
            field_analysis[col] = self._analyze_field(df[col], col)
        
        return field_analysis

    def _analyze_field(self, series: pd.Series, field_name: str) -> Dict[str, Any]:
        """Analyze a single field."""
        total = len(series)
        null_count = series.isnull().sum()
        filled_count = total - null_count
        fill_rate = (filled_count / total * 100) if total > 0 else 0
        
        # Infer data type
        dtype = str(series.dtype)
        inferred_type = self._infer_data_type(series)
        
        # Unique values
        unique_count = series.nunique()
        unique_ratio = (unique_count / filled_count * 100) if filled_count > 0 else 0
        
        # Sample values
        sample_values = series.dropna().head(5).tolist()
        
        analysis = {
            'data_type': dtype,
            'inferred_type': inferred_type,
            'total_values': total,
            'null_count': null_count,
            'filled_count': filled_count,
            'fill_rate_pct': round(fill_rate, 2),
            'unique_count': unique_count,
            'unique_ratio_pct': round(unique_ratio, 2),
            'sample_values': [str(v) for v in sample_values]
        }
        
        # Numeric analysis
        if inferred_type == 'numeric':
            analysis.update(self._analyze_numeric_field(series))
        
        # String analysis
        elif inferred_type == 'string':
            analysis.update(self._analyze_string_field(series))
        
        return analysis

    def _infer_data_type(self, series: pd.Series) -> str:
        """Infer the actual data type of a field."""
        import re
        
        non_null = series.dropna()
        
        if len(non_null) == 0:
            return 'empty'
        
        # Check if field name suggests it's a date
        field_name = series.name if hasattr(series, 'name') else ''
        is_date_field = bool(re.search(r'date|time|dt|timestamp', str(field_name), re.IGNORECASE))
        
        # For potential date fields, try datetime first
        if is_date_field:
            # Check for YYYYMMDD pattern (8-digit dates) first
            # Sample first 100 values to check pattern
            sample = non_null.head(100).astype(str).str.strip()
            yyyymmdd_pattern = r'^\d{8}$'
            yyyymmdd_matches = sample.str.match(yyyymmdd_pattern).sum()
            
            if yyyymmdd_matches / len(sample) >= 0.8:  # 80% match YYYYMMDD pattern
                # Try to parse as dates
                try:
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        parsed = pd.to_datetime(sample, format='%Y%m%d', errors='coerce')
                        valid_dates = parsed.notna().sum()
                        if valid_dates / len(sample) >= 0.8:
                            return 'datetime'
                except:
                    pass
            
            # Try general datetime parsing for date fields
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    parsed = pd.to_datetime(non_null, errors='coerce')
                    valid_pct = parsed.notna().sum() / len(non_null) * 100
                    if valid_pct >= 50:
                        return 'datetime'
            except:
                pass
        
        # Try numeric (but only if not a date pattern)
        try:
            pd.to_numeric(non_null)
            return 'numeric'
        except:
            pass
        
        # Try datetime for non-date-named fields
        if not is_date_field:
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    pd.to_datetime(non_null)
                    return 'datetime'
            except:
                pass
        
        return 'string'

    def _analyze_numeric_field(self, series: pd.Series) -> Dict[str, Any]:
        """Analyze numeric field."""
        numeric_series = pd.to_numeric(series, errors='coerce').dropna()
        
        if len(numeric_series) == 0:
            return {}
        
        return {
            'min': float(numeric_series.min()),
            'max': float(numeric_series.max()),
            'mean': float(numeric_series.mean()),
            'median': float(numeric_series.median()),
            'std_dev': float(numeric_series.std())
        }

    def _analyze_string_field(self, series: pd.Series) -> Dict[str, Any]:
        """Analyze string field."""
        string_series = series.dropna().astype(str)
        
        if len(string_series) == 0:
            return {}
        
        lengths = string_series.str.len()
        
        return {
            'min_length': int(lengths.min()),
            'max_length': int(lengths.max()),
            'avg_length': round(float(lengths.mean()), 2)
        }

    def _analyze_duplicates(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze duplicate rows."""
        total_rows = len(df)
        unique_rows = len(df.drop_duplicates())
        duplicate_rows = total_rows - unique_rows
        
        # Find most duplicated rows
        if duplicate_rows > 0:
            dup_counts = df.groupby(list(df.columns)).size().reset_index(name='count')
            dup_counts = dup_counts[dup_counts['count'] > 1].sort_values('count', ascending=False)
            top_duplicates = dup_counts.head(10)['count'].tolist()
        else:
            top_duplicates = []
        
        return {
            'total_rows': total_rows,
            'unique_rows': unique_rows,
            'duplicate_rows': duplicate_rows,
            'duplicate_pct': round((duplicate_rows / total_rows * 100) if total_rows > 0 else 0, 2),
            'top_duplicate_counts': top_duplicates
        }

    def _validate_schema(self, df: pd.DataFrame) -> None:
        """Validate data against schema from mapping."""
        if not self.mapping_config or 'fields' not in self.mapping_config:
            return
        
        expected_fields = {f['name'] for f in self.mapping_config['fields']}
        actual_fields = set(df.columns)
        
        # Missing fields
        missing = expected_fields - actual_fields
        if missing:
            for field in missing:
                self.errors.append({
                    'severity': 'error',
                    'category': 'schema',
                    'message': f"Missing required field: {field}",
                    'row': None,
                    'field': field
                })
        
        # Extra fields
        extra = actual_fields - expected_fields
        if extra:
            for field in extra:
                self.warnings.append({
                    'severity': 'warning',
                    'category': 'schema',
                    'message': f"Unexpected field: {field}",
                    'row': None,
                    'field': field
                })

    def _profile_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate data profile statistics."""
        return {
            'row_count': len(df),
            'column_count': len(df.columns),
            'memory_usage_mb': round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2),
            'columns': list(df.columns)
        }

    def _analyze_date_fields(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze date/datetime fields comprehensively."""
        import warnings
        
        date_analysis = {}
        
        for col in df.columns:
            # Try to parse as datetime
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    date_series = pd.to_datetime(df[col], errors='coerce')
                
                # Check if at least 50% of values are valid dates
                valid_dates = date_series.notna()
                valid_pct = valid_dates.sum() / len(df) * 100 if len(df) > 0 else 0
                
                if valid_pct >= 50:  # Consider it a date field if >= 50% are valid dates
                    invalid_count = (~valid_dates).sum()
                    future_count = (date_series > pd.Timestamp.now()).sum()
                    null_count = df[col].isna().sum()
                    
                    # Detect date formats
                    detected_formats = self._detect_date_formats(df[col])
                    
                    # Calculate date range
                    valid_date_series = date_series[valid_dates]
                    if len(valid_date_series) > 0:
                        earliest = valid_date_series.min()
                        latest = valid_date_series.max()
                        date_range_days = (latest - earliest).days
                    else:
                        earliest = None
                        latest = None
                        date_range_days = 0
                    
                    date_analysis[col] = {
                        'earliest_date': earliest.isoformat() if earliest else None,
                        'latest_date': latest.isoformat() if latest else None,
                        'date_range_days': date_range_days,
                        'valid_date_count': valid_dates.sum(),
                        'valid_date_pct': round(valid_pct, 2),
                        'invalid_date_count': invalid_count,
                        'invalid_date_pct': round((invalid_count / len(df) * 100) if len(df) > 0 else 0, 2),
                        'future_date_count': future_count,
                        'future_date_pct': round((future_count / len(df) * 100) if len(df) > 0 else 0, 2),
                        'null_date_count': null_count,
                        'null_date_pct': round((null_count / len(df) * 100) if len(df) > 0 else 0, 2),
                        'detected_formats': detected_formats
                    }
                    
                    # Add warnings for invalid/future dates
                    if invalid_count > 0:
                        expected_format = self._get_expected_date_format(col)
                        format_hint = f" Expected format: {expected_format}." if expected_format else ""
                        self.warnings.append({
                            'severity': 'warning',
                            'category': 'data',
                            'message': (
                                f"Field '{col}' has {invalid_count} invalid date values "
                                f"({invalid_count / len(df) * 100:.2f}%).{format_hint}"
                            ),
                            'row': None,
                            'field': col,
                            'expected_format': expected_format
                        })
                    
                    if future_count > 0:
                        self.info.append({
                            'severity': 'info',
                            'category': 'data',
                            'message': f"Field '{col}' has {future_count} future date values ({future_count / len(df) * 100:.2f}%)",
                            'row': None,
                            'field': col
                        })
            except:
                continue
        
        return date_analysis

    def _get_expected_date_format(self, field_name: str) -> Optional[str]:
        """Get expected date format from mapping config, if provided."""
        if not self.mapping_config:
            return None

        # Universal mapping format
        for field in self.mapping_config.get('fields', []):
            if field.get('name') == field_name and field.get('format'):
                return str(field.get('format'))

        # Legacy mapping format
        for m in self.mapping_config.get('mappings', []):
            if m.get('source_column') == field_name:
                if m.get('format'):
                    return str(m.get('format'))
                for rule in m.get('validation_rules', []):
                    if rule.get('type') == 'date_format':
                        fmt = rule.get('parameters', {}).get('format')
                        if fmt:
                            return str(fmt)

        return None

    def _detect_date_formats(self, series: pd.Series) -> List[str]:
        """Detect common date formats in the series."""
        import warnings
        
        formats = []
        sample = series.dropna().head(100)
        
        if len(sample) == 0:
            return formats
        
        common_formats = [
            ('%Y-%m-%d', 'YYYY-MM-DD'),
            ('%m/%d/%Y', 'MM/DD/YYYY'),
            ('%d/%m/%Y', 'DD/MM/YYYY'),
            ('%Y%m%d', 'YYYYMMDD'),
            ('%m-%d-%Y', 'MM-DD-YYYY'),
            ('%d-%m-%Y', 'DD-MM-YYYY'),
            ('%Y/%m/%d', 'YYYY/MM/DD'),
        ]
        
        for fmt_code, fmt_name in common_formats:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    parsed = pd.to_datetime(sample, format=fmt_code, errors='coerce')
                    if parsed.notna().sum() / len(sample) > 0.8:
                        formats.append(fmt_name)
            except:
                continue
        
        return formats if formats else ['Mixed/Unknown']

    def _build_appendix_data(self, df: pd.DataFrame, detailed: bool) -> Dict[str, Any]:
        """Build appendix data for the report."""
        # Validation configuration
        validation_config = {
            'detailed_mode': detailed,
            'mapping_file': self.mapping_config.get('file_path') if self.mapping_config and 'file_path' in self.mapping_config else None,
            'validation_timestamp': datetime.now().isoformat(),
            'validator_version': '1.0.0'
        }
        
        # Mapping details
        mapping_details = self._get_mapping_details()
        
        # Affected rows summary
        all_issues = self.errors + self.warnings
        affected_rows_summary = self._get_affected_rows_summary(all_issues, len(df))
        
        return {
            'validation_config': validation_config,
            'mapping_details': mapping_details,
            'affected_rows': affected_rows_summary
        }

    def _get_mapping_details(self) -> Optional[Dict[str, Any]]:
        """Extract mapping file details."""
        if not self.mapping_config or 'fields' not in self.mapping_config:
            return None
        
        fields = self.mapping_config.get('fields', [])
        required_fields = [f['name'] for f in fields if f.get('required', False)]
        
        # Calculate total width for fixed-width files
        total_width = sum(f.get('length', 0) for f in fields)
        
        return {
            'total_fields': len(fields),
            'field_names': [f['name'] for f in fields],
            'required_fields': required_fields,
            'required_field_count': len(required_fields),
            'total_width': total_width if total_width > 0 else None
        }

    def _get_affected_rows_summary(self, issues: List[Dict], total_rows: int) -> Dict[str, Any]:
        """Get summary of rows affected by issues."""
        affected_rows = set()
        issues_by_row = {}
        
        for issue in issues:
            if 'row' in issue and issue['row'] is not None:
                row_num = issue['row']
                affected_rows.add(row_num)
                
                if row_num not in issues_by_row:
                    issues_by_row[row_num] = []
                issues_by_row[row_num].append(issue)
        
        # Get top 100 most problematic rows
        top_problematic = sorted(
            issues_by_row.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:100]
        
        return {
            'total_affected_rows': len(affected_rows),
            'affected_row_pct': round((len(affected_rows) / total_rows * 100) if total_rows > 0 else 0, 2),
            'top_problematic_rows': [
                {
                    'row_number': row,
                    'issue_count': len(issues),
                    'issues': [i.get('message', '') for i in issues[:10]]  # Limit to 10 issues per row
                }
                for row, issues in top_problematic
            ]
        }

    def _build_result(self, valid: bool, file_metadata: Dict[str, Any], 
                     df: Optional[pd.DataFrame], **kwargs) -> Dict[str, Any]:
        """Build comprehensive validation result."""
        result = {
            'valid': valid,
            'timestamp': datetime.now().isoformat(),
            'file_metadata': file_metadata,
            'errors': self.errors,
            'warnings': self.warnings,
            'info': self.info,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'info_count': len(self.info)
        }
        
        # Add optional components
        result.update(kwargs)
        
        return result
    
    def _load_rule_engine(self, rules_config_path: str):
        """Load business rules engine from configuration file."""
        import json
        from src.validators.rule_engine import RuleEngine
        
        try:
            with open(rules_config_path, 'r') as f:
                rules_config = json.load(f)
            
            return RuleEngine(rules_config)
        except Exception as e:
            self.warnings.append({
                'severity': 'warning',
                'category': 'business_rules',
                'message': f"Failed to load business rules: {str(e)}",
                'row': None,
                'field': None
            })
            return None
    
    def _validate_business_rules(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Execute business rules and return violations."""
        if not self.rule_engine:
            return {
                'violations': [],
                'statistics': {},
                'enabled': False
            }
        
        try:
            # Set total rows for compliance calculation
            self.rule_engine.set_total_rows(len(df))
            
            # Execute rules
            violations = self.rule_engine.validate(df)
            statistics = self.rule_engine.get_statistics()
            
            # Convert violations to dictionaries
            violations_dict = [v.to_dict() for v in violations]
            
            # Add rule violations to warnings/errors based on severity
            for violation in violations:
                if violation.severity == 'error':
                    self.errors.append({
                        'severity': 'error',
                        'category': 'business_rule',
                        'message': violation.message,
                        'row': violation.row_number,
                        'field': violation.field,
                        'rule_id': violation.rule_id,
                        'rule_name': violation.rule_name
                    })
                elif violation.severity == 'warning':
                    self.warnings.append({
                        'severity': 'warning',
                        'category': 'business_rule',
                        'message': violation.message,
                        'row': violation.row_number,
                        'field': violation.field,
                        'rule_id': violation.rule_id,
                        'rule_name': violation.rule_name
                    })
                else:  # info
                    self.info.append({
                        'severity': 'info',
                        'category': 'business_rule',
                        'message': violation.message,
                        'row': violation.row_number,
                        'field': violation.field,
                        'rule_id': violation.rule_id,
                        'rule_name': violation.rule_name
                    })
            
            return {
                'violations': violations_dict,
                'statistics': statistics,
                'enabled': True
            }
        
        except Exception as e:
            self.warnings.append({
                'severity': 'warning',
                'category': 'business_rules',
                'message': f"Error executing business rules: {str(e)}",
                'row': None,
                'field': None
            })
            return {
                'violations': [],
                'statistics': {},
                'enabled': False,
                'error': str(e)
            }
