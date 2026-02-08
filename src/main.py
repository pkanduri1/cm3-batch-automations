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
        result = detect.detect(file)
        
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
@click.option('--format', '-t', help='File format (auto-detect if not specified)')
@click.option('--output', '-o', help='Output file (default: stdout)')
def parse(file, format, output):
    """Parse file and display contents."""
    logger = setup_logger('cm3-batch', log_to_file=False)
    
    try:
        from src.parsers.format_detector import FormatDetector
        from src.parsers.pipe_delimited_parser import PipeDelimitedParser
        from src.parsers.fixed_width_parser import FixedWidthParser
        
        # Auto-detect if format not specified
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
def validate(file, mapping):
    """Validate file format and content."""
    logger = setup_logger('cm3-batch', log_to_file=False)
    
    try:
        from src.parsers.format_detector import FormatDetector
        from src.parsers.validator import FileValidator
        
        # Get parser
        detector = FormatDetector()
        parser_class = detector.get_parser_class(file)
        parser = parser_class(file)
        
        # Validate
        validator = FileValidator(parser)
        result = validator.validate()
        
        if result['valid']:
            click.echo(click.style('✓ File is valid', fg='green'))
        else:
            click.echo(click.style('✗ File validation failed', fg='red'))
            for error in result['errors']:
                click.echo(click.style(f"  ERROR: {error}", fg='red'))
        
        if result['warnings']:
            click.echo(click.style('\nWarnings:', fg='yellow'))
            for warning in result['warnings']:
                click.echo(click.style(f"  {warning}", fg='yellow'))
        
    except Exception as e:
        logger.error(f"Error validating file: {e}")
        sys.exit(1)


@cli.command()
@click.option('--file1', '-f1', required=True, help='First file')
@click.option('--file2', '-f2', required=True, help='Second file')
@click.option('--keys', '-k', required=True, help='Key columns (comma-separated)')
@click.option('--output', '-o', help='Output HTML report file')
@click.option('--thresholds', '-t', help='Threshold configuration file')
@click.option('--detailed/--basic', default=True, help='Detailed field analysis')
def compare(file1, file2, keys, output, thresholds, detailed):
    """Compare two files and generate report."""
    logger = setup_logger('cm3-batch', log_to_file=False)
    
    try:
        from src.parsers.format_detector import FormatDetector
        from src.comparators.file_comparator import FileComparator
        from src.reporters.html_reporter import HTMLReporter
        from src.validators.threshold import ThresholdEvaluator, ThresholdConfig
        from src.config.loader import ConfigLoader
        
        # Parse both files
        detector = FormatDetector()
        
        parser1_class = detector.get_parser_class(file1)
        parser1 = parser1_class(file1)
        df1 = parser1.parse()
        
        parser2_class = detector.get_parser_class(file2)
        parser2 = parser2_class(file2)
        df2 = parser2.parse()
        
        # Compare
        key_columns = [k.strip() for k in keys.split(',')]
        comparator = FileComparator(df1, df2, key_columns)
        results = comparator.compare(detailed=detailed)
        
        # Display summary
        click.echo(f"\nComparison Summary:")
        click.echo(f"  Total rows (File 1): {results['total_rows_file1']}")
        click.echo(f"  Total rows (File 2): {results['total_rows_file2']}")
        click.echo(f"  Matching rows: {results['matching_rows']}")
        click.echo(f"  Only in File 1: {len(results['only_in_file1'])}")
        click.echo(f"  Only in File 2: {len(results['only_in_file2'])}")
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
def reconcile(mapping):
    """Reconcile mapping document with database schema."""
    logger = setup_logger('cm3-batch', log_to_file=False)
    
    try:
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
        
    except Exception as e:
        logger.error(f"Error reconciling mapping: {e}")
        sys.exit(1)


@cli.command()
@click.option('--table', '-t', required=True, help='Table name to extract')
@click.option('--output', '-o', required=True, help='Output file path')
@click.option('--limit', '-l', type=int, help='Limit number of rows')
@click.option('--delimiter', '-d', default='|', help='Output delimiter (default: |)')
def extract(table, output, limit, delimiter):
    """Extract data from Oracle database to file."""
    logger = setup_logger('cm3-batch', log_to_file=False)
    
    try:
        from src.database.connection import OracleConnection
        from src.database.extractor import DataExtractor
        
        conn = OracleConnection.from_env()
        extractor = DataExtractor(conn)
        
        click.echo(f"\nExtracting from table: {table}")
        
        if limit:
            df = extractor.extract_table(table, limit=limit)
            df.to_csv(output, sep=delimiter, index=False, header=False)
            click.echo(f"Extracted {len(df)} rows to {output}")
        else:
            stats = extractor.extract_to_file(table, output, delimiter=delimiter)
            click.echo(f"Extracted {stats['total_rows']} rows to {output}")
            click.echo(f"Chunks written: {stats['chunks_written']}")
        
        click.echo(click.style('✓ Extraction complete', fg='green'))
        
    except Exception as e:
        logger.error(f"Error extracting data: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
