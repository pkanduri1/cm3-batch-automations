"""Parser for fixed-width files."""

import pandas as pd
from typing import List, Tuple
from .base_parser import BaseParser


class FixedWidthParser(BaseParser):
    """Parser for fixed-width format files."""

    def __init__(self, file_path: str, column_specs: List[Tuple[str, int, int]]):
        """Initialize fixed-width parser.
        
        Args:
            file_path: Path to the fixed-width file
            column_specs: List of tuples (column_name, start_pos, end_pos)
        """
        super().__init__(file_path)
        self.column_specs = column_specs

    def parse(self) -> pd.DataFrame:
        """Parse fixed-width file.
        
        Returns:
            DataFrame containing parsed data
        """
        try:
            colspecs = [(start, end) for _, start, end in self.column_specs]
            names = [name for name, _, _ in self.column_specs]
            
            df = pd.read_fwf(
                self.file_path,
                colspecs=colspecs,
                names=names,
                dtype=str,
            )
            return df
        except Exception as e:
            raise ValueError(f"Failed to parse fixed-width file: {e}")

    def validate_format(self) -> bool:
        """Validate fixed-width format.
        
        Returns:
            True if format is valid
        """
        try:
            with open(self.file_path, "r") as f:
                lines = [f.readline() for _ in range(min(10, sum(1 for _ in f)))]
                if not lines:
                    return False
                line_lengths = [len(line.rstrip("\n")) for line in lines]
                return len(set(line_lengths)) <= 2
        except Exception:
            return False
