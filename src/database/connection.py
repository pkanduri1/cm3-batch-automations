"""Oracle database connection management."""

import oracledb
from typing import Optional
import os


class OracleConnection:
    """Manages Oracle database connections."""

    def __init__(
        self,
        username: str,
        password: str,
        dsn: str,
        encoding: str = "UTF-8",
    ):
        """Initialize Oracle connection parameters.
        
        Args:
            username: Database username
            password: Database password
            dsn: Data Source Name (TNS or Easy Connect)
            encoding: Character encoding (default: UTF-8)
        """
        self.username = username
        self.password = password
        self.dsn = dsn
        self.encoding = encoding
        self.connection: Optional[oracledb.Connection] = None

    def connect(self) -> oracledb.Connection:
        """Establish database connection.
        
        Returns:
            Oracle connection object
        """
        try:
            self.connection = oracledb.connect(
                user=self.username,
                password=self.password,
                dsn=self.dsn,
            )
            return self.connection
        except oracledb.Error as e:
            raise ConnectionError(f"Failed to connect to Oracle database: {e}")

    def disconnect(self) -> None:
        """Close database connection."""
        if self.connection:
            try:
                self.connection.close()
            except oracledb.Error as e:
                raise ConnectionError(f"Failed to close connection: {e}")
            finally:
                self.connection = None

    def __enter__(self):
        """Context manager entry."""
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    @staticmethod
    def from_env() -> "OracleConnection":
        """Create connection from environment variables.
        
        Returns:
            OracleConnection instance
        """
        return OracleConnection(
            username=os.getenv("ORACLE_USER", ""),
            password=os.getenv("ORACLE_PASSWORD", ""),
            dsn=os.getenv("ORACLE_DSN", ""),
        )

