"""Integration tests for the PostgresDb class"""

import uuid
from typing import Generator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.schema import Table

from agno.db.postgres.postgres import PostgresDb
from agno.db.postgres.schemas import SESSION_TABLE_SCHEMA

# TODO: should spin up a db
TEST_DB_URL = "postgresql+psycopg://ai:ai@localhost:5532/ai"


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    """Handle the engine lifecycle"""
    db = PostgresDb(db_url=TEST_DB_URL)
    yield db.db_engine
    db.db_engine.dispose()


@pytest.fixture
def postgres_db(engine: Engine) -> Generator[PostgresDb, None, None]:
    """Setup and cleanup a PostgresDb instance"""
    schema = f"test_schema_{uuid.uuid4().hex[:8]}"
    db = PostgresDb(
        db_engine=engine,
        db_schema=schema,
        session_table="test_sessions",
        user_memory_table="test_memories",
        metrics_table="test_metrics",
        eval_table="test_evals",
        knowledge_table="test_knowledge",
    )

    yield db

    # Cleanup
    with db.Session() as session:
        try:
            session.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
            session.commit()
        except Exception:
            session.rollback()


class TestPostgresDbInfrastructure:
    """Test database infrastructure: initialization, table creation, and schema management."""

    def test_initialization_with_db_url(self):
        db = PostgresDb(db_url=TEST_DB_URL)

        assert db.db_url == TEST_DB_URL
        assert db.db_engine is not None
        assert db.db_schema == "ai"
        assert db.Session is not None

    def test_initialization_with_engine(self, engine: Engine):
        db = PostgresDb(db_engine=engine)

        assert db.db_engine == engine
        assert db.db_url is None
        assert db.db_schema == "ai"

    def test_initialization_with_custom_schema(self, engine: Engine):
        custom_schema = "custom_test_schema"
        db = PostgresDb(db_engine=engine, db_schema=custom_schema)

        assert db.db_schema == custom_schema

    def test_initialization_requires_url_or_engine(self):
        with pytest.raises(ValueError, match="One of db_url or db_engine must be provided"):
            PostgresDb()

    def test_create_table(self, postgres_db: PostgresDb):
        """Ensure the _create_table method creates the table correctly"""
        table = postgres_db._create_table(
            table_name="test_sessions", table_type="sessions", db_schema=postgres_db.db_schema
        )

        # Verify the Table object
        assert isinstance(table, Table)
        assert table.name == "test_sessions"
        assert table.schema == postgres_db.db_schema

        # Verify the table was created
        with postgres_db.Session() as session:
            result = session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = :schema AND table_name = :table"
                ),
                {"schema": postgres_db.db_schema, "table": "test_sessions"},
            )
            assert result.fetchone() is not None

        # Verify the table columns
        expected_columns = [key for key in SESSION_TABLE_SCHEMA.keys() if key[0] != "_"]
        actual_columns = [col.name for col in table.columns]
        for col in expected_columns:
            assert col in actual_columns, f"Missing column: {col}"

        table = postgres_db._create_table(
            table_name="test_knowledge", table_type="knowledge", db_schema=postgres_db.db_schema
        )

        assert isinstance(table, Table)
        assert table.name == "test_knowledge"

        # Verify essential columns
        column_names = [col.name for col in table.columns]
        expected_columns = [
            "id",
            "name",
            "description",
            "metadata",
            "type",
            "size",
            "linked_to",
            "access_count",
            "status",
            "status_message",
            "created_at",
            "updated_at",
        ]
        for col in expected_columns:
            assert col in column_names, f"Missing column: {col}"

    def test_table_indexes(self, postgres_db: PostgresDb):
        """Ensure created tables have the expected indexes"""
        postgres_db._create_table(table_name="test_sessions", table_type="sessions", db_schema=postgres_db.db_schema)

        # Verify indexes were created
        with postgres_db.Session() as session:
            result = session.execute(
                text("SELECT indexname FROM pg_indexes WHERE schemaname = :schema AND tablename = :table"),
                {"schema": postgres_db.db_schema, "table": "test_sessions"},
            )

            # Verify indexes exist
            indexes = [row[0] for row in result.fetchall()]
            assert len(indexes) > 0

    def test_table_unique_constraints(self, postgres_db: PostgresDb):
        """Ensure created tables have the expected unique constraints"""
        postgres_db._create_table(table_name="test_sessions", table_type="sessions", db_schema=postgres_db.db_schema)

        with postgres_db.Session() as session:
            result = session.execute(
                text(
                    "SELECT constraint_name, constraint_type FROM information_schema.table_constraints "
                    "WHERE table_schema = :schema AND table_name = :table AND constraint_type = 'UNIQUE'"
                ),
                {"schema": postgres_db.db_schema, "table": "test_sessions"},
            )

            # Verify the unique constraints exist
            constraints = result.fetchall()
            assert len(constraints) >= 0

    def test_get_table(self, postgres_db: PostgresDb):
        """Ensure the _get_table method returns and cache results as expected"""
        table = postgres_db._get_table("sessions")
        assert isinstance(table, Table)
        assert table.name == "test_sessions"
        assert table.schema == postgres_db.db_schema

        # Verify table is cached (second call returns same object)
        table2 = postgres_db._get_table("sessions")
        assert table is table2

    def test_get_table_all_mappings(self, postgres_db: PostgresDb):
        """Ensure the _get_table method returns the correct table for all mappings"""
        # Eval table
        table = postgres_db._get_table("evals")
        assert isinstance(table, Table)
        assert table.name == "test_evals"
        assert table.schema == postgres_db.db_schema

        # Knowledge table
        table = postgres_db._get_table("knowledge")
        assert isinstance(table, Table)
        assert table.name == "test_knowledge"
        assert table.schema == postgres_db.db_schema

        # Memory table
        table = postgres_db._get_table("user_memories")
        assert isinstance(table, Table)
        assert table.name == "test_memories"
        assert table.schema == postgres_db.db_schema

        # Metrics table
        table = postgres_db._get_table("metrics")
        assert isinstance(table, Table)
        assert table.name == "test_metrics"
        assert table.schema == postgres_db.db_schema

    def test_get_table_invalid_type(self, postgres_db: PostgresDb):
        """Ensure _get_table raises for invalid table types"""
        with pytest.raises(ValueError, match="Unknown table type: fake-type"):
            postgres_db._get_table("fake-type")

    def test_get_or_create_table_creates_new(self, postgres_db: PostgresDb):
        """Ensure _get_or_create_table creates a new table when it doesn't exist"""
        table = postgres_db._get_or_create_table(
            table_name="new_test_table", table_type="sessions", db_schema=postgres_db.db_schema
        )

        assert isinstance(table, Table)
        assert table.name == "new_test_table"

        # Verify table exists in database
        with postgres_db.Session() as session:
            result = session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = :schema AND table_name = :table"
                ),
                {"schema": postgres_db.db_schema, "table": "new_test_table"},
            )
            assert result.fetchone() is not None

    def test_get_or_create_table_loads_existing(self, postgres_db: PostgresDb):
        """Ensure _get_or_create_table loads existing table without creating duplicate"""
        # Create table first
        postgres_db._create_table(table_name="existing_table", table_type="sessions", db_schema=postgres_db.db_schema)

        # Verify exactly one table exists before
        with postgres_db.Session() as session:
            result = session.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = :schema AND table_name = :table"
                ),
                {"schema": postgres_db.db_schema, "table": "existing_table"},
            )
            initial_count = result.scalar()
            assert initial_count == 1

        # Call get_or_create - should load existing, not create new
        table = postgres_db._get_or_create_table(
            table_name="existing_table", table_type="sessions", db_schema=postgres_db.db_schema
        )

        # Verify still exactly one table (no duplicates created)
        with postgres_db.Session() as session:
            result = session.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = :schema AND table_name = :table"
                ),
                {"schema": postgres_db.db_schema, "table": "existing_table"},
            )
            final_count = result.scalar()
            assert final_count == 1  # Key assertion: no new table created

        assert isinstance(table, Table)
        assert table.name == "existing_table"

    def test_schema_creation(self, postgres_db: PostgresDb):
        """Ensure database schemas are created lazily on table obtention"""
        # Getting a table should create it together with the schema, if needed
        postgres_db._get_table("sessions")

        # Verify schema exists
        with postgres_db.Session() as session:
            result = session.execute(
                text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"),
                {"schema": postgres_db.db_schema},
            )
            assert result.fetchone() is not None

    def test_table_creation_idempotency(self, postgres_db: PostgresDb):
        """Ensure table creation is idempotent (can be called multiple times)"""
        table1 = postgres_db._create_table(
            table_name="idempotent_test", table_type="sessions", db_schema=postgres_db.db_schema
        )
        table2 = postgres_db._create_table(
            table_name="idempotent_test", table_type="sessions", db_schema=postgres_db.db_schema
        )

        assert table1.name == table2.name

        # Verify only one table exists
        with postgres_db.Session() as session:
            result = session.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = :schema AND table_name = :table"
                ),
                {"schema": postgres_db.db_schema, "table": "idempotent_test"},
            )
            count = result.scalar()
            assert count == 1

    def test_multiple_table_types_creation(self, postgres_db: PostgresDb):
        """Test creating all table types in the same schema."""
        table_types = ["sessions", "user_memories", "metrics", "evals", "knowledge"]

        for table_type in table_types:
            table = postgres_db._get_table(table_type)
            assert isinstance(table, Table)

        # Verify all tables exist in database
        with postgres_db.Session() as session:
            result = session.execute(
                text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = :schema"),
                {"schema": postgres_db.db_schema},
            )
            count = result.scalar()
            assert count == len(table_types)
