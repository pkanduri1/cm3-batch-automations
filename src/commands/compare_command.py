from __future__ import annotations

import sys
from pathlib import Path
import click


def run_compare_command(file1, file2, keys, mapping, output, thresholds, detailed, chunk_size, progress, use_chunked, logger):
    """Compare two files and generate report."""
    try:
        from src.parsers.format_detector import FormatDetector
        from src.comparators.file_comparator import FileComparator
        from src.comparators.chunked_comparator import ChunkedFileComparator
        from src.reports.renderers.comparison_renderer import HTMLReporter
        from src.validators.threshold import ThresholdEvaluator, ThresholdConfig
        from src.config.loader import ConfigLoader
        
        # Parse key columns if provided
        if keys:
            key_columns = [k.strip() for k in keys.split(',')]
            comparison_mode = "key-based"
        else:
            key_columns = None
            comparison_mode = "row-by-row"
            click.echo(f"No keys provided - using row-by-row comparison...")
        
        # Use chunked processing for large files
        if use_chunked:
            if not keys:
                click.echo(click.style("Error: Row-by-row comparison is not supported with chunked processing.", fg='red'))
                click.echo("Please provide key columns with -k option or use standard comparison (remove --use-chunked).")
                sys.exit(1)
            
            click.echo(f"Using chunked processing (chunk size: {chunk_size:,})...")
            
            # Detect delimiter from file extension
            delimiter = ','  # Default to comma for CSV
            if file1.endswith('.txt') or file1.endswith('.dat'):
                delimiter = '|'  # Pipe for text files
            
            comparator = ChunkedFileComparator(
                file1, file2, key_columns,
                delimiter=delimiter,
                chunk_size=chunk_size
            )
            results = comparator.compare(detailed=detailed, show_progress=progress)
        else:
            # Parse both files (original method)
            detector = FormatDetector()
            import json
            from src.parsers.fixed_width_parser import FixedWidthParser

            mapping_config = None
            if mapping:
                with open(mapping, 'r') as f:
                    mapping_config = json.load(f)

            def _build_fixed_width_specs(cfg):
                field_specs = []
                current_pos = 0
                for field in cfg.get('fields', []):
                    name = field['name']
                    length = int(field['length'])
                    if field.get('position') is not None:
                        start = int(field['position']) - 1
                    else:
                        start = current_pos
                    end = start + length
                    field_specs.append((name, start, end))
                    current_pos = end
                return field_specs

            parser1_class = detector.get_parser_class(file1)
            if parser1_class == FixedWidthParser:
                if not (mapping_config and mapping_config.get('fields')):
                    click.echo(click.style(
                        "Error: fixed-width compare requires --mapping with fields/length metadata.",
                        fg='red'))
                    sys.exit(1)
                parser1 = FixedWidthParser(file1, _build_fixed_width_specs(mapping_config))
                df1 = parser1.parse()
            else:
                parser1 = parser1_class(file1)
                df1 = parser1.parse()

            parser2_class = detector.get_parser_class(file2)
            if parser2_class == FixedWidthParser:
                if not (mapping_config and mapping_config.get('fields')):
                    click.echo(click.style(
                        "Error: fixed-width compare requires --mapping with fields/length metadata.",
                        fg='red'))
                    sys.exit(1)
                parser2 = FixedWidthParser(file2, _build_fixed_width_specs(mapping_config))
                df2 = parser2.parse()
            else:
                parser2 = parser2_class(file2)
                df2 = parser2.parse()

            # For delimited files with header rows, retry parse with header-derived columns
            # when provided keys are missing from default numeric columns.
            if key_columns and any(k not in df1.columns for k in key_columns):
                try:
                    import pandas as pd
                    df1h = pd.read_csv(file1, sep='|', dtype=str, keep_default_na=False, header=0)
                    df2h = pd.read_csv(file2, sep='|', dtype=str, keep_default_na=False, header=0)
                    if all(k in df1h.columns for k in key_columns) and all(k in df2h.columns for k in key_columns):
                        df1, df2 = df1h, df2h
                except Exception:
                    pass

            # Compare
            comparator = FileComparator(df1, df2, key_columns)
            results = comparator.compare(detailed=detailed)
        
        # Display summary
        click.echo(f"\nComparison Summary:")
        click.echo(f"  Total rows (File 1): {results['total_rows_file1']}")
        click.echo(f"  Total rows (File 2): {results['total_rows_file2']}")
        click.echo(f"  Matching rows: {results['matching_rows']}")
        
        # Use count fields if lists are empty (chunked processing)
        only_in_file1 = results.get('only_in_file1_count', len(results.get('only_in_file1', [])))
        only_in_file2 = results.get('only_in_file2_count', len(results.get('only_in_file2', [])))
        
        click.echo(f"  Only in File 1: {only_in_file1}")
        click.echo(f"  Only in File 2: {only_in_file2}")
        click.echo(f"  Rows with differences: {results.get('rows_with_differences', len(results['differences']))}")
        
        # Evaluate thresholds
        if thresholds:
            loader = ConfigLoader()
            threshold_config = loader.load(thresholds)
            threshold_dict = ThresholdConfig.from_dict(threshold_config.get('thresholds', {}))
            evaluator = ThresholdEvaluator(threshold_dict)
        else:
            evaluator = ThresholdEvaluator()
        
        evaluation = evaluator.evaluate(results)
        
        click.echo("\nThreshold Evaluation:")
        if evaluation['passed']:
            click.echo(click.style('  ✓ PASS', fg='green'))
        elif evaluation['overall_result'].value == 'warning':
            click.echo(click.style('  ⚠ WARNING', fg='yellow'))
        else:
            click.echo(click.style('  ✗ FAIL', fg='red'))
        
        # Show detailed field statistics if available
        if detailed and results.get('field_statistics'):
            stats = results['field_statistics']
            click.echo(f"\nField-Level Statistics:")
            click.echo(f"  Fields with differences: {stats['fields_with_differences']}")
            if stats['most_different_field']:
                click.echo(f"  Most different field: {stats['most_different_field']}")
        
        # Generate report
        if output:
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            reporter = HTMLReporter()
            reporter.generate(results, output)
            click.echo(f"\nReport generated: {output}")
        
    except Exception as e:
        logger.error(f"Error comparing files: {e}")
        sys.exit(1)

