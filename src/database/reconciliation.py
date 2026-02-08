"""Database schema reconciliation with mapping documents."""

from typing import Dict, List, Any, Optional
import oracledb
from ..config.mapping_parser import MappingDocument
from .connection import OracleConnection
from .query_executor import QueryExecutor
from ..utils.logger import get_logger


class SchemaReconciler:
    """Reconciles mapping documents with actual database schema."""

    def __init__(self, connection: OracleConnection):
        """Initialize schema reconciler.
        
        Args:
            connection: OracleConnection instance
        """
        self.connection = connection
        self.executor = QueryExecutor(connection)
        self.logger = get_logger(__name__)

    def reconcile_mapping(self, mapping: MappingDocument) -> Dict[str, Any]:
        """Reconcile mapping document with database schema.
        
        Args:
            mapping: MappingDocument to reconcile
            
        Returns:
            Reconciliation results with errors and warnings
        """
        errors = []
        warnings = []
        
        # Get target table name
        if mapping.target['type'] != 'database':
            return {
                'valid': True,
                'errors': [],
                'warnings': ['Target is not a database, skipping reconciliation'],
            }
        
        table_name = mapping.target.get('table_name')
        if not table_name:
            errors.append("No target table name specified")
            return {'valid': False, 'errors': errors, 'warnings': warnings}
        
        # Check if table exists
        if not self._table_exists(table_name):
            errors.append(f"Target table does not exist: {table_name}")
            return {'valid': False, 'errors': errors, 'warnings': warnings}
        
        # Get table columns
        db_columns = self._get_table_columns(table_name)
        db_column_info = self._get_column_details(table_name)
        
        # Check each mapping
        for col_mapping in mapping.mappings:
            target_col = col_mapping.target_column
            
            # Check if column exists
            if target_col not in db_columns:
                if col_mapping.required:
                    errors.append(f"Required target column not found: {target_col}")
                else:
                    warnings.append(f"Optional target column not found: {target_col}")
                continue
            
            # Get column info
            col_info = db_column_info.get(target_col, {})
            
            # Check data type compatibility
            db_type = col_info.get('data_type', '')
            mapping_type = col_mapping.data_type
            
            if not self._types_compatible(mapping_type, db_type):
                warnings.append(
                    f"Type mismatch for {target_col}: "
                    f"mapping expects '{mapping_type}', database has '{db_type}'"
                )
            
            # Check nullable constraint
            nullable = col_info.get('nullable', 'Y')
            if col_mapping.required and nullable == 'Y':
                warnings.append(
                    f"Column {target_col} is required in mapping but nullable in database"
                )
            
            # Check length constraints
            if mapping_type == 'string':
                db_length = col_info.get('data_length')
                if db_length:
                    # Check validation rules for max_length
                    for rule in col_mapping.validation_rules:
                        if rule['type'] == 'max_length':
                            max_len = rule['parameters'].get('length', 0)
                            if max_len > db_length:
                                warnings.append(
                                    f"Column {target_col}: validation max_length ({max_len}) "
                                    f"exceeds database length ({db_length})"
                                )
        
        # Check for unmapped required database columns
        mapped_columns = {m.target_column for m in mapping.mappings}
        required_db_columns = self._get_required_columns(table_name)
        
        unmapped_required = required_db_columns - mapped_columns
        if unmapped_required:
            warnings.append(
                f"Required database columns not in mapping: {sorted(unmapped_required)}"
            )
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'table_name': table_name,
            'mapped_columns': len(mapping.mappings),
            'database_columns': len(db_columns),
            'unmapped_required': list(unmapped_required),
        }

    def _table_exists(self, table_name: str) -> bool:
        """Check if table exists.
        
        Args:
            table_name: Name of the table
            
        Returns:
            True if table exists
        """
        query = """
            SELECT COUNT(*) as cnt
            FROM user_tables
            WHERE table_name = :table_name
        """
        
        try:
            df = self.executor.execute_query(query, {'table_name': table_name.upper()})
            return df['CNT'].iloc[0] > 0
        except Exception as e:
            self.logger.error(f"Error checking table existence: {e}")
            return False

    def _get_table_columns(self, table_name: str) -> List[str]:
        """Get list of column names for table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column names
        """
        return self.executor.fetch_table_columns(table_name)

    def _get_column_details(self, table_name: str) -> Dict[str, Dict[str, Any]]:
        """Get detailed column information.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary mapping column names to their details
        """
        query = """
            SELECT 
                column_name,
                data_type,
                data_length,
                data_precision,
                data_scale,
                nullable
            FROM user_tab_columns
            WHERE table_name = :table_name
            ORDER BY column_id
        """
        
        try:
            df = self.executor.execute_query(query, {'table_name': table_name.upper()})
            
            result = {}
            for _, row in df.iterrows():
                result[row['COLUMN_NAME']] = {
                    'data_type': row['DATA_TYPE'],
                    'data_length': row['DATA_LENGTH'],
                    'data_precision': row['DATA_PRECISION'],
                    'data_scale': row['DATA_SCALE'],
                    'nullable': row['NULLABLE'],
                }
            
            return result
        except Exception as e:
            self.logger.error(f"Error getting column details: {e}")
            return {}

    def _get_required_columns(self, table_name: str) -> set:
        """Get set of required (NOT NULL) columns.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Set of required column names
        """
        query = """
            SELECT column_name
            FROM user_tab_columns
            WHERE table_name = :table_name
            AND nullable = 'N'
        """
        
        try:
            df = self.executor.execute_query(query, {'table_name': table_name.upper()})
            return set(df['COLUMN_NAME'].tolist())
        except Exception as e:
            self.logger.error(f"Error getting required columns: {e}")
            return set()

    def _types_compatible(self, mapping_type: str, db_type: str) -> bool:
        """Check if mapping type is compatible with database type.
        
        Args:
            mapping_type: Type from mapping document
            db_type: Type from database
            
        Returns:
            True if types are compatible
        """
        # Define compatibility matrix
        compatibility = {
            'string': ['VARCHAR2', 'CHAR', 'NVARCHAR2', 'NCHAR', 'CLOB', 'NCLOB'],
            'number': ['NUMBER', 'INTEGER', 'FLOAT', 'BINARY_FLOAT', 'BINARY_DOUBLE'],
            'date': ['DATE', 'TIMESTAMP', 'TIMESTAMP WITH TIME ZONE', 'TIMESTAMP WITH LOCAL TIME ZONE'],
            'boolean': ['NUMBER', 'CHAR', 'VARCHAR2'],  # Oracle doesn't have native boolean
        }
        
        compatible_types = compatibility.get(mapping_type.lower(), [])
        return db_type.upper() in compatible_types

    def generate_reconciliation_report(self, mapping: MappingDocument) -> str:
        """Generate human-readable reconciliation report.
        
        Args:
            mapping: MappingDocument to reconcile
            
        Returns:
            Formatted report string
        """
        result = self.reconcile_mapping(mapping)
        
        report = []
        report.append("=" * 70)
        report.append("MAPPING RECONCILIATION REPORT")
        report.append("=" * 70)
        report.append(f"Mapping: {mapping.mapping_name} (v{mapping.version})")
        report.append(f"Target Table: {result.get('table_name', 'N/A')}")
        report.append(f"Status: {'VALID' if result['valid'] else 'INVALID'}")
        report.append("")
        
        report.append(f"Mapped Columns: {result.get('mapped_columns', 0)}")
        report.append(f"Database Columns: {result.get('database_columns', 0)}")
        report.append("")
        
        if result['errors']:
            report.append("ERRORS:")
            for error in result['errors']:
                report.append(f"  ✗ {error}")
            report.append("")
        
        if result['warnings']:
            report.append("WARNINGS:")
            for warning in result['warnings']:
                report.append(f"  ⚠ {warning}")
            report.append("")
        
        if not result['errors'] and not result['warnings']:
            report.append("✓ No issues found")
            report.append("")
        
        report.append("=" * 70)
        
        return "\n".join(report)


