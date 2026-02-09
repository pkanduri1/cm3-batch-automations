"""Business rule validation engine."""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import pandas as pd
import re
from datetime import datetime


@dataclass
class RuleViolation:
    """Represents a single rule violation."""
    rule_id: str
    rule_name: str
    severity: str  # error, warning, info
    row_number: int
    field: str
    value: Any
    message: str
    expected: Optional[Any] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class RuleEngine:
    """Execute business rules against DataFrame."""
    
    def __init__(self, rules_config: Dict):
        """
        Initialize rule engine with configuration.
        
        Args:
            rules_config: Dictionary containing rules configuration
        """
        self.rules_config = rules_config
        self.rules = rules_config.get('rules', [])
        self.enabled_rules = [r for r in self.rules if r.get('enabled', True)]
        self.violations = []
        self.statistics = {
            'total_rules': len(self.rules),
            'enabled_rules': len(self.enabled_rules),
            'executed_rules': 0,
            'total_violations': 0,
            'violations_by_severity': {'error': 0, 'warning': 0, 'info': 0},
            'violations_by_rule': {}
        }
    
    def validate(self, df: pd.DataFrame) -> List[RuleViolation]:
        """
        Execute all enabled rules and return violations.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            List of RuleViolation objects
        """
        self.violations = []
        
        for rule in self.enabled_rules:
            try:
                rule_violations = self._execute_rule(rule, df)
                self.violations.extend(rule_violations)
                
                # Update statistics
                self.statistics['executed_rules'] += 1
                violation_count = len(rule_violations)
                self.statistics['violations_by_rule'][rule['id']] = violation_count
                
            except Exception as e:
                # Log error but continue with other rules
                print(f"Error executing rule {rule.get('id', 'unknown')}: {e}")
        
        # Update total statistics
        self.statistics['total_violations'] = len(self.violations)
        for violation in self.violations:
            severity = violation.severity
            self.statistics['violations_by_severity'][severity] = \
                self.statistics['violations_by_severity'].get(severity, 0) + 1
        
        return self.violations
    
    def _execute_rule(self, rule: Dict, df: pd.DataFrame) -> List[RuleViolation]:
        """
        Execute a single rule.
        
        Args:
            rule: Rule configuration dictionary
            df: DataFrame to validate
            
        Returns:
            List of violations for this rule
        """
        rule_type = rule.get('type')
        
        if rule_type == 'field_validation':
            return self._validate_field(rule, df)
        elif rule_type == 'cross_field':
            return self._validate_cross_field(rule, df)
        else:
            raise ValueError(f"Unknown rule type: {rule_type}")
    
    def _validate_field(self, rule: Dict, df: pd.DataFrame) -> List[RuleViolation]:
        """
        Validate individual field values.
        
        Args:
            rule: Rule configuration
            df: DataFrame to validate
            
        Returns:
            List of violations
        """
        from src.validators.field_validator import FieldValidator
        
        validator = FieldValidator()
        field = rule['field']
        operator = rule.get('operator')
        
        # Check if field exists
        if field not in df.columns:
            return []
        
        # Get violation mask based on operator
        if operator in ['>', '<', '>=', '<=', '==', '!=']:
            value = rule.get('value')
            mask = validator.validate_numeric(df, field, operator, value)
        elif operator in ['in', 'not_in']:
            values = rule.get('values', [])
            if isinstance(values, str):
                values = [v.strip() for v in values.split(',')]
            mask = validator.validate_list(df, field, operator, values)
        elif operator == 'regex':
            pattern = rule.get('pattern')
            mask = validator.validate_regex(df, field, pattern)
        elif operator == 'range':
            min_val = rule.get('min')
            max_val = rule.get('max')
            mask = validator.validate_range(df, field, min_val, max_val)
        elif operator == 'not_null':
            mask = validator.validate_not_null(df, field)
        elif operator == 'length':
            min_len = rule.get('min_length')
            max_len = rule.get('max_length')
            mask = validator.validate_length(df, field, min_len, max_len)
        else:
            raise ValueError(f"Unknown operator: {operator}")
        
        # Create violations for rows that failed validation
        violations = []
        for idx in df[mask].index:
            violations.append(RuleViolation(
                rule_id=rule['id'],
                rule_name=rule['name'],
                severity=rule.get('severity', 'error'),
                row_number=int(idx) + 1,  # 1-indexed for user display
                field=field,
                value=df.loc[idx, field],
                message=self._format_message(rule, df.loc[idx, field]),
                expected=rule.get('value') or rule.get('values') or rule.get('pattern')
            ))
        
        return violations
    
    def _validate_cross_field(self, rule: Dict, df: pd.DataFrame) -> List[RuleViolation]:
        """
        Validate relationships between fields.
        
        Args:
            rule: Rule configuration
            df: DataFrame to validate
            
        Returns:
            List of violations
        """
        from src.validators.cross_field_validator import CrossFieldValidator
        
        validator = CrossFieldValidator()
        operator = rule.get('operator')
        left_field = rule.get('left_field')
        right_field = rule.get('right_field')
        
        # Check if fields exist
        if left_field not in df.columns or right_field not in df.columns:
            return []
        
        # Get violation mask
        mask = validator.validate_field_comparison(df, left_field, operator, right_field)
        
        # Create violations
        violations = []
        for idx in df[mask].index:
            violations.append(RuleViolation(
                rule_id=rule['id'],
                rule_name=rule['name'],
                severity=rule.get('severity', 'error'),
                row_number=int(idx) + 1,
                field=f"{left_field}, {right_field}",
                value=f"{df.loc[idx, left_field]} vs {df.loc[idx, right_field]}",
                message=self._format_cross_field_message(rule, df.loc[idx, left_field], 
                                                         df.loc[idx, right_field]),
                expected=f"{left_field} {operator} {right_field}"
            ))
        
        return violations
    
    def _format_message(self, rule: Dict, value: Any) -> str:
        """Format violation message."""
        description = rule.get('description', rule.get('name'))
        return f"{description} (got: {value})"
    
    def _format_cross_field_message(self, rule: Dict, left_value: Any, 
                                    right_value: Any) -> str:
        """Format cross-field violation message."""
        description = rule.get('description', rule.get('name'))
        return f"{description} (got: {left_value} vs {right_value})"
    
    def get_statistics(self) -> Dict:
        """
        Get rule execution statistics.
        
        Returns:
            Dictionary with statistics
        """
        # Calculate compliance rate
        total_rows = self.statistics.get('total_rows', 0)
        if total_rows > 0:
            affected_rows = len(set(v.row_number for v in self.violations))
            compliance_rate = ((total_rows - affected_rows) / total_rows) * 100
        else:
            compliance_rate = 100.0
        
        return {
            **self.statistics,
            'compliance_rate': round(compliance_rate, 2)
        }
    
    def set_total_rows(self, total_rows: int):
        """Set total rows for compliance calculation."""
        self.statistics['total_rows'] = total_rows
