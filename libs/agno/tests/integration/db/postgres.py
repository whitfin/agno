"""Integration tests for the PostgresDb class"""

import time
import uuid
from datetime import datetime
from typing import Generator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.schema import Table

from agno.db.base import SessionType
from agno.db.postgres.postgres import PostgresDb
from agno.db.postgres.schemas import SESSION_TABLE_SCHEMA
from agno.db.schemas.memory import UserMemory
from agno.run.base import RunStatus
from agno.run.response import RunResponse
from agno.run.team import TeamRunResponse
from agno.session.agent import AgentSession
from agno.session.summary import SessionSummary
from agno.session.team import TeamSession

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
        session_table="test_agno_sessions",
        user_memory_table="test_agno_memories",
        metrics_table="test_agno_metrics",
        eval_table="test_agno_evals",
        knowledge_table="test_agno_knowledge",
    )

    yield db

    # Cleanup
    with db.Session() as session:
        try:
            session.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
            session.commit()
        except Exception:
            session.rollback()


@pytest.fixture(scope="class")
def test_db(engine: Engine) -> Generator[PostgresDb, None, None]:
    """PostgresDb instance to be used across all tests"""
    schema = f"session_test_schema_{uuid.uuid4().hex[:8]}"
    db = PostgresDb(
        db_engine=engine,
        db_schema=schema,
        session_table="test_agno_sessions",
        user_memory_table="test_agno_memories",
        metrics_table="test_agno_metrics",
        eval_table="test_agno_evals",
        knowledge_table="test_agno_knowledge",
    )

    # Force table creation by accessing the sessions table
    db._get_table("sessions")

    yield db

    # Cleanup
    with db.Session() as session:
        try:
            session.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
            session.commit()
        except Exception:
            session.rollback()


