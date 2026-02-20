"""Main entry point for CM3 Batch Automations."""

import sys
import os
import click
from src.utils.logger import setup_logger


@click.group()
@click.version_option(version='0.1.0')
def cli():
    """CM3 Batch Automations - File parsing, validation, and comparison tool."""
    pass


@cli.command()
@click.option('--file', '-f', required=True, help='File to detect format')
def detect(file):
    """Detect file format automatically."""
    logger = setup_logger('cm3-batch', log_to_file=False)
    
    try:
        from src.parsers.format_detector import FormatDetector
        
        detector = FormatDetector()
        result = detector.detect(file)
        
        logger.info(f"File: {file}")
        logger.info(f"Format: {result['format'].value}")
        logger.info(f"Confidence: {result['confidence']:.2%}")
        if 'delimiter' in result:
            logger.info(f"Delimiter: {result['delimiter']}")
        logger.info(f"Sample lines: {result['line_count']}")
        
        click.echo(f"\nDetected format: {result['format'].value}")
        click.echo(f"Confidence: {result['confidence']:.2%}")
        
    except Exception as e:
        logger.error(f"Error detecting format: {e}")
        sys.exit(1)


@cli.command()
@click.option('--file', '-f', required=True, help='File to parse')
@click.option('--mapping', '-m', help='Mapping configuration file')
@click.option('--format', '-t', help='File format (auto-detect if not specified)')
@click.option('--output', '-o', help='Output file (default: stdout)')
@click.option('--use-chunked', is_flag=True, help='Use chunked processing for large files')
@click.option('--chunk-size', default=100000, help='Chunk size for large files (default: 100000)')
def parse(file, mapping, format, output, use_chunked, chunk_size):
    """Parse file and display contents."""
    logger = setup_logger('cm3-batch', log_to_file=False)

    try:
        from src.parsers.format_detector import FormatDetector
        from src.parsers.pipe_delimited_parser import PipeDelimitedParser
        from src.parsers.fixed_width_parser import FixedWidthParser
        from src.parsers.chunked_parser import ChunkedFileParser, ChunkedFixedWidthParser
        import json

        mapping_config = None
        field_specs = []

        # If mapping provided, build field specs (fixed-width)
        if mapping:
            with open(mapping, 'r') as f:
                mapping_config = json.load(f)

            current_pos = 0
            for field in mapping_config.get('fields', []):
                field_name = field['name']
                field_length = field['length']
                field_specs.append((field_name, current_pos, current_pos + field_length))
                current_pos += field_length

        # Chunked path
        if use_chunked:
            if mapping and field_specs:
                parser = ChunkedFixedWidthParser(file, field_specs, chunk_size=chunk_size)
            else:
                delimiter = '|'
                if format == 'pipe':
                    delimiter = '|'
                elif format in ('csv', 'comma'):
                    delimiter = ','
                parser = ChunkedFileParser(file, delimiter=delimiter, chunk_size=chunk_size)

            total_rows = 0
            preview_df = None

            if output:
                first_chunk = True
                for chunk in parser.parse_chunks():
                    if preview_df is None:
                        preview_df = chunk.head(10)
                    chunk.to_csv(output, index=False, mode='w' if first_chunk else 'a', header=first_chunk)
                    first_chunk = False
                    total_rows += len(chunk)
                click.echo(f"Output written to: {output}")
                click.echo(f"Total rows: {total_rows}")
            else:
                for chunk in parser.parse_chunks():
                    if preview_df is None:
                        preview_df = chunk.head(10)
                    total_rows += len(chunk)

                if preview_df is not None:
                    click.echo(preview_df.to_string())
                click.echo(f"\nTotal rows: {total_rows}")

            return

        # Non-chunked path (existing behavior)
        if mapping and field_specs:
            parser = FixedWidthParser(file, field_specs)
        else:
            if not format:
                detector = FormatDetector()
                parser_class = detector.get_parser_class(file)
                parser = parser_class(file)
            else:
                if format == 'pipe':
                    parser = PipeDelimitedParser(file)
                elif format == 'fixed':
                    parser = FixedWidthParser(file, [])
                else:
                    click.echo(f"Unknown format: {format}")
                    sys.exit(1)

        df = parser.parse()
        logger.info(f"Parsed {len(df)} rows, {len(df.columns)} columns")

        if output:
            df.to_csv(output, index=False)
            click.echo(f"Output written to: {output}")
        else:
            click.echo(df.head(10).to_string())
            click.echo(f"\nTotal rows: {len(df)}")

    except Exception as e:
        logger.error(f"Error parsing file: {e}")
        sys.exit(1)


