"""Database interface placeholder for future Phase 2 storage."""


class Database:
    """Abstract access point for the application's database layer."""

    def get_transactions(self):
        """Return transactions once a database backend is configured."""
        raise NotImplementedError("Database backend has not been configured.")