class TestPostgresDbInfrastructure:
    """Tests for the infrastructure-related methods of PostgresDb"""

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

    def test_create_table(self, test_db: PostgresDb):
        """Ensure the _create_table method creates the table correctly"""
        table = test_db._create_table(
            table_name="test_agno_sessions", table_type="sessions", db_schema=test_db.db_schema
        )

        # Verify the Table object
        assert isinstance(table, Table)
        assert table.name == "test_agno_sessions"
        assert table.schema == test_db.db_schema

        # Verify the table was created
        with test_db.Session() as session:
            result = session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = :schema AND table_name = :table"
                ),
                {"schema": test_db.db_schema, "table": "test_agno_sessions"},
            )
            assert result.fetchone() is not None

        # Verify the table columns
        expected_columns = [key for key in SESSION_TABLE_SCHEMA.keys() if key[0] != "_"]
        actual_columns = [col.name for col in table.columns]
        for col in expected_columns:
            assert col in actual_columns, f"Missing column: {col}"

        table = test_db._create_table(
            table_name="test_agno_knowledge", table_type="knowledge", db_schema=test_db.db_schema
        )

        assert isinstance(table, Table)
        assert table.name == "test_agno_knowledge"

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

    def test_table_indexes(self, test_db: PostgresDb):
        """Ensure created tables have the expected indexes"""
        test_db._create_table(table_name="test_agno_sessions", table_type="sessions", db_schema=test_db.db_schema)

        # Verify indexes were created
        with test_db.Session() as session:
            result = session.execute(
                text("SELECT indexname FROM pg_indexes WHERE schemaname = :schema AND tablename = :table"),
                {"schema": test_db.db_schema, "table": "test_agno_sessions"},
            )

            # Verify indexes exist
            indexes = [row[0] for row in result.fetchall()]
            assert len(indexes) > 0

    def test_table_unique_constraints(self, test_db: PostgresDb):
        """Ensure created tables have the expected unique constraints"""
        # Create a fresh sessions table specifically for testing constraints
        table_name = "test_agno_constraint_sessions"
        test_db._create_table(table_name=table_name, table_type="sessions", db_schema=test_db.db_schema)

        with test_db.Session() as session:
            result = session.execute(
                text(
                    "SELECT constraint_name, constraint_type FROM information_schema.table_constraints "
                    "WHERE table_schema = :schema AND table_name = :table AND constraint_type = 'UNIQUE'"
                ),
                {"schema": test_db.db_schema, "table": table_name},
            )

            # Verify the specific session_id unique constraint exists
            constraints = result.fetchall()
            constraint_names = [row[0] for row in constraints]
            expected_constraint_name = f"{table_name}_uq_session_id"
            assert expected_constraint_name in constraint_names, (
                f"Expected constraint {expected_constraint_name} not found. Found: {constraint_names}"
            )

    def test_get_table(self, test_db: PostgresDb):
        """Ensure the _get_table method returns and cache results as expected"""
        table = test_db._get_table("sessions")
        assert isinstance(table, Table)
        assert table.name == "test_agno_sessions"
        assert table.schema == test_db.db_schema

        # Verify table is cached (second call returns same object)
        table2 = test_db._get_table("sessions")
        assert table is table2

    def test_get_table_all_mappings(self, test_db: PostgresDb):
        """Ensure the _get_table method returns the correct table for all mappings"""
        # Eval table
        table = test_db._get_table("evals")
        assert isinstance(table, Table)
        assert table.name == "test_agno_evals"
        assert table.schema == test_db.db_schema

        # Knowledge table
        table = test_db._get_table("knowledge")
        assert isinstance(table, Table)
        assert table.name == "test_agno_knowledge"
        assert table.schema == test_db.db_schema

        # Memory table
        table = test_db._get_table("user_memories")
        assert isinstance(table, Table)
        assert table.name == "test_agno_memories"
        assert table.schema == test_db.db_schema

        # Metrics table
        table = test_db._get_table("metrics")
        assert isinstance(table, Table)
        assert table.name == "test_agno_metrics"
        assert table.schema == test_db.db_schema

    def test_get_table_invalid_type(self, test_db: PostgresDb):
        """Ensure _get_table raises for invalid table types"""
        with pytest.raises(ValueError, match="Unknown table type: fake-type"):
            test_db._get_table("fake-type")

    def test_get_or_create_table_creates_new(self, test_db: PostgresDb):
        """Ensure _get_or_create_table creates a new table when it doesn't exist"""
        table = test_db._get_or_create_table(
            table_name="test_agno_new_table", table_type="sessions", db_schema=test_db.db_schema
        )

        assert isinstance(table, Table)
        assert table.name == "test_agno_new_table"

        # Verify table exists in database
        with test_db.Session() as session:
            result = session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = :schema AND table_name = :table"
                ),
                {"schema": test_db.db_schema, "table": "test_agno_new_table"},
            )
            assert result.fetchone() is not None

    def test_get_or_create_table_loads_existing(self, test_db: PostgresDb):
        """Ensure _get_or_create_table loads existing table without creating duplicate"""
        # Create table first
        test_db._create_table(table_name="test_agno_existing_table", table_type="sessions", db_schema=test_db.db_schema)

        # Verify exactly one table exists before
        with test_db.Session() as session:
            result = session.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = :schema AND table_name = :table"
                ),
                {"schema": test_db.db_schema, "table": "test_agno_existing_table"},
            )
            initial_count = result.scalar()
            assert initial_count == 1

        # Call get_or_create - should load existing, not create new
        table = test_db._get_or_create_table(
            table_name="test_agno_existing_table", table_type="sessions", db_schema=test_db.db_schema
        )

        # Verify still exactly one table (no duplicates created)
        with test_db.Session() as session:
            result = session.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = :schema AND table_name = :table"
                ),
                {"schema": test_db.db_schema, "table": "test_agno_existing_table"},
            )
            final_count = result.scalar()
            assert final_count == 1  # Key assertion: no new table created

        assert isinstance(table, Table)
        assert table.name == "test_agno_existing_table"

    def test_schema_creation(self, test_db: PostgresDb):
        """Ensure database schemas are created lazily on table obtention"""
        # Getting a table should create it together with the schema, if needed
        test_db._get_table("sessions")

        # Verify schema exists
        with test_db.Session() as session:
            result = session.execute(
                text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"),
                {"schema": test_db.db_schema},
            )
            assert result.fetchone() is not None

    def test_table_creation_idempotency(self, test_db: PostgresDb):
        """Ensure table creation is idempotent (can be called multiple times)"""
        table1 = test_db._create_table(
            table_name="test_agno_idempotent", table_type="sessions", db_schema=test_db.db_schema
        )
        table2 = test_db._create_table(
            table_name="test_agno_idempotent", table_type="sessions", db_schema=test_db.db_schema
        )

        assert table1.name == table2.name

        # Verify only one table exists
        with test_db.Session() as session:
            result = session.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = :schema AND table_name = :table"
                ),
                {"schema": test_db.db_schema, "table": "test_agno_idempotent"},
            )
            count = result.scalar()
            assert count == 1

    def test_multiple_table_types_creation(self, test_db: PostgresDb):
        """Test creating all table types in the same schema."""
        table_types = ["sessions", "user_memories", "metrics", "evals", "knowledge"]

        for table_type in table_types:
            table = test_db._get_table(table_type)
            assert isinstance(table, Table)

        # Verify all expected tables exist in database
        expected_table_names = [
            "test_agno_sessions",
            "test_agno_memories",
            "test_agno_metrics",
            "test_agno_evals",
            "test_agno_knowledge",
        ]
        with test_db.Session() as session:
            result = session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = :schema AND table_name = ANY(:table_names)"
                ),
                {"schema": test_db.db_schema, "table_names": expected_table_names},
            )
            found_tables = [row[0] for row in result.fetchall()]

        assert len(found_tables) == len(table_types)
        assert set(found_tables) == set(expected_table_names)