@cli.command()
@click.option('--file', '-f', required=True, help='File to validate')
@click.option('--mapping', '-m', help='Mapping file for schema validation')
@click.option('--rules', '-r', type=click.Path(exists=True), help='Business rules configuration file (JSON)')
@click.option('--output', '-o', help='Output HTML report file')
@click.option('--detailed/--basic', default=True, help='Include detailed field analysis')
@click.option('--use-chunked', is_flag=True, help='Use chunked processing for large files')
@click.option('--chunk-size', default=100000, help='Chunk size for large files (default: 100000)')
@click.option('--progress/--no-progress', default=True, help='Show progress bar')
def validate(file, mapping, rules, output, detailed, use_chunked, chunk_size, progress):
    """Validate file format and content."""
    logger = setup_logger('cm3-batch', log_to_file=False)

    try:
        from src.parsers.format_detector import FormatDetector
        from src.parsers.enhanced_validator import EnhancedFileValidator
        from src.parsers.fixed_width_parser import FixedWidthParser
        from src.parsers.chunked_validator import ChunkedFileValidator
        from src.parsers.chunked_parser import ChunkedFixedWidthParser
        from src.reporters.validation_reporter import ValidationReporter
        from src.reporting.result_adapter_chunked import adapt_chunked_validation_result
        import json

        mapping_config = None
        if mapping:
            with open(mapping, 'r') as f:
                mapping_config = json.load(f)
            mapping_config['file_path'] = mapping

        # Chunked path
        if use_chunked:
            detector = FormatDetector()
            parser_class = detector.get_parser_class(file)

            chunk_parser = None
            delimiter = '|'
            if parser_class == FixedWidthParser and mapping_config and 'fields' in mapping_config:
                field_specs = []
                current_pos = 0
                for field in mapping_config.get('fields', []):
                    field_name = field['name']
                    field_length = int(field['length'])

                    # Support both styles:
                    # 1) explicit 1-based `position`
                    # 2) implicit cumulative positions from `length`
                    if field.get('position') is not None:
                        start = int(field['position']) - 1
                    else:
                        start = current_pos

                    end = start + field_length
                    field_specs.append((field_name, start, end))
                    current_pos = end

                chunk_parser = ChunkedFixedWidthParser(file, field_specs, chunk_size=chunk_size)
            elif parser_class == FixedWidthParser and mapping_config and 'mappings' in mapping_config:
                # Fallback for non-universal mappings (no fixed-width position metadata)
                click.echo(click.style('Chunked fixed-width validation requires mapping with fields/position/length metadata.', fg='red'))
                sys.exit(1)
            else:
                delimiter = '|'

            chunked_validator = ChunkedFileValidator(
                file_path=file,
                delimiter=delimiter,
                chunk_size=chunk_size,
                parser=chunk_parser,
                rules_config_path=rules,
            )

            if mapping_config:
                if 'fields' in mapping_config:
                    expected_columns = [f['name'] for f in mapping_config['fields']]
                    required_columns = [f['name'] for f in mapping_config['fields'] if f.get('required', False)]
                elif 'mappings' in mapping_config:
                    expected_columns = [m['source_column'] for m in mapping_config['mappings']]
                    required_columns = [m['source_column'] for m in mapping_config['mappings'] if m.get('required', False)]
                else:
                    expected_columns = []
                    required_columns = []

                if expected_columns:
                    result = chunked_validator.validate_with_schema(
                        expected_columns=expected_columns,
                        required_columns=required_columns if required_columns else expected_columns,
                        show_progress=progress,
                    )
                else:
                    result = chunked_validator.validate(show_progress=progress)
            else:
                result = chunked_validator.validate(show_progress=progress)

            if result['valid']:
                click.echo(click.style('✓ File is valid (chunked)', fg='green'))
            else:
                click.echo(click.style('✗ File validation failed (chunked)', fg='red'))

            click.echo(f"\nTotal Rows: {result.get('total_rows', 0):,}")

            if result.get('errors'):
                click.echo(click.style(f"\nErrors ({len(result['errors'])}):", fg='red'))
                for error in result['errors'][:5]:
                    msg = error.get('message', str(error)) if isinstance(error, dict) else str(error)
                    click.echo(click.style(f"  • {msg}", fg='red'))
                if len(result['errors']) > 5:
                    click.echo(click.style(f"  ... and {len(result['errors']) - 5} more", fg='red'))

            if result.get('warnings'):
                click.echo(click.style(f"\nWarnings ({len(result['warnings'])}):", fg='yellow'))
                for warning in result['warnings'][:5]:
                    msg = warning.get('message', str(warning)) if isinstance(warning, dict) else str(warning)
                    click.echo(click.style(f"  • {msg}", fg='yellow'))
                if len(result['warnings']) > 5:
                    click.echo(click.style(f"  ... and {len(result['warnings']) - 5} more", fg='yellow'))

            if output:
                if output.lower().endswith('.json'):
                    with open(output, 'w') as f:
                        json.dump(result, f, indent=2)
                    click.echo(f"\n✓ Chunked validation JSON report generated: {output}")
                elif output.lower().endswith('.html') or output.lower().endswith('.htm'):
                    reporter = ValidationReporter()
                    adapted = adapt_chunked_validation_result(result, file_path=file, mapping=mapping)
                    reporter.generate(adapted, output)
                    click.echo(f"\n✓ Chunked validation HTML report generated: {output}")
                else:
                    click.echo(click.style("\nUnsupported output type for chunked validation. Use .json or .html", fg='yellow'))

            if not result['valid']:
                sys.exit(1)
            return

        # Non-chunked path (existing behavior)
        detector = FormatDetector()
        parser_class = detector.get_parser_class(file)

        if mapping_config and parser_class == FixedWidthParser:
            field_specs = []
            current_pos = 0
            for field in mapping_config.get('fields', []):
                field_name = field['name']
                field_length = field['length']
                field_specs.append((field_name, current_pos, current_pos + field_length))
                current_pos += field_length

            parser = FixedWidthParser(file, field_specs)
        else:
            parser = parser_class(file)

        validator = EnhancedFileValidator(parser, mapping_config, rules)
        result = validator.validate(detailed=detailed)

        if result['valid']:
            click.echo(click.style('✓ File is valid', fg='green'))
        else:
            click.echo(click.style('✗ File validation failed', fg='red'))

        quality_score = result.get('quality_metrics', {}).get('quality_score', 0)
        click.echo(f"\nData Quality Score: {quality_score}%")

        metrics = result.get('quality_metrics', {})
        if metrics:
            click.echo(f"  Total Rows: {metrics.get('total_rows', 0):,}")
            click.echo(f"  Total Columns: {metrics.get('total_columns', 0):,}")
            click.echo(f"  Completeness: {metrics.get('completeness_pct', 0)}%")
            click.echo(f"  Uniqueness: {metrics.get('uniqueness_pct', 0)}%")

        if result['errors']:
            click.echo(click.style(f"\nErrors ({len(result['errors'])}):", fg='red'))
            for error in result['errors'][:5]:
                click.echo(click.style(f"  • {error.get('message', '')}", fg='red'))
            if len(result['errors']) > 5:
                click.echo(click.style(f"  ... and {len(result['errors']) - 5} more", fg='red'))

        if result['warnings']:
            click.echo(click.style(f"\nWarnings ({len(result['warnings'])}):", fg='yellow'))
            for warning in result['warnings'][:5]:
                click.echo(click.style(f"  • {warning.get('message', '')}", fg='yellow'))
            if len(result['warnings']) > 5:
                click.echo(click.style(f"  ... and {len(result['warnings']) - 5} more", fg='yellow'))

        if output:
            reporter = ValidationReporter()
            reporter.generate(result, output)
            click.echo(f"\n✓ Validation report generated: {output}")

        # Align exit behavior with chunked validation path and CI expectations.
        if not result['valid']:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error validating file: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)



