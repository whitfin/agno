from typing import Any, Optional

from agno.storage_v2.base import DBManager
from agno.utils.log import log_debug, log_info, log_warning, logger

try:
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.engine import Engine, create_engine
    from sqlalchemy.inspection import inspect
    from sqlalchemy.orm import scoped_session, sessionmaker
    from sqlalchemy.schema import Column, MetaData, Table
    from sqlalchemy.sql.expression import select, text
    from sqlalchemy.types import JSON, BigInteger, DateTime, String, Text
except ImportError:
    raise ImportError("`sqlalchemy` not installed. Please install it using `pip install sqlalchemy`")


class PostgresDB(DBManager):
    def __init__(
        self,
        db_engine: Optional[Engine] = None,
        db_schema: Optional[str] = None,
        db_url: Optional[str] = None,
        agent_sessions_table_name: Optional[str] = None,
        team_sessions_table_name: Optional[str] = None,
        workflow_sessions_table_name: Optional[str] = None,
        memory_table_name: Optional[str] = None,
        learnings_table_name: Optional[str] = None,
        eval_runs_table_name: Optional[str] = None,
    ):
        """
        Interface for interacting with a PostgreSQL database.

        The following order is used to determine the database connection:
            1. Use the db_engine if provided
            2. Use the db_url
            3. Raise an error if neither is provided

        Args:
            db_url (Optional[str]): The database URL to connect to.
            db_engine (Optional[Engine]): The SQLAlchemy database engine to use.
            agent_sessions_table_name (Optional[str]): Name of the table to store Agent sessions.
            team_sessions_table_name (Optional[str]): Name of the table to store Team sessions.
            workflow_sessions_table_name (Optional[str]): Name of the table to store Workflow sessions.
            memory_table_name (Optional[str]): Name of the table to store memory.
            learnings_table_name (Optional[str]): Name of the table to store learnings.
            eval_runs_table_name (Optional[str]): Name of the table to store eval runs.

        Raises:
            ValueError: If neither db_url nor db_engine is provided.
            ValueError: If none of the tables are provided.
        """
        super().__init__(
            agent_sessions_table_name=agent_sessions_table_name,
            team_sessions_table_name=team_sessions_table_name,
            workflow_sessions_table_name=workflow_sessions_table_name,
            memory_table_name=memory_table_name,
            learnings_table_name=learnings_table_name,
            eval_runs_table_name=eval_runs_table_name,
        )

        _engine: Optional[Engine] = db_engine
        if _engine is None and db_url is not None:
            _engine = create_engine(db_url)
        if _engine is None:
            raise ValueError("One of db_url or db_engine must be provided")

        self.db_url: Optional[str] = db_url
        self.db_engine: Engine = _engine
        self.db_schema: str = db_schema if db_schema is not None else "public"

        # Initialize metadata for table management
        self.metadata = MetaData()
        # Database session
        self.Session: scoped_session = scoped_session(sessionmaker(bind=self.db_engine))

        # Setup tables
        self.agent_sessions_table: Optional[Table] = (
            self.get_or_create_table(
                table_name=self.agent_sessions_table_name, table_type="agent_sessions", schema=self.db_schema
            )
            if self.agent_sessions_table_name is not None
            else None
        )
        self.team_sessions_table: Optional[Table] = (
            self.get_or_create_table(
                table_name=self.team_sessions_table_name, table_type="team_sessions", schema=self.db_schema
            )
            if self.team_sessions_table_name is not None
            else None
        )
        self.workflow_sessions_table: Optional[Table] = (
            self.get_or_create_table(
                table_name=self.workflow_sessions_table_name, table_type="workflow_sessions", schema=self.db_schema
            )
            if self.workflow_sessions_table_name is not None
            else None
        )
        self.memory_table: Optional[Table] = (
            self.get_or_create_table(table_name=self.memory_table_name, table_type="memory", schema=self.db_schema)
            if self.memory_table_name is not None
            else None
        )
        self.learnings_table: Optional[Table] = (
            self.get_or_create_table(
                table_name=self.learnings_table_name, table_type="learnings", schema=self.db_schema
            )
            if self.learnings_table_name is not None
            else None
        )
        self.eval_runs_table: Optional[Table] = (
            self.get_or_create_table(
                table_name=self.eval_runs_table_name, table_type="eval_runs", schema=self.db_schema
            )
            if self.eval_runs_table_name is not None
            else None
        )

        log_debug("Created PostgresDB")

    # TODO: the schemas should live together with the app layer classes
    def _get_table_schema_definition(self, table_name: str) -> dict[str, Any]:
        """
        Get the expected schema definition for a given table name.

        Returns:
            Dict[str, Any]: Dictionary containing column definitions for the table
        """
        schemas = {
            # Agent sessions table schema
            "agent_sessions": {
                "session_id": {"type": String, "nullable": False},
                "agent_id": {"type": String, "nullable": False},
                "user_id": {"type": String, "nullable": True},
                "team_session_id": {"type": String, "nullable": True},
                "memory": {"type": JSON, "nullable": True},
                "session_data": {"type": JSON, "nullable": True},
                "extra_data": {"type": JSON, "nullable": True},
                "created_at": {"type": BigInteger, "nullable": False},
                "updated_at": {"type": BigInteger, "nullable": True},
                "agent_data": {"type": JSON, "nullable": True},
                "chat_history": {"type": JSON, "nullable": True},
                "runs": {"type": JSON, "nullable": True},
                "summary": {"type": JSON, "nullable": True},
            },
            "team_sessions": {},
            "workflow_sessions": {},
            "memory": {},
            "learnings": {},
            "eval_runs": {},
        }

        for schema_key, schema_def in schemas.items():
            if schema_key in table_name.lower() or table_name.lower().endswith(schema_key):
                return schema_def

        raise ValueError(f"Unknown table type for table name: {table_name}")

    # TODO: do we need to carry these Table objects?
    def get_or_create_table(self, table_name: str, table_type: str, schema: str) -> Table:
        """
        Check if the table exists and is valid, else create it.

        Returns:
            Table: SQLAlchemy Table object representing the schema.
        """

        if not self.table_exists(table_name=table_name, schema=schema):
            return self.create_table(table_name=table_name, table_type=table_type, schema=schema)

        if not self.is_valid_table(table_name=table_name, table_type=table_type, schema=schema):
            raise ValueError(f"Table {schema}.{table_name} has an invalid schema")

        try:
            table = Table(table_name, self.metadata, schema=schema)
            log_debug(f"Loaded existing table {schema}.{table_name}")
            return table

        except Exception as e:
            logger.error(f"Error loading existing table {schema}.{table_name}: {e}")
            raise

    # TODO: should also check column types, indexes
    def is_valid_table(self, table_name: str, table_type: str, schema: str) -> bool:
        """
        Check if the existing table has the expected column names.

        Args:
            table_name (str): Name of the table to validate
            schema (str): Database schema name

        Returns:
            bool: True if table has all expected columns, False otherwise
        """
        try:
            expected_table_schema = self._get_table_schema_definition(table_type)
            expected_columns = set(expected_table_schema.keys())

            # Get existing columns
            inspector = inspect(self.db_engine)
            existing_columns_info = inspector.get_columns(table_name, schema=schema)
            existing_columns = set(col["name"] for col in existing_columns_info)

            # Check if all expected columns exist
            missing_columns = expected_columns - existing_columns
            if missing_columns:
                log_warning(f"Missing columns {missing_columns} in table {schema}.{table_name}")
                return False

            log_debug(f"Table {schema}.{table_name} has all expected columns")
            return True
        except Exception as e:
            logger.error(f"Error validating table schema for {schema}.{table_name}: {e}")
            return False

    def table_exists(self, table_name: str, schema: str) -> bool:
        """
        Check if the given table exists in the given schema.

        Returns:
            bool: True if the table exists, False otherwise.
        """
        try:
            with self.Session() as sess:
                exists_query = text(
                    "SELECT 1 FROM information_schema.tables WHERE table_schema = :schema AND table_name = :table"
                )
                exists = sess.execute(exists_query, {"schema": schema, "table": table_name}).scalar() is not None
                if not exists:
                    log_debug(f"Table {schema}.{table_name} {'exists' if exists else 'does not exist'}")

                return exists

        except Exception as e:
            logger.error(f"Error checking if table exists: {e}")
            return False

    def _create_schema(self, schema: str) -> None:
        """Create the database schema if it doesn't exist."""
        try:
            with self.Session() as sess, sess.begin():
                log_debug(f"Creating schema if not exists: {schema}")
                sess.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema};"))
        except Exception as e:
            logger.warning(f"Could not create schema {schema}: {e}")

    def create_table(self, table_name: str, table_type: str, schema: str) -> Table:
        """
        Create a table with the appropriate schema based on the table name.

        Args:
            table_name (str): Name of the table to create
            schema (str): Database schema name

        Returns:
            Table: SQLAlchemy Table object
        """
        try:
            table_schema = self._get_table_schema_definition(table_type)

            columns, indexes = [], []
            for col_name, col_config in table_schema.items():
                column_args = [col_name, col_config["type"]()]
                column_kwargs = {}

                if col_config.get("primary_key", False):
                    column_kwargs["primary_key"] = True
                if "nullable" in col_config:
                    column_kwargs["nullable"] = col_config["nullable"]
                if col_config.get("index", False):
                    indexes.append(col_name)

                columns.append(Column(*column_args, **column_kwargs))

            # Create the table object
            table_metadata = MetaData(schema=schema)
            table = Table(table_name, table_metadata, *columns, schema=schema)

            # Add indexes to the table definition
            for idx_col in indexes:
                from sqlalchemy import Index

                idx_name = f"idx_{table_name}_{idx_col}"
                table.append_constraint(Index(idx_name, idx_col))

            # TODO: do we want this?
            self._create_schema(schema)

            # Create table
            table_without_indexes = Table(
                table_name,
                MetaData(schema=schema),
                *[c.copy() for c in table.columns],
                schema=schema,
            )
            table_without_indexes.create(self.db_engine, checkfirst=True)

            # Create indexes
            for idx in table.indexes:
                try:
                    idx_name = idx.name
                    log_debug(f"Creating index: {idx_name}")

                    # Check if index already exists
                    with self.Session() as sess:
                        exists_query = text(
                            "SELECT 1 FROM pg_indexes WHERE schemaname = :schema AND indexname = :index_name"
                        )
                        exists = (
                            sess.execute(exists_query, {"schema": schema, "index_name": idx_name}).scalar() is not None
                        )

                    if not exists:
                        idx.create(self.db_engine)
                    else:
                        log_debug(f"Index {idx_name} already exists in {schema}.{table_name}, skipping creation")

                except Exception as e:
                    logger.warning(f"Error creating index {idx.name}: {e}")

            log_info(f"Successfully created table {schema}.{table_name}")
            return table

        except Exception as e:
            logger.error(f"Could not create table {schema}.{table_name}: {e}")
            raise