class TestPostgresDbSession:
    """Tests for the session-related methods of PostgresDb"""

    @pytest.fixture(autouse=True)
    def cleanup_sessions(self, test_db: PostgresDb):
        """Fixture to clean-up session rows after each test"""
        yield

        with test_db.Session() as session:
            try:
                sessions_table = test_db._get_table("sessions")
                session.execute(sessions_table.delete())
                session.commit()
            except Exception:
                session.rollback()

    @pytest.fixture
    def sample_agent_session(self) -> AgentSession:
        """Fixture returning a sample AgentSession"""
        agent_run = RunResponse(
            run_id="test_agent_run_1",
            agent_id="test_agent_1",
            user_id="test_user_1",
            status=RunStatus.completed,
            messages=[],
        )
        return AgentSession(
            session_id="test_agent_session_1",
            agent_id="test_agent_1",
            user_id="test_user_1",
            team_id="test_team_1",
            team_session_id="test_team_session_1",
            workflow_id="test_workflow_1",
            session_data={"session_name": "Test Agent Session", "key": "value"},
            agent_data={"name": "Test Agent", "model": "gpt-4"},
            extra_data={"extra_key": "extra_value"},
            runs=[agent_run],
            summary=None,
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )

    @pytest.fixture
    def sample_team_session(self) -> TeamSession:
        """Fixture returning a sample TeamSession"""
        team_run = TeamRunResponse(
            run_id="test_team_run_1",
            team_id="test_team_1",
            status=RunStatus.completed,
            messages=[],
            created_at=int(time.time()),
        )
        return TeamSession(
            session_id="test_team_session_1",
            team_id="test_team_1",
            user_id="test_user_1",
            team_session_id="parent_team_session_1",
            workflow_id="test_workflow_1",
            session_data={"session_name": "Test Team Session", "key": "value"},
            team_data={"name": "Test Team", "model": "gpt-4"},
            extra_data={"extra_key": "extra_value"},
            runs=[team_run],
            summary=None,
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )

    def test_session_table_constraint_exists(self, test_db: PostgresDb):
        """Ensure the session table has the expected unique constraint on session_id"""
        with test_db.Session() as session:
            result = session.execute(
                text(
                    "SELECT constraint_name FROM information_schema.table_constraints "
                    "WHERE table_schema = :schema AND table_name = :table AND constraint_type = 'UNIQUE'"
                ),
                {"schema": test_db.db_schema, "table": "test_agno_sessions"},
            )

            constraint_names = [row[0] for row in result.fetchall()]
            expected_constraint = "test_agno_sessions_uq_session_id"
            assert expected_constraint in constraint_names, (
                f"Session table missing unique constraint {expected_constraint}. Found: {constraint_names}"
            )

    def test_insert_agent_session(self, test_db: PostgresDb, sample_agent_session: AgentSession):
        """Ensure the upsert method works as expected when inserting a new AgentSession"""
        result = test_db.upsert_session(sample_agent_session, deserialize=True)

        assert result is not None
        assert isinstance(result, AgentSession)
        assert result.session_id == sample_agent_session.session_id
        assert result.agent_id == sample_agent_session.agent_id
        assert result.user_id == sample_agent_session.user_id
        assert result.session_data == sample_agent_session.session_data
        assert result.agent_data == sample_agent_session.agent_data

    def test_update_agent_session(self, test_db: PostgresDb, sample_agent_session: AgentSession):
        """Ensure the upsert method works as expected when updating an existing AgentSession"""
        # Inserting
        test_db.upsert_session(sample_agent_session, deserialize=True)

        # Updating
        sample_agent_session.session_data = {"session_name": "Updated Session", "updated": True}
        sample_agent_session.agent_data = {"foo": "bar"}

        result = test_db.upsert_session(sample_agent_session, deserialize=True)

        assert result is not None
        assert isinstance(result, AgentSession)
        assert result.session_data is not None
        assert result.session_data["session_name"] == "Updated Session"
        assert result.agent_data is not None
        assert result.agent_data["foo"] == "bar"

        # Assert Agent runs
        assert result.runs is not None and result.runs[0] is not None
        assert sample_agent_session.runs is not None and sample_agent_session.runs[0] is not None
        assert result.runs[0].run_id == sample_agent_session.runs[0].run_id

    def test_insert_team_session(self, test_db: PostgresDb, sample_team_session: TeamSession):
        """Ensure the upsert method works as expected when inserting a new TeamSession"""
        result = test_db.upsert_session(sample_team_session, deserialize=True)

        assert result is not None
        assert isinstance(result, TeamSession)
        assert result.session_id == sample_team_session.session_id
        assert result.team_id == sample_team_session.team_id
        assert result.user_id == sample_team_session.user_id
        assert result.session_data == sample_team_session.session_data
        assert result.team_data == sample_team_session.team_data

        # Assert Team runs
        assert result.runs is not None and result.runs[0] is not None
        assert sample_team_session.runs is not None and sample_team_session.runs[0] is not None
        assert result.runs[0].run_id == sample_team_session.runs[0].run_id

    def test_update_team_session(self, test_db: PostgresDb, sample_team_session: TeamSession):
        """Ensure the upsert method works as expected when updating an existing TeamSession"""
        # Inserting
        test_db.upsert_session(sample_team_session, deserialize=True)

        # Update
        sample_team_session.session_data = {"session_name": "Updated Team Session", "updated": True}
        sample_team_session.team_data = {"foo": "bar"}

        result = test_db.upsert_session(sample_team_session, deserialize=True)

        assert result is not None
        assert isinstance(result, TeamSession)
        assert result.session_data is not None
        assert result.session_data["session_name"] == "Updated Team Session"
        assert result.team_data is not None
        assert result.team_data["foo"] == "bar"

    def test_upserting_without_deserialization(self, test_db: PostgresDb, sample_agent_session: AgentSession):
        """Ensure the upsert method works as expected when upserting a session without deserialization"""
        result = test_db.upsert_session(sample_agent_session, deserialize=False)

        assert result is not None
        assert isinstance(result, dict)
        assert result["session_id"] == sample_agent_session.session_id

    def test_get_agent_session_by_id(self, test_db: PostgresDb, sample_agent_session: AgentSession):
        """Ensure the get_session method works as expected when retrieving an AgentSession by session_id"""
        # Insert session first
        test_db.upsert_session(sample_agent_session, deserialize=True)

        # Retrieve session
        result = test_db.get_session(
            session_id=sample_agent_session.session_id, session_type=SessionType.AGENT, deserialize=True
        )

        assert result is not None
        assert isinstance(result, AgentSession)
        assert result.session_id == sample_agent_session.session_id
        assert result.agent_id == sample_agent_session.agent_id

    def test_get_team_session_by_id(self, test_db: PostgresDb, sample_team_session: TeamSession):
        """Ensure the get_session method works as expected when retrieving a TeamSession by session_id"""
        # Insert session first
        test_db.upsert_session(sample_team_session, deserialize=True)

        # Retrieve session
        result = test_db.get_session(
            session_id=sample_team_session.session_id, session_type=SessionType.TEAM, deserialize=True
        )

        assert result is not None
        assert isinstance(result, TeamSession)
        assert result.session_id == sample_team_session.session_id
        assert result.team_id == sample_team_session.team_id

    def test_get_session_with_user_id_filter(self, test_db: PostgresDb, sample_agent_session: AgentSession):
        """Ensure the get_session method works as expected when retrieving a session with user_id filter"""
        # Insert session
        test_db.upsert_session(sample_agent_session, deserialize=True)

        # Get with correct user_id
        result = test_db.get_session(
            session_id=sample_agent_session.session_id,
            user_id=sample_agent_session.user_id,
            session_type=SessionType.AGENT,
            deserialize=True,
        )
        assert result is not None

        # Get with wrong user_id
        result = test_db.get_session(
            session_id=sample_agent_session.session_id,
            user_id="wrong_user",
            session_type=SessionType.AGENT,
            deserialize=True,
        )
        assert result is None

    def test_get_session_without_deserialization(self, test_db: PostgresDb, sample_agent_session: AgentSession):
        """Ensure the get_session method works as expected when retrieving a session without deserialization"""
        # Insert session
        test_db.upsert_session(sample_agent_session, deserialize=True)

        # Retrieve as dict
        result = test_db.get_session(
            session_id=sample_agent_session.session_id, session_type=SessionType.AGENT, deserialize=False
        )

        assert result is not None
        assert isinstance(result, dict)
        assert result["session_id"] == sample_agent_session.session_id

    def test_get_nonexistent_session(self, test_db: PostgresDb):
        """Ensure the get_session method returns None and doesn't raise if the session doesn't exist"""
        result = test_db.get_session(session_id="fake_session", session_type=SessionType.AGENT, deserialize=True)
        assert result is None

    def test_get_all_sessions(
        self,
        test_db: PostgresDb,
        sample_agent_session: AgentSession,
        sample_team_session: TeamSession,
    ):
        """Ensure the get_sessions method works as expected when retrieving all sessions"""
        # Insert both sessions
        test_db.upsert_session(sample_agent_session, deserialize=True)
        test_db.upsert_session(sample_team_session, deserialize=True)

        # Get all agent sessions
        agent_sessions = test_db.get_sessions(session_type=SessionType.AGENT, deserialize=True)
        assert len(agent_sessions) == 1
        assert isinstance(agent_sessions[0], AgentSession)

        # Get all team sessions
        team_sessions = test_db.get_sessions(session_type=SessionType.TEAM, deserialize=True)
        assert len(team_sessions) == 1
        assert isinstance(team_sessions[0], TeamSession)

    def test_filtering_by_user_id(self, test_db: PostgresDb):
        """Ensure the get_sessions method works as expected when filtering by user_id"""
        # Create sessions with different user_ids
        session1 = AgentSession(session_id="session1", agent_id="agent1", user_id="user1", created_at=int(time.time()))
        session2 = AgentSession(session_id="session2", agent_id="agent2", user_id="user2", created_at=int(time.time()))

        test_db.upsert_session(session1, deserialize=True)
        test_db.upsert_session(session2, deserialize=True)

        # Filter by user1
        user1_sessions = test_db.get_sessions(session_type=SessionType.AGENT, user_id="user1", deserialize=True)
        assert len(user1_sessions) == 1
        assert user1_sessions[0].user_id == "user1"

    def test_filtering_by_component_id(self, test_db: PostgresDb):
        """Ensure the get_sessions method works as expected when filtering by component_id (agent_id/team_id)"""
        # Create sessions with different agent_ids
        session1 = AgentSession(session_id="session1", agent_id="agent1", user_id="user1", created_at=int(time.time()))
        session2 = AgentSession(session_id="session2", agent_id="agent2", user_id="user1", created_at=int(time.time()))

        test_db.upsert_session(session1, deserialize=True)
        test_db.upsert_session(session2, deserialize=True)

        # Filter by agent_id
        agent1_sessions = test_db.get_sessions(
            session_type=SessionType.AGENT,
            component_id="agent1",
            deserialize=True,
        )
        assert len(agent1_sessions) == 1
        assert isinstance(agent1_sessions[0], AgentSession)
        assert agent1_sessions[0].agent_id == "agent1"

    def test_get_sessions_with_pagination(self, test_db: PostgresDb):
        """Test retrieving sessions with pagination"""

        # Create multiple sessions
        sessions = []
        for i in range(5):
            session = AgentSession(
                session_id=f"session_{i}", agent_id=f"agent_{i}", user_id="test_user", created_at=int(time.time()) + i
            )
            sessions.append(session)
            test_db.upsert_session(session, deserialize=True)

        # Test pagination
        page1 = test_db.get_sessions(session_type=SessionType.AGENT, limit=2, page=1, deserialize=True)
        assert len(page1) == 2

        page2 = test_db.get_sessions(session_type=SessionType.AGENT, limit=2, page=2, deserialize=True)
        assert len(page2) == 2

        # Verify no overlap
        page1_ids = {s.session_id for s in page1}
        page2_ids = {s.session_id for s in page2}
        assert len(page1_ids & page2_ids) == 0

    def test_get_sessions_with_sorting(self, test_db: PostgresDb):
        """Test retrieving sessions with sorting"""
        from agno.db.base import SessionType
        from agno.session.agent import AgentSession

        # Create sessions with different timestamps
        base_time = int(time.time())
        session1 = AgentSession(session_id="session1", agent_id="agent1", created_at=base_time + 100)
        session2 = AgentSession(session_id="session2", agent_id="agent2", created_at=base_time + 200)

        test_db.upsert_session(session1, deserialize=True)
        test_db.upsert_session(session2, deserialize=True)

        # Sort by created_at ascending
        sessions_asc = test_db.get_sessions(
            session_type=SessionType.AGENT, sort_by="created_at", sort_order="asc", deserialize=True
        )
        assert sessions_asc is not None and isinstance(sessions_asc, list)
        assert sessions_asc[0].session_id == "session1"
        assert sessions_asc[1].session_id == "session2"

        # Sort by created_at descending
        sessions_desc = test_db.get_sessions(
            session_type=SessionType.AGENT, sort_by="created_at", sort_order="desc", deserialize=True
        )
        assert sessions_desc is not None and isinstance(sessions_desc, list)
        assert sessions_desc[0].session_id == "session2"
        assert sessions_desc[1].session_id == "session1"

    def test_get_sessions_with_timestamp_filter(self, test_db: PostgresDb):
        """Test retrieving sessions with timestamp filters"""
        from agno.db.base import SessionType
        from agno.session.agent import AgentSession

        base_time = int(time.time())

        # Create sessions at different times
        session1 = AgentSession(
            session_id="session1",
            agent_id="agent1",
            created_at=base_time - 1000,  # Old session
        )
        session2 = AgentSession(
            session_id="session2",
            agent_id="agent2",
            created_at=base_time + 1000,  # New session
        )

        test_db.upsert_session(session1, deserialize=True)
        test_db.upsert_session(session2, deserialize=True)

        # Filter by start timestamp
        recent_sessions = test_db.get_sessions(
            session_type=SessionType.AGENT, start_timestamp=base_time, deserialize=True
        )
        assert len(recent_sessions) == 1
        assert recent_sessions[0].session_id == "session2"

        # Filter by end timestamp
        old_sessions = test_db.get_sessions(session_type=SessionType.AGENT, end_timestamp=base_time, deserialize=True)
        assert len(old_sessions) == 1
        assert old_sessions[0].session_id == "session1"

    def test_get_sessions_with_session_name_filter(self, test_db: PostgresDb):
        """Test retrieving sessions filtered by session name"""
        from agno.db.base import SessionType
        from agno.session.agent import AgentSession

        # Create sessions with different names
        session1 = AgentSession(
            session_id="session1",
            agent_id="agent1",
            session_data={"session_name": "Test Session Alpha"},
            created_at=int(time.time()),
        )
        session2 = AgentSession(
            session_id="session2",
            agent_id="agent2",
            session_data={"session_name": "Test Session Beta"},
            created_at=int(time.time()),
        )

        test_db.upsert_session(session1, deserialize=True)
        test_db.upsert_session(session2, deserialize=True)

        # Search by partial name
        alpha_sessions = test_db.get_sessions(session_type=SessionType.AGENT, session_name="Alpha", deserialize=True)
        assert len(alpha_sessions) == 1
        assert alpha_sessions[0].session_id == "session1"

    def test_get_sessions_without_deserialize(self, test_db: PostgresDb, sample_agent_session: AgentSession):
        """Test retrieving sessions without deserialization"""
        from agno.db.base import SessionType

        # Insert session
        test_db.upsert_session(sample_agent_session, deserialize=True)

        # Get as dicts
        sessions, total_count = test_db.get_sessions(session_type=SessionType.AGENT, deserialize=False)

        assert isinstance(sessions, list)
        assert len(sessions) == 1
        assert isinstance(sessions[0], dict)
        assert sessions[0]["session_id"] == sample_agent_session.session_id
        assert total_count == 1

    def test_rename_agent_session(self, test_db: PostgresDb, sample_agent_session: AgentSession):
        """Test renaming an AgentSession"""
        from agno.db.base import SessionType

        # Insert session
        test_db.upsert_session(sample_agent_session, deserialize=True)

        # Rename session
        new_name = "Renamed Agent Session"
        result = test_db.rename_session(
            session_id=sample_agent_session.session_id,
            session_type=SessionType.AGENT,
            session_name=new_name,
            deserialize=True,
        )

        assert result is not None
        assert isinstance(result, AgentSession)
        assert result.session_data is not None
        assert result.session_data["session_name"] == new_name

    def test_rename_team_session(self, test_db: PostgresDb, sample_team_session: TeamSession):
        """Test renaming a TeamSession"""
        from agno.db.base import SessionType

        # Insert session
        test_db.upsert_session(sample_team_session, deserialize=True)

        # Rename session
        new_name = "Renamed Team Session"
        result = test_db.rename_session(
            session_id=sample_team_session.session_id,
            session_type=SessionType.TEAM,
            session_name=new_name,
            deserialize=True,
        )

        assert result is not None
        assert isinstance(result, TeamSession)
        assert result.session_data is not None
        assert result.session_data["session_name"] == new_name

    def test_rename_session_without_deserialize(self, test_db: PostgresDb, sample_agent_session: AgentSession):
        """Test renaming session without deserialization"""
        from agno.db.base import SessionType

        # Insert session
        test_db.upsert_session(sample_agent_session, deserialize=True)

        # Rename session
        new_name = "Renamed Session Dict"
        result = test_db.rename_session(
            session_id=sample_agent_session.session_id,
            session_type=SessionType.AGENT,
            session_name=new_name,
            deserialize=False,
        )

        assert result is not None
        assert isinstance(result, dict)
        assert result["session_data"]["session_name"] == new_name

    def test_delete_single_session(self, test_db: PostgresDb, sample_agent_session: AgentSession):
        """Test deleting a single session"""
        # Insert session
        test_db.upsert_session(sample_agent_session, deserialize=True)

        # Verify it exists
        from agno.db.base import SessionType

        session = test_db.get_session(
            session_id=sample_agent_session.session_id, session_type=SessionType.AGENT, deserialize=True
        )
        assert session is not None

        # Delete session
        success = test_db.delete_session(sample_agent_session.session_id)
        assert success is True

        # Verify it's gone
        session = test_db.get_session(
            session_id=sample_agent_session.session_id, session_type=SessionType.AGENT, deserialize=True
        )
        assert session is None

    def test_delete_nonexistent_session(self, test_db: PostgresDb):
        """Test deleting a session that doesn't exist"""
        success = test_db.delete_session("nonexistent_session")
        assert success is False

    def test_delete_multiple_sessions(self, test_db: PostgresDb):
        """Test deleting multiple sessions"""
        from agno.db.base import SessionType
        from agno.session.agent import AgentSession

        # Create and insert multiple sessions
        sessions = []
        session_ids = []
        for i in range(3):
            session = AgentSession(session_id=f"session_{i}", agent_id=f"agent_{i}", created_at=int(time.time()))
            sessions.append(session)
            session_ids.append(session.session_id)
            test_db.upsert_session(session, deserialize=True)

        # Verify they exist
        all_sessions = test_db.get_sessions(session_type=SessionType.AGENT, deserialize=True)
        assert len(all_sessions) == 3

        # Delete multiple sessions
        test_db.delete_sessions(session_ids[:2])  # Delete first 2

        # Verify deletion
        remaining_sessions = test_db.get_sessions(session_type=SessionType.AGENT, deserialize=True)
        assert len(remaining_sessions) == 1
        assert remaining_sessions[0].session_id == "session_2"

    def test_session_type_polymorphism(
        self, test_db: PostgresDb, sample_agent_session: AgentSession, sample_team_session: TeamSession
    ):
        """Ensuring session types propagate into types correctly into and out of the database"""

        # Insert both session types
        test_db.upsert_session(sample_agent_session, deserialize=True)
        test_db.upsert_session(sample_team_session, deserialize=True)

        # Verify agent session is returned as AgentSession
        agent_result = test_db.get_session(
            session_id=sample_agent_session.session_id, session_type=SessionType.AGENT, deserialize=True
        )
        assert isinstance(agent_result, AgentSession)

        # Verify team session is returned as TeamSession
        team_result = test_db.get_session(
            session_id=sample_team_session.session_id, session_type=SessionType.TEAM, deserialize=True
        )
        assert isinstance(team_result, TeamSession)

        # Verify wrong session type returns None
        wrong_type_result = test_db.get_session(
            session_id=sample_agent_session.session_id,
            # Wrong session type!
            session_type=SessionType.TEAM,
            deserialize=True,
        )
        assert wrong_type_result is None

    def test_upsert_session_handles_all_agent_session_fields(self, test_db: PostgresDb):
        """Ensure upsert_session correctly handles all AgentSession fields"""
        # Create comprehensive AgentSession with all possible fields populated
        agent_run = RunResponse(
            run_id="test_run_comprehensive",
            agent_id="comprehensive_agent",
            user_id="comprehensive_user",
            status=RunStatus.completed,
            messages=[],
        )

        comprehensive_agent_session = AgentSession(
            session_id="comprehensive_agent_session",
            team_session_id="parent_team_session_id",
            agent_id="comprehensive_agent_id",
            user_id="comprehensive_user_id",
            session_data={
                "session_name": "Comprehensive Agent Session",
                "session_state": {"key": "value"},
                "images": ["image1.jpg", "image2.png"],
                "videos": ["video1.mp4"],
                "audio": ["audio1.wav"],
                "custom_field": "custom_value",
            },
            extra_data={"extra_key1": "extra_value1", "extra_key2": {"nested": "data"}, "extra_list": [1, 2, 3]},
            agent_data={
                "name": "Comprehensive Agent",
                "model": "gpt-4",
                "description": "A comprehensive test agent",
                "capabilities": ["chat", "search", "analysis"],
            },
            runs=[agent_run],
            summary=None,
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )

        # Insert session
        result = test_db.upsert_session(comprehensive_agent_session, deserialize=True)
        assert result is not None
        assert isinstance(result, AgentSession)

        # Verify all fields are preserved
        assert result.session_id == comprehensive_agent_session.session_id
        assert result.team_session_id == comprehensive_agent_session.team_session_id
        assert result.agent_id == comprehensive_agent_session.agent_id
        assert result.team_id == comprehensive_agent_session.team_id
        assert result.user_id == comprehensive_agent_session.user_id
        assert result.workflow_id == comprehensive_agent_session.workflow_id
        assert result.session_data == comprehensive_agent_session.session_data
        assert result.extra_data == comprehensive_agent_session.extra_data
        assert result.agent_data == comprehensive_agent_session.agent_data
        assert result.created_at == comprehensive_agent_session.created_at
        assert result.updated_at == comprehensive_agent_session.updated_at
        assert result.runs is not None
        assert len(result.runs) == 1
        assert result.runs[0].run_id == agent_run.run_id

    def test_upsert_session_handles_all_team_session_fields(self, test_db: PostgresDb):
        """Ensure upsert_session correctly handles all TeamSession fields"""
        # Create comprehensive TeamSession with all possible fields populated
        team_run = TeamRunResponse(
            run_id="test_team_run_comprehensive",
            team_id="comprehensive_team",
            status=RunStatus.completed,
            messages=[],
            created_at=int(time.time()),
        )
        team_summary = SessionSummary(
            summary="Comprehensive team session summary",
            topics=["tests", "fake"],
            last_updated=datetime.now(),
        )

        comprehensive_team_session = TeamSession(
            session_id="comprehensive_team_session",
            team_session_id="parent_team_session_id",
            team_id="comprehensive_team_id",
            user_id="comprehensive_user_id",
            team_data={
                "name": "Comprehensive Team",
                "model": "gpt-4",
                "description": "A comprehensive test team",
                "members": ["agent1", "agent2", "agent3"],
                "strategy": "collaborative",
            },
            session_data={
                "session_name": "Comprehensive Team Session",
                "session_state": {"phase": "active"},
                "images": ["team_image1.jpg"],
                "videos": ["team_video1.mp4"],
                "audio": ["team_audio1.wav"],
                "team_custom_field": "team_custom_value",
            },
            extra_data={
                "team_extra_key1": "team_extra_value1",
                "team_extra_key2": {"nested": "team_data"},
                "team_metrics": {"efficiency": 0.95},
            },
            runs=[team_run],
            summary=team_summary.to_dict(),
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )

        # Insert session
        result = test_db.upsert_session(comprehensive_team_session, deserialize=True)
        assert result is not None
        assert isinstance(result, TeamSession)

        # Verify all fields are preserved
        assert result.session_id == comprehensive_team_session.session_id
        assert result.team_session_id == comprehensive_team_session.team_session_id
        assert result.team_id == comprehensive_team_session.team_id
        assert result.user_id == comprehensive_team_session.user_id
        assert result.team_data == comprehensive_team_session.team_data
        assert result.session_data == comprehensive_team_session.session_data
        assert result.extra_data == comprehensive_team_session.extra_data
        assert isinstance(result.summary, SessionSummary)
        assert result.summary.to_dict() == comprehensive_team_session.summary
        assert result.created_at == comprehensive_team_session.created_at
        assert result.updated_at == comprehensive_team_session.updated_at
        assert result.runs is not None
        assert len(result.runs) == 1
        assert result.runs[0].run_id == team_run.run_id