@cli.command('convert-rules')
@click.option('--template', '-t', required=True, type=click.Path(exists=True),
              help='Excel or CSV template file')
@click.option('--output', '-o', required=True, type=click.Path(),
              help='Output JSON rules file')
@click.option('--sheet', '-s', help='Sheet name (for Excel files)')
def convert_rules(template, output, sheet):
    """Convert Excel/CSV template to JSON rules configuration."""
    logger = setup_logger('cm3-batch', log_to_file=False)
    
    try:
        from src.config.rules_template_converter import RulesTemplateConverter
        
        converter = RulesTemplateConverter()
        
        # Convert based on file type
        if template.endswith('.xlsx') or template.endswith('.xls'):
            logger.info(f"Converting Excel template: {template}")
            rules_config = converter.from_excel(template, sheet)
        elif template.endswith('.csv'):
            logger.info(f"Converting CSV template: {template}")
            rules_config = converter.from_csv(template)
        else:
            logger.error("Template must be .xlsx, .xls, or .csv file")
            sys.exit(1)
        
        # Save to JSON
        converter.save(output)
        
        # Display summary
        total_rules = len(rules_config['rules'])
        enabled_rules = len([r for r in rules_config['rules'] if r.get('enabled', True)])
        
        click.echo(f"\n✓ Rules configuration saved to: {output}")
        click.echo(f"  Total rules: {total_rules}")
        click.echo(f"  Enabled rules: {enabled_rules}")
        click.echo(f"  Disabled rules: {total_rules - enabled_rules}")
        
        # Show rule types breakdown
        rule_types = {}
        for rule in rules_config['rules']:
            rule_type = rule.get('type', 'unknown')
            rule_types[rule_type] = rule_types.get(rule_type, 0) + 1
        
        click.echo("\n  Rule types:")
        for rule_type, count in rule_types.items():
            click.echo(f"    - {rule_type}: {count}")
        
    except Exception as e:
        logger.error(f"Error converting template: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option('--file1', '-f1', required=True, help='First file')
@click.option('--file2', '-f2', required=True, help='Second file')
@click.option('--keys', '-k', help='Key columns (comma-separated). If not provided, compares row-by-row.')
@click.option('--mapping', '-m', help='Mapping file (recommended for fixed-width comparison).')
@click.option('--output', '-o', help='Output HTML report file')
@click.option('--thresholds', '-t', help='Threshold configuration file')
@click.option('--detailed/--basic', default=True, help='Detailed field analysis')
@click.option('--chunk-size', default=100000, help='Chunk size for large files (default: 100000)')
@click.option('--progress/--no-progress', default=True, help='Show progress bar')
@click.option('--use-chunked', is_flag=True, help='Use chunked processing for large files')
def compare(file1, file2, keys, mapping, output, thresholds, detailed, chunk_size, progress, use_chunked):
    """Compare two files and generate report."""
    logger = setup_logger('cm3-batch', log_to_file=False)
    
    try:
        from src.parsers.format_detector import FormatDetector
        from src.comparators.file_comparator import FileComparator
        from src.comparators.chunked_comparator import ChunkedFileComparator
        from src.reporters.html_reporter import HTMLReporter
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
            else:
                parser2 = parser2_class(file2)
            df2 = parser2.parse()

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
            reporter = HTMLReporter()
            reporter.generate(results, output)
            click.echo(f"\nReport generated: {output}")
        
    except Exception as e:
        logger.error(f"Error comparing files: {e}")
        sys.exit(1)


@cli.command()
def info():
    """Display system information and check dependencies."""
    logger = setup_logger('cm3-batch', log_to_file=False)
    
    click.echo("CM3 Batch Automations v0.1.0")
    click.echo(f"Python version: {sys.version}")
    click.echo(f"Working directory: {os.getcwd()}")
    
    # Check Oracle
    oracle_home = os.getenv("ORACLE_HOME")
    if oracle_home:
        click.echo(f"Oracle Home: {oracle_home}")
    else:
        click.echo(click.style("Warning: ORACLE_HOME not set", fg='yellow'))
    
    try:
        import oracledb
        click.echo(f"oracledb version: {oracledb.__version__}")
        click.echo(click.style("✓ Oracle connectivity available (thin mode)", fg='green'))
    except ImportError:
        click.echo(click.style("✗ oracledb not available", fg='red'))
    except Exception as e:
        click.echo(click.style(f"✗ Oracle client error: {e}", fg='red'))


@cli.command()
@click.option('--mapping', '-m', required=True, help='Mapping file to validate')
@click.option('--output', '-o', help='Write reconciliation report to file (.json for machine-readable output)')
@click.option('--fail-on-warnings', is_flag=True, help='Return non-zero exit code if warnings are found')
def reconcile(mapping, output, fail_on_warnings):
    """Reconcile mapping document with database schema."""
    logger = setup_logger('cm3-batch', log_to_file=False)

    try:
        import json
        from src.database.connection import OracleConnection
        from src.database.reconciliation import SchemaReconciler
        from src.config.loader import ConfigLoader
        from src.config.mapping_parser import MappingParser

        # Load mapping
        loader = ConfigLoader()
        mapping_dict = loader.load_mapping(mapping)

        parser = MappingParser()
        mapping_doc = parser.parse(mapping_dict)

        # Reconcile with database
        conn = OracleConnection.from_env()
        reconciler = SchemaReconciler(conn)

        click.echo(f"\nReconciling mapping: {mapping_doc.mapping_name}")
        click.echo(f"Target table: {mapping_doc.target.get('table_name', 'N/A')}")

        result = reconciler.reconcile_mapping(mapping_doc)

        if result['valid']:
            click.echo(click.style('\n✓ Mapping is valid', fg='green'))
        else:
            click.echo(click.style('\n✗ Mapping validation failed', fg='red'))
            for error in result['errors']:
                click.echo(click.style(f"  ERROR: {error}", fg='red'))

        if result['warnings']:
            click.echo(click.style('\nWarnings:', fg='yellow'))
            for warning in result['warnings']:
                click.echo(click.style(f"  {warning}", fg='yellow'))

        click.echo(f"\nMapped columns: {result.get('mapped_columns', 0)}")
        click.echo(f"Database columns: {result.get('database_columns', 0)}")

        if output:
            if output.lower().endswith('.json'):
                with open(output, 'w') as f:
                    json.dump(result, f, indent=2)
            else:
                report = reconciler.generate_reconciliation_report(mapping_doc)
                with open(output, 'w') as f:
                    f.write(report)
            click.echo(f"Report written to: {output}")

        if (not result['valid']) or (fail_on_warnings and result['warnings']):
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error reconciling mapping: {e}")
        sys.exit(1)


@cli.command('reconcile-all')
@click.option('--mappings-dir', '-d', default='config/mappings', type=click.Path(exists=True, file_okay=False),
              help='Directory containing mapping files (default: config/mappings)')
@click.option('--pattern', default='*.json', help='Glob pattern for mapping files (default: *.json)')
@click.option('--output', '-o', help='Write aggregate reconciliation report (.json recommended)')
@click.option('--baseline', '-b', type=click.Path(exists=True),
              help='Baseline reconcile-all JSON report to compare drift against')
@click.option('--fail-on-warnings', is_flag=True, help='Return non-zero exit code if warnings are found')
@click.option('--fail-on-drift', is_flag=True, help='Return non-zero exit code if new errors/warnings appear vs baseline')
def reconcile_all(mappings_dir, pattern, output, baseline, fail_on_warnings, fail_on_drift):
    """Reconcile all mapping documents in a directory against database schema."""
    logger = setup_logger('cm3-batch', log_to_file=False)

    try:
        import json
        from pathlib import Path
        from src.database.connection import OracleConnection
        from src.database.reconciliation import SchemaReconciler
        from src.config.loader import ConfigLoader
        from src.config.mapping_parser import MappingParser

        loader = ConfigLoader()
        parser = MappingParser()
        conn = OracleConnection.from_env()
        reconciler = SchemaReconciler(conn)

        mapping_files = sorted(Path(mappings_dir).glob(pattern))
        if not mapping_files:
            click.echo(click.style(f"No mapping files found in {mappings_dir} matching '{pattern}'", fg='yellow'))
            return

        results = []
        total_errors = 0
        total_warnings = 0
        invalid_mappings = 0

        for mapping_file in mapping_files:
            click.echo(f"\nReconciling: {mapping_file}")
            try:
                mapping_dict = loader.load_mapping(str(mapping_file))
                mapping_doc = parser.parse(mapping_dict)
                result = reconciler.reconcile_mapping(mapping_doc)

                errors = result.get('error_count', len(result.get('errors', [])))
                warnings = result.get('warning_count', len(result.get('warnings', [])))
                total_errors += errors
                total_warnings += warnings

                if not result.get('valid', False):
                    invalid_mappings += 1
                    click.echo(click.style(f"  ✗ INVALID ({errors} errors, {warnings} warnings)", fg='red'))
                else:
                    status_color = 'yellow' if warnings else 'green'
                    status_text = f"  ✓ VALID ({warnings} warnings)" if warnings else "  ✓ VALID"
                    click.echo(click.style(status_text, fg=status_color))

                results.append({
                    'mapping_file': str(mapping_file),
                    'mapping_name': mapping_doc.mapping_name,
                    **result,
                })

            except Exception as file_error:
                invalid_mappings += 1
                total_errors += 1
                click.echo(click.style(f"  ✗ FAILED to process: {file_error}", fg='red'))
                results.append({
                    'mapping_file': str(mapping_file),
                    'valid': False,
                    'errors': [f"Failed to process mapping: {file_error}"],
                    'warnings': [],
                    'error_count': 1,
                    'warning_count': 0,
                })

        summary = {
            'total_mappings': len(mapping_files),
            'valid_mappings': len(mapping_files) - invalid_mappings,
            'invalid_mappings': invalid_mappings,
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'results': results,
        }

        click.echo("\n" + "=" * 60)
        click.echo("RECONCILE-ALL SUMMARY")
        click.echo("=" * 60)
        click.echo(f"Total mappings:  {summary['total_mappings']}")
        click.echo(f"Valid mappings:  {summary['valid_mappings']}")
        click.echo(f"Invalid mappings:{summary['invalid_mappings']}")
        click.echo(f"Total errors:    {summary['total_errors']}")
        click.echo(f"Total warnings:  {summary['total_warnings']}")

        drift = None
        if baseline:
            with open(baseline, 'r') as f:
                baseline_report = json.load(f)

            baseline_results = {
                r.get('mapping_file'): r
                for r in baseline_report.get('results', [])
                if r.get('mapping_file')
            }
            current_results = {
                r.get('mapping_file'): r
                for r in results
                if r.get('mapping_file')
            }

            baseline_files = set(baseline_results.keys())
            current_files = set(current_results.keys())

            added_files = sorted(current_files - baseline_files)
            removed_files = sorted(baseline_files - current_files)

            changed = []
            new_errors = 0
            new_warnings = 0

            for mf in sorted(current_files & baseline_files):
                old = baseline_results[mf]
                new = current_results[mf]
                old_e = old.get('error_count', len(old.get('errors', [])))
                old_w = old.get('warning_count', len(old.get('warnings', [])))
                new_e = new.get('error_count', len(new.get('errors', [])))
                new_w = new.get('warning_count', len(new.get('warnings', [])))

                delta_e = new_e - old_e
                delta_w = new_w - old_w
                if delta_e != 0 or delta_w != 0:
                    changed.append({
                        'mapping_file': mf,
                        'old_errors': old_e,
                        'new_errors': new_e,
                        'delta_errors': delta_e,
                        'old_warnings': old_w,
                        'new_warnings': new_w,
                        'delta_warnings': delta_w,
                    })
                    if delta_e > 0:
                        new_errors += delta_e
                    if delta_w > 0:
                        new_warnings += delta_w

            drift = {
                'baseline': baseline,
                'added_files': added_files,
                'removed_files': removed_files,
                'changed': changed,
                'new_errors': new_errors,
                'new_warnings': new_warnings,
            }

            click.echo("\nDRIFT SUMMARY")
            click.echo("-" * 60)
            click.echo(f"Added mappings:   {len(added_files)}")
            click.echo(f"Removed mappings: {len(removed_files)}")
            click.echo(f"Changed mappings: {len(changed)}")
            click.echo(f"New errors:       {new_errors}")
            click.echo(f"New warnings:     {new_warnings}")

        if drift is not None:
            summary['drift'] = drift

        if output:
            if output.lower().endswith('.json'):
                with open(output, 'w') as f:
                    json.dump(summary, f, indent=2)
            else:
                with open(output, 'w') as f:
                    f.write(json.dumps(summary, indent=2))
            click.echo(f"\nAggregate report written to: {output}")

        has_drift_regression = bool(drift and (drift.get('new_errors', 0) > 0 or drift.get('new_warnings', 0) > 0))

        if (
            summary['invalid_mappings'] > 0
            or (fail_on_warnings and summary['total_warnings'] > 0)
            or (fail_on_drift and has_drift_regression)
        ):
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error reconciling mappings directory: {e}")
        sys.exit(1)


@cli.command()
@click.option('--table', '-t', help='Table name to extract')
@click.option('--query', '-q', help='SQL query to execute')
@click.option('--sql-file', '-s', type=click.Path(exists=True), help='Path to SQL file')
@click.option('--output', '-o', required=True, help='Output file path')
@click.option('--limit', '-l', type=int, help='Limit number of rows (only for --table)')
@click.option('--delimiter', '-d', default='|', help='Output delimiter (default: |)')
def extract(table, query, sql_file, output, limit, delimiter):
    """Extract data from Oracle database to file.
    
    Supports three modes:
    1. Table extraction: --table TABLENAME
    2. Direct query: --query "SELECT ..."
    3. SQL file: --sql-file path/to/query.sql
    """
    logger = setup_logger('cm3-batch', log_to_file=False)
    
    # Validate input options
    options_provided = sum([bool(table), bool(query), bool(sql_file)])
    if options_provided == 0:
        click.echo(click.style('Error: Must provide one of --table, --query, or --sql-file', fg='red'))
        sys.exit(1)
    elif options_provided > 1:
        click.echo(click.style('Error: Only one of --table, --query, or --sql-file can be specified', fg='red'))
        sys.exit(1)
    
    try:
        from src.database.connection import OracleConnection
        from src.database.extractor import DataExtractor
        
        conn = OracleConnection.from_env()
        extractor = DataExtractor(conn)
        
        # Determine extraction mode
        if sql_file:
            # Read SQL from file
            with open(sql_file, 'r') as f:
                sql_query = f.read().strip()
            click.echo(f"\nExecuting SQL from file: {sql_file}")
            stats = extractor.extract_to_file(output_file=output, query=sql_query, delimiter=delimiter)
            click.echo(f"Extracted {stats['total_rows']} rows to {output}")
            click.echo(f"Chunks written: {stats['chunks_written']}")
            
        elif query:
            # Use provided SQL query
            click.echo(f"\nExecuting custom query")
            stats = extractor.extract_to_file(output_file=output, query=query, delimiter=delimiter)
            click.echo(f"Extracted {stats['total_rows']} rows to {output}")
            click.echo(f"Chunks written: {stats['chunks_written']}")
            
        else:
            # Table extraction
            click.echo(f"\nExtracting from table: {table}")
            
            if limit:
                df = extractor.extract_table(table, limit=limit)
                df.to_csv(output, sep=delimiter, index=False, header=False)
                click.echo(f"Extracted {len(df)} rows to {output}")
            else:
                stats = extractor.extract_to_file(table_name=table, output_file=output, delimiter=delimiter)
                click.echo(f"Extracted {stats['total_rows']} rows to {output}")
                click.echo(f"Chunks written: {stats['chunks_written']}")
        
        click.echo(click.style('✓ Extraction complete', fg='green'))
        
    except Exception as e:
        logger.error(f"Error extracting data: {e}")
        sys.exit(1)


@cli.command('generate-oracle-expected')
@click.option('--manifest', 'manifest_path', required=True, type=click.Path(exists=True),
              help='Oracle expected-generation manifest JSON')
@click.option('--dry-run/--run', default=True,
              help='Dry-run by default. Use --run to execute Oracle extraction jobs')
@click.option('--output', '-o', help='Optional output JSON summary file')
def generate_oracle_expected(manifest_path, dry_run, output):
    """Generate expected target files from Oracle transformation SQL (cm3int)."""
    logger = setup_logger('cm3-batch', log_to_file=False)
    try:
        import json
        from src.pipeline.oracle_expected_generator import load_oracle_manifest, generate_expected_from_oracle

        manifest = load_oracle_manifest(manifest_path)
        summary = generate_expected_from_oracle(manifest, dry_run=dry_run)

        click.echo(f"Status: {summary.get('status')}")
        for j in summary.get('jobs', []):
            click.echo(f"- {j.get('name')}: {j.get('status')}")

        if output:
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
            click.echo(f"\n✓ Oracle expected summary written: {output}")

        if summary.get('status') == 'failed':
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error generating oracle expected files: {e}")
        sys.exit(1)


@cli.command('run-pipeline')
@click.option('--config', 'config_path', required=True, type=click.Path(exists=True),
              help='Source-system pipeline profile JSON')
@click.option('--dry-run/--run', default=True,
              help='Dry-run by default. Use --run to execute configured stage commands')
@click.option('--output', '-o', help='Optional output JSON summary file')
@click.option('--summary-md', help='Optional output Markdown summary file')
def run_pipeline(config_path, dry_run, output, summary_md):
    """Run source-system orchestration profile (scaffold)."""
    logger = setup_logger('cm3-batch', log_to_file=False)
    try:
        from src.pipeline.runner import PipelineRunner
        from src.pipeline.run_summary_reporter import write_pipeline_summary_json, write_pipeline_summary_markdown

        runner = PipelineRunner(config_path)
        summary = runner.run(dry_run=dry_run)

        click.echo(f"Source: {summary.get('source_system')}")
        click.echo(f"Status: {summary.get('status')}")
        for step in summary.get('steps', []):
            click.echo(f"- {step.get('name')}: {step.get('status')} ({step.get('message', '')})")

        if output:
            write_pipeline_summary_json(summary, output)
            click.echo(f"\n✓ Pipeline summary written: {output}")

        if summary_md:
            write_pipeline_summary_markdown(summary, summary_md)
            click.echo(f"✓ Pipeline Markdown summary written: {summary_md}")

        if summary.get('status') == 'failed':
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error running pipeline profile: {e}")
        sys.exit(1)


@cli.command('gx-checkpoint1')
@click.option('--targets', '-t', 'targets_csv', type=click.Path(exists=True), required=True,
              help='CSV file listing data targets (BA-friendly).')
@click.option('--expectations', '-e', 'expectations_csv', type=click.Path(exists=True), required=True,
              help='CSV file listing expectations (BA-friendly).')
@click.option('--output', '-o', 'output_json', type=click.Path(),
              help='Optional path to write run summary JSON.')
@click.option('--csv-output', type=click.Path(),
              help='Optional path to write flattened expectation results CSV.')
@click.option('--html-output', type=click.Path(),
              help='Optional path to write human-readable HTML summary.')
@click.option('--data-docs-dir', type=click.Path(),
              help='Optional Great Expectations data docs directory.')
def gx_checkpoint1(targets_csv, expectations_csv, output_json, csv_output, html_output, data_docs_dir):
    """Run Great Expectations Checkpoint 1 (schema/null/uniqueness/allowed values/range/row-count)."""
    logger = setup_logger('cm3-batch', log_to_file=False)

    try:
        from src.quality.gx_checkpoint1 import run_checkpoint_1

        summary = run_checkpoint_1(
            targets_csv=targets_csv,
            expectations_csv=expectations_csv,
            output_json=output_json,
            csv_output=csv_output,
            html_output=html_output,
            data_docs_dir=data_docs_dir,
        )

        if summary.get('success'):
            click.echo(click.style('✓ Great Expectations Checkpoint 1 passed', fg='green'))
        else:
            click.echo(click.style('✗ Great Expectations Checkpoint 1 failed', fg='red'))
            sys.exit(1)

        click.echo(f"Targets run: {summary.get('targets_run', 0)}")
        if output_json:
            click.echo(f"JSON summary written to: {output_json}")
        if csv_output:
            click.echo(f"CSV summary written to: {csv_output}")
        if html_output:
            click.echo(f"HTML summary written to: {html_output}")

    except Exception as e:
        logger.error(f"Error running Great Expectations Checkpoint 1: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
