"""Parser for pipe-delimited files."""

import pandas as pd
from typing import Optional, List
from .base_parser import BaseParser


class PipeDelimitedParser(BaseParser):
    """Parser for pipe-delimited (|) files."""

    def __init__(self, file_path: str, columns: Optional[List[str]] = None):
        """Initialize pipe-delimited parser.
        
        Args:
            file_path: Path to the pipe-delimited file
            columns: Optional list of column names
        """
        super().__init__(file_path)
        self.columns = columns

    def parse(self) -> pd.DataFrame:
        """Parse pipe-delimited file.
        
        Returns:
            DataFrame containing parsed data
        """
        try:
            df = pd.read_csv(
                self.file_path,
                sep="|",
                names=self.columns,
                dtype=str,
                keep_default_na=False,
            )
            return df
        except Exception as e:
            raise ValueError(f"Failed to parse pipe-delimited file: {e}")

    def validate_format(self) -> bool:
        """Validate pipe-delimited format.
        
        Returns:
            True if format is valid
        """
        try:
            with open(self.file_path, "r") as f:
                first_line = f.readline()
                return "|" in first_line
        except Exception:
            return False