class MappingValidator:
    """Validates mapping documents against database schema."""

    def __init__(self, connection: OracleConnection):
        """Initialize mapping validator.
        
        Args:
            connection: OracleConnection instance
        """
        self.reconciler = SchemaReconciler(connection)
        self.logger = get_logger(__name__)

    def validate_all_mappings(self, mappings: List[MappingDocument]) -> Dict[str, Any]:
        """Validate multiple mapping documents.
        
        Args:
            mappings: List of MappingDocument instances
            
        Returns:
            Validation results for all mappings
        """
        results = {}
        total_valid = 0
        total_invalid = 0
        
        for mapping in mappings:
            result = self.reconciler.reconcile_mapping(mapping)
            results[mapping.mapping_name] = result
            
            if result['valid']:
                total_valid += 1
            else:
                total_invalid += 1
        
        return {
            'total_mappings': len(mappings),
            'valid': total_valid,
            'invalid': total_invalid,
            'results': results,
        }

    def validate_mapping_file(self, mapping_file_path: str) -> Dict[str, Any]:
        """Validate a mapping file against database.
        
        Args:
            mapping_file_path: Path to mapping JSON file
            
        Returns:
            Validation results
        """
        from ..config.loader import ConfigLoader
        from ..config.mapping_parser import MappingParser
        
        # Load and parse mapping
        loader = ConfigLoader()
        mapping_dict = loader.load_mapping(mapping_file_path)
        
        parser = MappingParser()
        mapping = parser.parse(mapping_dict)
        
        # Reconcile with database
        return self.reconciler.reconcile_mapping(mapping)