class TestPostgresDbMemory:
    """Tests for the memory-related methods of PostgresDb"""

    @pytest.fixture(autouse=True)
    def cleanup_memories(self, test_db: PostgresDb):
        """Fixture to clean-up memory rows after each test"""
        yield

        with test_db.Session() as session:
            try:
                memory_table = test_db._get_table("user_memories")
                session.execute(memory_table.delete())
                session.commit()
            except Exception:
                session.rollback()

    @pytest.fixture
    def sample_user_memory(self) -> UserMemory:
        """Fixture returning a sample UserMemory"""
        return UserMemory(
            memory_id="test_memory_1",
            memory="User prefers coffee over tea and likes working in the morning",
            topics=["preferences", "work_habits"],
            user_id="test_user_1",
            input="I prefer coffee and work best in the morning",
            last_updated=datetime.now(),
            feedback="positive",
            agent_id="test_agent_1",
            team_id="test_team_1",
            workflow_id="test_workflow_1",
        )

    def test_insert_memory(self, test_db: PostgresDb, sample_user_memory):
        result = test_db.upsert_user_memory(sample_user_memory, deserialize=True)

        assert result is not None
        assert isinstance(result, UserMemory)
        assert result.memory_id == sample_user_memory.memory_id
        assert result.memory == sample_user_memory.memory
        assert result.topics == sample_user_memory.topics
        assert result.user_id == sample_user_memory.user_id
        assert result.agent_id == sample_user_memory.agent_id
        assert result.team_id == sample_user_memory.team_id
        assert result.workflow_id == sample_user_memory.workflow_id

    def test_update_memory(self, test_db: PostgresDb, sample_user_memory):
        # Insert initial memory
        test_db.upsert_user_memory(sample_user_memory, deserialize=True)

        # Update the memory
        sample_user_memory.memory = "Updated: User prefers tea now and works best at night"
        sample_user_memory.topics = ["preferences", "work_habits", "updated"]

        result = test_db.upsert_user_memory(sample_user_memory, deserialize=True)

        assert result is not None
        assert isinstance(result, UserMemory)
        assert result.memory == sample_user_memory.memory
        assert result.topics == sample_user_memory.topics

    def test_upsert_user_memory_without_deserialize(self, test_db: PostgresDb, sample_user_memory):
        """Ensure upsert_user_memory without deserialization returns a dict"""
        result = test_db.upsert_user_memory(sample_user_memory, deserialize=False)

        assert result is not None
        assert isinstance(result, dict)
        assert result["memory_id"] == sample_user_memory.memory_id

    def test_get_user_memory_by_id(self, test_db: PostgresDb, sample_user_memory):
        """Ensure get_user_memory returns a UserMemory"""
        test_db.upsert_user_memory(sample_user_memory, deserialize=True)

        result = test_db.get_user_memory(memory_id=sample_user_memory.memory_id, deserialize=True)

        assert result is not None
        assert isinstance(result, UserMemory)
        assert result.memory_id == sample_user_memory.memory_id
        assert result.memory == sample_user_memory.memory

    def test_get_nonexistent_user_memory(self, test_db: PostgresDb):
        """Ensure get_user_memory returns None for a nonexistent memory"""
        result = test_db.get_user_memory(memory_id="nonexistent_memory", deserialize=True)
        assert result is None

    def test_get_user_memory_without_deserialize(self, test_db: PostgresDb, sample_user_memory):
        """Ensure get_user_memory without deserialization returns a dict"""
        test_db.upsert_user_memory(sample_user_memory, deserialize=True)

        result = test_db.get_user_memory(memory_id=sample_user_memory.memory_id, deserialize=False)

        assert result is not None
        assert isinstance(result, dict)
        assert result["memory_id"] == sample_user_memory.memory_id

    def test_delete_user_memory(self, test_db: PostgresDb, sample_user_memory):
        """Ensure delete_user_memory deletes the memory"""
        test_db.upsert_user_memory(sample_user_memory, deserialize=True)

        # Verify the memory exists
        memory = test_db.get_user_memory(memory_id=sample_user_memory.memory_id, deserialize=True)
        assert memory is not None

        # Delete the memory
        success = test_db.delete_user_memory(sample_user_memory.memory_id)
        assert success is True

        # Verify the memory has been deleted
        memory = test_db.get_user_memory(memory_id=sample_user_memory.memory_id, deserialize=True)
        assert memory is None

    def test_delete_multiple_user_memories(self, test_db: PostgresDb):
        """Ensure delete_user_memories deletes multiple memories"""

        # Inserting some memories
        memory_ids = []
        for i in range(3):
            memory = UserMemory(
                memory_id=f"memory_{i}", memory=f"Test memory {i}", user_id="test_user", last_updated=datetime.now()
            )
            test_db.upsert_user_memory(memory, deserialize=True)
            memory_ids.append(memory.memory_id)

        # Deleting the first two memories
        test_db.delete_user_memories(memory_ids[:2])

        # Verify deletions
        deleted_memory_1 = test_db.get_user_memory(memory_id="memory_0", deserialize=True)
        deleted_memory_2 = test_db.get_user_memory(memory_id="memory_1", deserialize=True)
        assert deleted_memory_1 is None
        assert deleted_memory_2 is None

        # Verify the third memory was not deleted
        remaining_memory = test_db.get_user_memory(memory_id="memory_2", deserialize=True)
        assert remaining_memory is not None

    def test_get_all_memory_topics(self, test_db: PostgresDb):
        """Ensure get_all_memory_topics returns all unique memory topics"""

        # Create memories with different topics
        memories = [
            UserMemory(
                memory_id="memory_1",
                memory="Memory 1",
                topics=["topic1", "topic2"],
                user_id="user1",
                last_updated=datetime.now(),
            ),
            UserMemory(
                memory_id="memory_2",
                memory="Memory 2",
                topics=["topic2", "topic3"],
                user_id="user2",
                last_updated=datetime.now(),
            ),
            UserMemory(
                memory_id="memory_3",
                memory="Memory 3",
                topics=["topic1", "topic4"],
                user_id="user3",
                last_updated=datetime.now(),
            ),
        ]

        for memory in memories:
            test_db.upsert_user_memory(memory, deserialize=True)

        # Get all topics
        topics = test_db.get_all_memory_topics()
        assert set(topics) == {"topic1", "topic2", "topic3", "topic4"}

    def test_get_user_memory_stats(self, test_db: PostgresDb):
        """Ensure get_user_memory_stats returns the correct statistics"""

        # Inserting some memories
        memories = [
            UserMemory(
                memory_id="memory_1", memory="Memory 1", user_id="user1", agent_id="agent1", last_updated=datetime.now()
            ),
            UserMemory(
                memory_id="memory_2", memory="Memory 2", user_id="user1", agent_id="agent2", last_updated=datetime.now()
            ),
        ]

        for memory in memories:
            test_db.upsert_user_memory(memory, deserialize=True)

        # Verify the correct statistics are returned
        stats, count = test_db.get_user_memory_stats()
        assert count == 1
        assert len(stats) == 1
        assert stats[0]["user_id"] == "user1"
        assert stats[0]["total_memories"] == 2

    def test_comprehensive_user_memory_fields(self, test_db: PostgresDb):
        """Ensure all UserMemory fields are properly handled"""

        # Creating a comprehensive memory
        comprehensive_memory = UserMemory(
            memory_id="comprehensive_memory",
            memory="This is a comprehensive test memory with detailed information about user preferences and behaviors",
            topics=["preferences", "behavior", "detailed", "comprehensive"],
            user_id="comprehensive_user",
            input="Original input that led to this memory being created",
            last_updated=datetime(2021, 1, 1, 12, 0, 0),
            feedback="Very positive feedback about this memory",
            agent_id="comprehensive_agent",
            team_id="comprehensive_team",
            workflow_id="comprehensive_workflow",
        )

        # Inserting the memory
        result = test_db.upsert_user_memory(comprehensive_memory, deserialize=True)
        assert result is not None
        assert isinstance(result, UserMemory)

        # Verify all fields are preserved
        assert result.memory_id == comprehensive_memory.memory_id
        assert result.memory == comprehensive_memory.memory
        assert result.topics == comprehensive_memory.topics
        assert result.user_id == comprehensive_memory.user_id
        assert result.input == comprehensive_memory.input
        assert result.agent_id == comprehensive_memory.agent_id
        assert result.team_id == comprehensive_memory.team_id
        assert result.workflow_id == comprehensive_memory.workflow_id

        # Verify the memory can be retrieved with all fields intact
        retrieved = test_db.get_user_memory(
            memory_id=comprehensive_memory.memory_id,  # type: ignore
            deserialize=True,
        )
        assert retrieved is not None and isinstance(retrieved, UserMemory)
        assert retrieved.memory_id == comprehensive_memory.memory_id
        assert retrieved.memory == comprehensive_memory.memory
        assert retrieved.topics == comprehensive_memory.topics
        assert retrieved.user_id == comprehensive_memory.user_id
        assert retrieved.input == comprehensive_memory.input
        assert retrieved.agent_id == comprehensive_memory.agent_id
        assert retrieved.team_id == comprehensive_memory.team_id
        assert retrieved.workflow_id == comprehensive_memory.workflow_id


class TestPostgresDbMetrics:
    """Tests for the metric-related methods of PostgresDb"""


class TestPostgresDbEvals:
    """Tests for the eval-related methods of PostgresDb"""


class TestPostgresDbKnowledge:
    """Tests for the knowledge-related methods of PostgresDb"""
