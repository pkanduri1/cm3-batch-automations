"""Field-level validation for business rules."""

import pandas as pd
import re
from typing import Any, List


class FieldValidator:
    """Validate individual field values against rules."""
    
    def validate_numeric(self, df: pd.DataFrame, field: str, 
                        operator: str, value: Any) -> pd.Series:
        """
        Validate numeric field against value.
        
        Args:
            df: DataFrame
            field: Field name
            operator: Comparison operator (>, <, >=, <=, ==, !=)
            value: Value to compare against
            
        Returns:
            Boolean mask where True indicates violation
        """
        series = pd.to_numeric(df[field], errors='coerce')
        
        if operator == '>':
            return ~(series > value)
        elif operator == '<':
            return ~(series < value)
        elif operator == '>=':
            return ~(series >= value)
        elif operator == '<=':
            return ~(series <= value)
        elif operator == '==':
            return ~(series == value)
        elif operator == '!=':
            return ~(series != value)
        else:
            raise ValueError(f"Unknown numeric operator: {operator}")
    
    def validate_list(self, df: pd.DataFrame, field: str, 
                     operator: str, values: List[Any]) -> pd.Series:
        """
        Validate field value is in/not in list.
        
        Args:
            df: DataFrame
            field: Field name
            operator: 'in' or 'not_in'
            values: List of valid values
            
        Returns:
            Boolean mask where True indicates violation
        """
        series = df[field].astype(str).str.strip()
        
        if operator == 'in':
            return ~series.isin(values)
        elif operator == 'not_in':
            return series.isin(values)
        else:
            raise ValueError(f"Unknown list operator: {operator}")
    
    def validate_regex(self, df: pd.DataFrame, field: str, 
                      pattern: str) -> pd.Series:
        """
        Validate field matches regex pattern.
        
        Args:
            df: DataFrame
            field: Field name
            pattern: Regex pattern
            
        Returns:
            Boolean mask where True indicates violation
        """
        series = df[field].astype(str).str.strip()
        
        # Return True for values that DON'T match pattern (violations)
        return ~series.str.match(pattern, na=False)
    
    def validate_range(self, df: pd.DataFrame, field: str, 
                      min_val: Any, max_val: Any) -> pd.Series:
        """
        Validate field is within range.
        
        Args:
            df: DataFrame
            field: Field name
            min_val: Minimum value (inclusive)
            max_val: Maximum value (inclusive)
            
        Returns:
            Boolean mask where True indicates violation
        """
        series = pd.to_numeric(df[field], errors='coerce')
        
        # Violation if value is outside range or NaN
        return ~((series >= min_val) & (series <= max_val))
    
    def validate_not_null(self, df: pd.DataFrame, field: str) -> pd.Series:
        """
        Validate field is not null/empty.
        
        Args:
            df: DataFrame
            field: Field name
            
        Returns:
            Boolean mask where True indicates violation
        """
        series = df[field]
        
        # Check for null, empty string, or whitespace-only
        is_null = series.isna()
        is_empty = series.astype(str).str.strip() == ''
        
        return is_null | is_empty
    
    def validate_length(self, df: pd.DataFrame, field: str, 
                       min_length: int = None, max_length: int = None) -> pd.Series:
        """
        Validate string length.
        
        Args:
            df: DataFrame
            field: Field name
            min_length: Minimum length (optional)
            max_length: Maximum length (optional)
            
        Returns:
            Boolean mask where True indicates violation
        """
        series = df[field].astype(str)
        lengths = series.str.len()
        
        violations = pd.Series([False] * len(df), index=df.index)
        
        if min_length is not None:
            violations |= lengths < min_length
        
        if max_length is not None:
            violations |= lengths > max_length
        
        return violations
