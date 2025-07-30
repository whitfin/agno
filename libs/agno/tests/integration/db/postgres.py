"""Integration tests for the PostgresDb class"""

import time
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Generator, List

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.schema import Table

from agno.db.base import SessionType
from agno.db.postgres.postgres import PostgresDb
from agno.db.postgres.schemas import SESSION_TABLE_SCHEMA
from agno.db.schemas.evals import EvalFilterType, EvalRunRecord, EvalType
from agno.db.schemas.knowledge import KnowledgeRow
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


@pytest.fixture(scope="class")
def test_db(engine: Engine) -> Generator[PostgresDb, None, None]:
    """PostgresDb instance to be used across all tests"""
    schema = f"session_test_schema_{uuid.uuid4().hex[:8]}"
    db = PostgresDb(
        db_engine=engine,
        db_schema=schema,
        session_table="test_agno_sessions",
        memory_table="test_agno_memories",
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
        table = test_db._get_table("memories")
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
        table_types = ["sessions", "memories", "metrics", "evals", "knowledge"]

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
                memory_table = test_db._get_table("memories")
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
        test_db.delete_user_memory(sample_user_memory.memory_id)

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

    @pytest.fixture(autouse=True)
    def cleanup_metrics_and_sessions(self, test_db: PostgresDb):
        """Fixture to clean-up metrics and session rows after each test"""
        yield

        with test_db.Session() as session:
            try:
                metrics_table = test_db._get_table("metrics")
                session.execute(metrics_table.delete())
                sessions_table = test_db._get_table("sessions")
                session.execute(sessions_table.delete())
                session.commit()
            except Exception:
                session.rollback()

    @pytest.fixture
    def sample_agent_sessions_for_metrics(self) -> List[AgentSession]:
        """Fixture returning sample AgentSessions for metrics testing"""
        base_time = int(time.time()) - 86400  # 1 day ago
        sessions = []

        for i in range(3):
            agent_run = RunResponse(
                run_id=f"test_run_{i}",
                agent_id=f"test_agent_{i}",
                user_id=f"test_user_{i}",
                status=RunStatus.completed,
                messages=[],
            )
            session = AgentSession(
                session_id=f"test_session_{i}",
                agent_id=f"test_agent_{i}",
                user_id=f"test_user_{i}",
                session_data={"session_name": f"Test Session {i}"},
                agent_data={"name": f"Test Agent {i}", "model": "gpt-4"},
                runs=[agent_run],
                created_at=base_time + (i * 3600),  # 1 hour apart
                updated_at=base_time + (i * 3600),
            )
            sessions.append(session)

        return sessions

    def test_get_all_sessions_for_metrics_calculation(self, test_db: PostgresDb, sample_agent_sessions_for_metrics):
        """Test the _get_all_sessions_for_metrics_calculation util method"""
        # Insert test sessions
        for session in sample_agent_sessions_for_metrics:
            test_db.upsert_session(session, deserialize=True)

        # Test getting all sessions
        sessions = test_db._get_all_sessions_for_metrics_calculation()

        assert len(sessions) == 3
        assert all("user_id" in session for session in sessions)
        assert all("session_data" in session for session in sessions)
        assert all("runs" in session for session in sessions)
        assert all("created_at" in session for session in sessions)
        assert all("session_type" in session for session in sessions)

    def test_get_all_sessions_for_metrics_calculation_with_timestamp_filter(
        self, test_db: PostgresDb, sample_agent_sessions_for_metrics
    ):
        """Test the _get_all_sessions_for_metrics_calculation util method with timestamp filters"""
        # Insert test sessions
        for session in sample_agent_sessions_for_metrics:
            test_db.upsert_session(session, deserialize=True)

        # Test with start timestamp filter
        start_time = sample_agent_sessions_for_metrics[1].created_at
        sessions = test_db._get_all_sessions_for_metrics_calculation(start_timestamp=start_time)

        assert len(sessions) == 2  # Should get the last 2 sessions

        # Test with end timestamp filter
        end_time = sample_agent_sessions_for_metrics[1].created_at
        sessions = test_db._get_all_sessions_for_metrics_calculation(end_timestamp=end_time)

        assert len(sessions) == 2  # Should get the first 2 sessions

    def test_get_metrics_calculation_starting_date_no_metrics_no_sessions(self, test_db: PostgresDb):
        """Test the _get_metrics_calculation_starting_date util method with no metrics and no sessions"""
        metrics_table = test_db._get_table("metrics")

        result = test_db._get_metrics_calculation_starting_date(metrics_table)

        assert result is None

    def test_get_metrics_calculation_starting_date_no_metrics_with_sessions(
        self, test_db: PostgresDb, sample_agent_sessions_for_metrics
    ):
        """Test the _get_metrics_calculation_starting_date util method with no metrics but with sessions"""
        # Insert test sessions
        for session in sample_agent_sessions_for_metrics:
            test_db.upsert_session(session, deserialize=True)

        metrics_table = test_db._get_table("metrics")
        result = test_db._get_metrics_calculation_starting_date(metrics_table)

        assert result is not None

        # Should return the date of the first session
        first_session_date = datetime.fromtimestamp(
            sample_agent_sessions_for_metrics[0].created_at, tz=timezone.utc
        ).date()
        assert result == first_session_date

    def test_calculate_metrics_no_sessions(self, test_db: PostgresDb):
        """Ensure the calculate_metrics method returns None when there are no sessions"""
        result = test_db.calculate_metrics()

        assert result is None

    def test_calculate_metrics(self, test_db: PostgresDb, sample_agent_sessions_for_metrics):
        """Ensure the calculate_metrics method returns a list of metrics when there are sessions"""
        for session in sample_agent_sessions_for_metrics:
            test_db.upsert_session(session, deserialize=True)

        # Calculate metrics
        result = test_db.calculate_metrics()
        assert result is not None
        assert isinstance(result, list)

    def test_get_metrics_with_date_filter(self, test_db: PostgresDb, sample_agent_sessions_for_metrics):
        """Test the get_metrics method with date filters"""
        # Insert test sessions and calculate metrics
        for session in sample_agent_sessions_for_metrics:
            test_db.upsert_session(session, deserialize=True)

        # Calculate metrics to populate the metrics table
        test_db.calculate_metrics()

        # Test getting metrics without filters
        metrics, latest_update = test_db.get_metrics()
        assert isinstance(metrics, list)
        assert latest_update is not None

        # Test with date range filter
        today = date.today()
        yesterday = today - timedelta(days=1)

        metrics_filtered, _ = test_db.get_metrics(starting_date=yesterday, ending_date=today)
        assert isinstance(metrics_filtered, list)

    def test_metrics_table_creation(self, test_db: PostgresDb):
        """Ensure the metrics table is created properly"""
        metrics_table = test_db._get_table("metrics")

        assert metrics_table is not None
        assert metrics_table.name == "test_agno_metrics"
        assert metrics_table.schema == test_db.db_schema

        # Verify essential columns exist
        column_names = [col.name for col in metrics_table.columns]
        expected_columns = ["date", "completed", "updated_at"]
        for col in expected_columns:
            assert col in column_names, f"Missing column: {col}"

    def test_calculate_metrics_idempotency(self, test_db: PostgresDb, sample_agent_sessions_for_metrics):
        """Ensure the calculate_metrics method is idempotent"""
        # Insert test sessions
        for session in sample_agent_sessions_for_metrics:
            test_db.upsert_session(session, deserialize=True)

        # Calculate metrics first time
        result1 = test_db.calculate_metrics()
        assert result1 is not None

        # Calculate metrics second time - should not process already completed dates
        result2 = test_db.calculate_metrics()
        assert result2 is None or isinstance(result2, list)

    def test_get_metrics_with_invalid_date_range(self, test_db: PostgresDb):
        """Test get_metrics with invalid date range (end before start)"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Pass end date before start date
        metrics, latest_update = test_db.get_metrics(starting_date=today, ending_date=yesterday)
        assert metrics == []
        assert latest_update is None

    def test_metrics_flow(self, test_db: PostgresDb, sample_agent_sessions_for_metrics):
        """Comprehensive test for the full metrics flow: insert sessions, calculate metrics, retrieve metrics"""

        # Step 1: Insert test sessions
        for session in sample_agent_sessions_for_metrics:
            test_db.upsert_session(session, deserialize=True)

        # Step 2: Verify sessions were inserted
        all_sessions = test_db.get_sessions(session_type=SessionType.AGENT, deserialize=True)
        assert len(all_sessions) == 3

        # Step 3: Calculate metrics
        calculated_metrics = test_db.calculate_metrics()
        assert calculated_metrics is not None

        # Step 4: Retrieve metrics
        metrics, latest_update = test_db.get_metrics()
        assert isinstance(metrics, list)
        assert len(metrics) > 0
        assert latest_update is not None

        # Step 5: Verify relevant metrics fields are there
        assert metrics[0] is not None and len(metrics) == 1
        metrics_obj = metrics[0]
        assert metrics_obj["completed"] is True
        assert metrics_obj["agent_runs_count"] == 3
        assert metrics_obj["team_runs_count"] == 0
        assert metrics_obj["workflow_runs_count"] == 0
        assert metrics_obj["updated_at"] is not None
        assert metrics_obj["created_at"] is not None
        assert metrics_obj["date"] is not None
        assert metrics_obj["aggregation_period"] == "daily"

    @pytest.fixture
    def sample_multi_day_sessions(self) -> List[AgentSession]:
        """Fixture returning sessions spread across multiple days"""
        sessions = []
        base_time = int(time.time()) - (3 * 86400)  # 3 days ago

        # Day 1: 2 sessions
        for i in range(2):
            agent_run = RunResponse(
                run_id=f"day1_run_{i}",
                agent_id=f"day1_agent_{i}",
                user_id=f"day1_user_{i}",
                status=RunStatus.completed,
                messages=[],
            )
            session = AgentSession(
                session_id=f"day1_session_{i}",
                agent_id=f"day1_agent_{i}",
                user_id=f"day1_user_{i}",
                session_data={"session_name": f"Day 1 Session {i}"},
                agent_data={"name": f"Day 1 Agent {i}", "model": "gpt-4"},
                runs=[agent_run],
                created_at=base_time + (i * 3600),  # 1 hour apart
                updated_at=base_time + (i * 3600),
            )
            sessions.append(session)

        # Day 2: 3 sessions (next day)
        day2_base = base_time + 86400  # Add 1 day
        for i in range(3):
            agent_run = RunResponse(
                run_id=f"day2_run_{i}",
                agent_id=f"day2_agent_{i}",
                user_id=f"day2_user_{i}",
                status=RunStatus.completed,
                messages=[],
            )
            session = AgentSession(
                session_id=f"day2_session_{i}",
                agent_id=f"day2_agent_{i}",
                user_id=f"day2_user_{i}",
                session_data={"session_name": f"Day 2 Session {i}"},
                agent_data={"name": f"Day 2 Agent {i}", "model": "gpt-4"},
                runs=[agent_run],
                created_at=day2_base + (i * 3600),  # 1 hour apart
                updated_at=day2_base + (i * 3600),
            )
            sessions.append(session)

        # Day 3: 1 session (next day)
        day3_base = base_time + (2 * 86400)  # Add 2 days
        agent_run = RunResponse(
            run_id="day3_run_0",
            agent_id="day3_agent_0",
            user_id="day3_user_0",
            status=RunStatus.completed,
            messages=[],
        )
        session = AgentSession(
            session_id="day3_session_0",
            agent_id="day3_agent_0",
            user_id="day3_user_0",
            session_data={"session_name": "Day 3 Session 0"},
            agent_data={"name": "Day 3 Agent 0", "model": "gpt-4"},
            runs=[agent_run],
            created_at=day3_base,
            updated_at=day3_base,
        )
        sessions.append(session)

        return sessions

    def test_calculate_metrics_multiple_days(self, test_db: PostgresDb, sample_multi_day_sessions):
        """Test that metrics calculation creates separate rows for different days"""
        # Insert sessions across multiple days
        for session in sample_multi_day_sessions:
            test_db.upsert_session(session, deserialize=True)

        # Calculate metrics
        result = test_db.calculate_metrics()
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 3  # Should have 3 metrics records for 3 different days

        # Retrieve all metrics
        metrics, latest_update = test_db.get_metrics()
        assert len(metrics) == 3  # Should have 3 rows, one per day
        assert latest_update is not None

        # Sort metrics by date for consistent checking
        metrics_sorted = sorted(metrics, key=lambda x: x["date"])

        # Verify Day 1 metrics (2 sessions)
        day1_metrics = metrics_sorted[0]
        assert day1_metrics["agent_runs_count"] == 2
        assert day1_metrics["team_runs_count"] == 0
        assert day1_metrics["workflow_runs_count"] == 0
        assert day1_metrics["completed"] is True

        # Verify Day 2 metrics (3 sessions)
        day2_metrics = metrics_sorted[1]
        assert day2_metrics["agent_runs_count"] == 3
        assert day2_metrics["team_runs_count"] == 0
        assert day2_metrics["workflow_runs_count"] == 0
        assert day2_metrics["completed"] is True

        # Verify Day 3 metrics (1 session)
        day3_metrics = metrics_sorted[2]
        assert day3_metrics["agent_runs_count"] == 1
        assert day3_metrics["team_runs_count"] == 0
        assert day3_metrics["workflow_runs_count"] == 0
        assert day3_metrics["completed"] is True

    def test_calculate_metrics_mixed_session_types_multiple_days(self, test_db: PostgresDb):
        """Test metrics calculation with different session types across multiple days"""
        base_time = int(time.time()) - (2 * 86400)  # 2 days ago
        sessions = []

        # Day 1: Agent and Team sessions
        day1_base = base_time

        # Agent session
        agent_run = RunResponse(
            run_id="mixed_agent_run",
            agent_id="mixed_agent",
            user_id="mixed_user",
            status=RunStatus.completed,
            messages=[],
        )
        agent_session = AgentSession(
            session_id="mixed_agent_session",
            agent_id="mixed_agent",
            user_id="mixed_user",
            session_data={"session_name": "Mixed Agent Session"},
            agent_data={"name": "Mixed Agent", "model": "gpt-4"},
            runs=[agent_run],
            created_at=day1_base,
            updated_at=day1_base,
        )
        sessions.append(agent_session)

        # Team session
        team_run = TeamRunResponse(
            run_id="mixed_team_run",
            team_id="mixed_team",
            status=RunStatus.completed,
            messages=[],
            created_at=day1_base + 3600,
        )
        team_session = TeamSession(
            session_id="mixed_team_session",
            team_id="mixed_team",
            user_id="mixed_user",
            session_data={"session_name": "Mixed Team Session"},
            team_data={"name": "Mixed Team", "model": "gpt-4"},
            runs=[team_run],
            created_at=day1_base + 3600,
            updated_at=day1_base + 3600,
        )
        sessions.append(team_session)

        # Day 2: Only Agent sessions
        day2_base = base_time + 86400
        for i in range(2):
            agent_run = RunResponse(
                run_id=f"day2_mixed_run_{i}",
                agent_id=f"day2_mixed_agent_{i}",
                user_id="mixed_user",
                status=RunStatus.completed,
                messages=[],
            )
            agent_session = AgentSession(
                session_id=f"day2_mixed_session_{i}",
                agent_id=f"day2_mixed_agent_{i}",
                user_id="mixed_user",
                session_data={"session_name": f"Day 2 Mixed Session {i}"},
                agent_data={"name": f"Day 2 Mixed Agent {i}", "model": "gpt-4"},
                runs=[agent_run],
                created_at=day2_base + (i * 3600),
                updated_at=day2_base + (i * 3600),
            )
            sessions.append(agent_session)

        # Insert all sessions
        for session in sessions:
            test_db.upsert_session(session, deserialize=True)

        # Calculate metrics
        result = test_db.calculate_metrics()
        assert result is not None
        assert len(result) == 2  # Should have 2 metrics records for 2 different days

        # Retrieve metrics
        metrics, _ = test_db.get_metrics()
        assert len(metrics) == 2

        # Sort by date
        metrics_sorted = sorted(metrics, key=lambda x: x["date"])

        # Day 1: 1 agent run + 1 team run
        day1_metrics = metrics_sorted[0]
        assert day1_metrics["agent_runs_count"] == 1
        assert day1_metrics["team_runs_count"] == 1
        assert day1_metrics["workflow_runs_count"] == 0

        # Day 2: 2 agent runs
        day2_metrics = metrics_sorted[1]
        assert day2_metrics["agent_runs_count"] == 2
        assert day2_metrics["team_runs_count"] == 0
        assert day2_metrics["workflow_runs_count"] == 0

    def test_get_metrics_date_range_multiple_days(self, test_db: PostgresDb, sample_multi_day_sessions):
        """Test retrieving metrics with date range filters across multiple days"""
        # Insert sessions and calculate metrics
        for session in sample_multi_day_sessions:
            test_db.upsert_session(session, deserialize=True)

        test_db.calculate_metrics()

        # Get the date range from the first and last sessions
        first_session_date = datetime.fromtimestamp(sample_multi_day_sessions[0].created_at, tz=timezone.utc).date()
        last_session_date = datetime.fromtimestamp(sample_multi_day_sessions[-1].created_at, tz=timezone.utc).date()

        # Test getting metrics for the full range
        metrics_full, _ = test_db.get_metrics(starting_date=first_session_date, ending_date=last_session_date)
        assert len(metrics_full) == 3  # All 3 days

        # Test getting metrics for partial range (first 2 days)
        second_day = first_session_date + timedelta(days=1)
        metrics_partial, _ = test_db.get_metrics(starting_date=first_session_date, ending_date=second_day)
        assert len(metrics_partial) == 2  # First 2 days only

        # Test getting metrics for single day
        metrics_single, _ = test_db.get_metrics(starting_date=first_session_date, ending_date=first_session_date)
        assert len(metrics_single) == 1  # First day only
        assert metrics_single[0]["agent_runs_count"] == 2  # Day 1 had 2 sessions

    def test_metrics_calculation_multiple_days(self, test_db: PostgresDb):
        """Ensure that metrics calculation can handle calculating metrics for multiple days at once"""
        base_time = int(time.time()) - (2 * 86400)  # 2 days ago

        # Add sessions for Day 1
        day1_sessions = []
        for i in range(2):
            agent_run = RunResponse(
                run_id=f"incremental_day1_run_{i}",
                agent_id=f"incremental_day1_agent_{i}",
                user_id="incremental_user",
                status=RunStatus.completed,
                messages=[],
            )
            session = AgentSession(
                session_id=f"incremental_day1_session_{i}",
                agent_id=f"incremental_day1_agent_{i}",
                user_id="incremental_user",
                session_data={"session_name": f"Incremental Day 1 Session {i}"},
                agent_data={"name": f"Incremental Day 1 Agent {i}", "model": "gpt-4"},
                runs=[agent_run],
                created_at=base_time + (i * 3600),
                updated_at=base_time + (i * 3600),
            )
            day1_sessions.append(session)

        # Insert Day 1 sessions and calculate metrics
        for session in day1_sessions:
            test_db.upsert_session(session, deserialize=True)

        # Calculate metircs for day 1
        result1 = test_db.calculate_metrics()
        assert result1 is not None
        assert len(result1) == 1

        # Verify day 1 metrics exist
        metrics1, _ = test_db.get_metrics()
        assert len(metrics1) == 1
        assert metrics1[0]["agent_runs_count"] == 2

        # Add sessions for day 2
        day2_base = base_time + 86400
        day2_sessions = []
        for i in range(3):
            agent_run = RunResponse(
                run_id=f"incremental_day2_run_{i}",
                agent_id=f"incremental_day2_agent_{i}",
                user_id="incremental_user",
                status=RunStatus.completed,
                messages=[],
            )
            session = AgentSession(
                session_id=f"incremental_day2_session_{i}",
                agent_id=f"incremental_day2_agent_{i}",
                user_id="incremental_user",
                session_data={"session_name": f"Incremental Day 2 Session {i}"},
                agent_data={"name": f"Incremental Day 2 Agent {i}", "model": "gpt-4"},
                runs=[agent_run],
                created_at=day2_base + (i * 3600),
                updated_at=day2_base + (i * 3600),
            )
            day2_sessions.append(session)

        # Insert day 2 sessions and calculate metrics again
        for session in day2_sessions:
            test_db.upsert_session(session, deserialize=True)

        # Calculate metrics for day 2
        result2 = test_db.calculate_metrics()
        assert result2 is not None
        assert len(result2) == 1

        # Verify both days' metrics exist
        metrics2, _ = test_db.get_metrics()
        assert len(metrics2) == 2
        metrics_sorted = sorted(metrics2, key=lambda x: x["date"])
        assert metrics_sorted[0]["agent_runs_count"] == 2
        assert metrics_sorted[1]["agent_runs_count"] == 3


class TestPostgresDbEvals:
    """Tests for the eval-related methods of PostgresDb"""

    @pytest.fixture(autouse=True)
    def cleanup_evals(self, test_db: PostgresDb):
        """Fixture to clean-up eval rows after each test"""
        yield

        with test_db.Session() as session:
            try:
                eval_table = test_db._get_table("evals")
                session.execute(eval_table.delete())
                session.commit()
            except Exception:
                session.rollback()

    @pytest.fixture
    def sample_eval_run_agent(self) -> EvalRunRecord:
        """Fixture returning a sample EvalRunRecord for agent evaluation"""
        return EvalRunRecord(
            run_id="test_eval_run_agent_1",
            agent_id="test_agent_1",
            model_id="gpt-4",
            model_provider="openai",
            name="Agent Accuracy Test",
            evaluated_component_name="Test Agent",
            eval_type=EvalType.ACCURACY,
            eval_data={
                "score": 0.85,
                "total_questions": 100,
                "correct_answers": 85,
                "test_duration": 120.5,
                "categories": ["math", "logic", "reasoning"],
                "details": {"math_score": 0.90, "logic_score": 0.80, "reasoning_score": 0.85},
            },
        )

    @pytest.fixture
    def sample_eval_run_team(self) -> EvalRunRecord:
        """Fixture returning a sample EvalRunRecord for team evaluation"""
        return EvalRunRecord(
            run_id="test_eval_run_team_1",
            team_id="test_team_1",
            model_id="gpt-4-turbo",
            model_provider="openai",
            name="Team Performance Test",
            evaluated_component_name="Test Team",
            eval_type=EvalType.PERFORMANCE,
            eval_data={
                "response_time": 45.2,
                "throughput": 25.7,
                "success_rate": 0.92,
                "collaboration_score": 0.88,
                "efficiency_metrics": {
                    "task_completion_time": 30.5,
                    "resource_utilization": 0.75,
                    "coordination_overhead": 0.12,
                },
            },
        )

    @pytest.fixture
    def sample_eval_run_workflow(self) -> EvalRunRecord:
        """Fixture returning a sample EvalRunRecord for workflow evaluation"""
        return EvalRunRecord(
            run_id="test_eval_run_workflow_1",
            workflow_id="test_workflow_1",
            model_id="claude-3-opus",
            model_provider="anthropic",
            name="Workflow Reliability Test",
            evaluated_component_name="Test Workflow",
            eval_type=EvalType.RELIABILITY,
            eval_data={
                "uptime": 0.999,
                "error_rate": 0.001,
                "recovery_time": 2.5,
                "consistency_score": 0.95,
                "fault_tolerance": {
                    "max_failures_handled": 5,
                    "recovery_success_rate": 1.0,
                    "mean_time_to_recovery": 1.8,
                },
            },
        )

    def test_create_eval_run_agent(self, test_db: PostgresDb, sample_eval_run_agent: EvalRunRecord):
        """Test creating an agent eval run"""
        result = test_db.create_eval_run(sample_eval_run_agent)

        assert result is not None
        assert isinstance(result, EvalRunRecord)
        assert result.run_id == sample_eval_run_agent.run_id
        assert result.agent_id == sample_eval_run_agent.agent_id
        assert result.eval_type == sample_eval_run_agent.eval_type
        assert result.eval_data == sample_eval_run_agent.eval_data
        assert result.name == sample_eval_run_agent.name
        assert result.model_id == sample_eval_run_agent.model_id

    def test_create_eval_run_team(self, test_db: PostgresDb, sample_eval_run_team: EvalRunRecord):
        """Test creating a team eval run"""
        result = test_db.create_eval_run(sample_eval_run_team)

        assert result is not None
        assert isinstance(result, EvalRunRecord)
        assert result.run_id == sample_eval_run_team.run_id
        assert result.team_id == sample_eval_run_team.team_id
        assert result.eval_type == sample_eval_run_team.eval_type
        assert result.eval_data == sample_eval_run_team.eval_data

    def test_create_eval_run_workflow(self, test_db: PostgresDb, sample_eval_run_workflow: EvalRunRecord):
        """Test creating a workflow eval run"""
        result = test_db.create_eval_run(sample_eval_run_workflow)

        assert result is not None
        assert isinstance(result, EvalRunRecord)
        assert result.run_id == sample_eval_run_workflow.run_id
        assert result.workflow_id == sample_eval_run_workflow.workflow_id
        assert result.eval_type == sample_eval_run_workflow.eval_type
        assert result.eval_data == sample_eval_run_workflow.eval_data

    def test_get_eval_run_with_deserialization(self, test_db: PostgresDb, sample_eval_run_agent: EvalRunRecord):
        """Test getting an eval run with deserialization"""
        test_db.create_eval_run(sample_eval_run_agent)

        result = test_db.get_eval_run(sample_eval_run_agent.run_id, deserialize=True)

        assert result is not None
        assert isinstance(result, EvalRunRecord)
        assert result.run_id == sample_eval_run_agent.run_id
        assert result.agent_id == sample_eval_run_agent.agent_id
        assert result.eval_type == sample_eval_run_agent.eval_type
        assert result.eval_data == sample_eval_run_agent.eval_data

    def test_get_eval_run_without_deserialization(self, test_db: PostgresDb, sample_eval_run_agent: EvalRunRecord):
        """Test getting an eval run without deserialization"""
        test_db.create_eval_run(sample_eval_run_agent)

        result = test_db.get_eval_run(sample_eval_run_agent.run_id, deserialize=False)

        assert result is not None
        assert isinstance(result, dict)
        assert result["run_id"] == sample_eval_run_agent.run_id
        assert result["agent_id"] == sample_eval_run_agent.agent_id

    def test_delete_eval_run(self, test_db: PostgresDb, sample_eval_run_agent: EvalRunRecord):
        """Test deleting a single eval run"""
        test_db.create_eval_run(sample_eval_run_agent)

        # Verify it exists
        eval_run = test_db.get_eval_run(sample_eval_run_agent.run_id, deserialize=True)
        assert eval_run is not None

        # Delete it
        test_db.delete_eval_run(sample_eval_run_agent.run_id)

        # Verify it's gone
        eval_run = test_db.get_eval_run(sample_eval_run_agent.run_id, deserialize=True)
        assert eval_run is None

    def test_delete_multiple_eval_runs(self, test_db: PostgresDb):
        """Test deleting multiple eval runs"""
        # Create multiple eval runs
        eval_runs = []
        run_ids = []
        for i in range(3):
            eval_run = EvalRunRecord(
                run_id=f"test_eval_run_{i}",
                agent_id=f"test_agent_{i}",
                eval_type=EvalType.ACCURACY,
                eval_data={"score": 0.8 + (i * 0.05)},
                name=f"Test Eval {i}",
            )
            eval_runs.append(eval_run)
            run_ids.append(eval_run.run_id)
            test_db.create_eval_run(eval_run)

        # Verify they exist
        for run_id in run_ids:
            eval_run = test_db.get_eval_run(run_id, deserialize=True)
            assert eval_run is not None

        # Delete first 2
        test_db.delete_eval_runs(run_ids[:2])

        # Verify deletions
        assert test_db.get_eval_run(run_ids[0], deserialize=True) is None
        assert test_db.get_eval_run(run_ids[1], deserialize=True) is None
        assert test_db.get_eval_run(run_ids[2], deserialize=True) is not None

    def test_get_eval_runs_no_filters(self, test_db: PostgresDb):
        """Test getting all eval runs without filters"""
        # Create multiple eval runs
        eval_runs = []
        for i in range(3):
            eval_run = EvalRunRecord(
                run_id=f"test_eval_run_{i}",
                agent_id=f"test_agent_{i}",
                eval_type=EvalType.ACCURACY,
                eval_data={"score": 0.8 + (i * 0.05)},
                name=f"Test Eval {i}",
            )
            eval_runs.append(eval_run)
            test_db.create_eval_run(eval_run)

        result = test_db.get_eval_runs(deserialize=True)

        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(run, EvalRunRecord) for run in result)

    def test_get_eval_runs_with_agent_filter(
        self, test_db: PostgresDb, sample_eval_run_agent: EvalRunRecord, sample_eval_run_team: EvalRunRecord
    ):
        """Test getting eval runs filtered by agent_id"""
        test_db.create_eval_run(sample_eval_run_agent)
        test_db.create_eval_run(sample_eval_run_team)

        result = test_db.get_eval_runs(agent_id="test_agent_1", deserialize=True)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].agent_id == "test_agent_1"

    def test_get_eval_runs_with_team_filter(
        self, test_db: PostgresDb, sample_eval_run_agent: EvalRunRecord, sample_eval_run_team: EvalRunRecord
    ):
        """Test getting eval runs filtered by team_id"""
        test_db.create_eval_run(sample_eval_run_agent)
        test_db.create_eval_run(sample_eval_run_team)

        result = test_db.get_eval_runs(team_id="test_team_1", deserialize=True)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].team_id == "test_team_1"

    def test_get_eval_runs_with_workflow_filter(self, test_db: PostgresDb, sample_eval_run_workflow: EvalRunRecord):
        """Test getting eval runs filtered by workflow_id"""
        test_db.create_eval_run(sample_eval_run_workflow)

        result = test_db.get_eval_runs(workflow_id="test_workflow_1", deserialize=True)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].workflow_id == "test_workflow_1"

    def test_get_eval_runs_with_model_filter(
        self, test_db: PostgresDb, sample_eval_run_agent: EvalRunRecord, sample_eval_run_team: EvalRunRecord
    ):
        """Test getting eval runs filtered by model_id"""
        test_db.create_eval_run(sample_eval_run_agent)
        test_db.create_eval_run(sample_eval_run_team)

        result = test_db.get_eval_runs(model_id="gpt-4", deserialize=True)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].model_id == "gpt-4"

    def test_get_eval_runs_with_eval_type_filter(
        self, test_db: PostgresDb, sample_eval_run_agent: EvalRunRecord, sample_eval_run_team: EvalRunRecord
    ):
        """Test getting eval runs filtered by eval_type"""
        test_db.create_eval_run(sample_eval_run_agent)
        test_db.create_eval_run(sample_eval_run_team)

        result = test_db.get_eval_runs(eval_type=[EvalType.ACCURACY], deserialize=True)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].eval_type == EvalType.ACCURACY

    def test_get_eval_runs_with_filter_type(
        self,
        test_db: PostgresDb,
        sample_eval_run_agent: EvalRunRecord,
        sample_eval_run_team: EvalRunRecord,
        sample_eval_run_workflow: EvalRunRecord,
    ):
        """Test getting eval runs filtered by component filter_type"""
        test_db.create_eval_run(sample_eval_run_agent)
        test_db.create_eval_run(sample_eval_run_team)
        test_db.create_eval_run(sample_eval_run_workflow)

        # Test AGENT filter
        agent_results = test_db.get_eval_runs(filter_type=EvalFilterType.AGENT, deserialize=True)
        assert len(agent_results) == 1
        assert agent_results[0].agent_id is not None

        # Test TEAM filter
        team_results = test_db.get_eval_runs(filter_type=EvalFilterType.TEAM, deserialize=True)
        assert len(team_results) == 1
        assert team_results[0].team_id is not None

        # Test WORKFLOW filter
        workflow_results = test_db.get_eval_runs(filter_type=EvalFilterType.WORKFLOW, deserialize=True)
        assert len(workflow_results) == 1
        assert workflow_results[0].workflow_id is not None

    def test_get_eval_runs_with_pagination(self, test_db: PostgresDb):
        """Test getting eval runs with pagination"""
        # Create multiple eval runs
        for i in range(5):
            eval_run = EvalRunRecord(
                run_id=f"test_eval_run_{i}",
                agent_id=f"test_agent_{i}",
                eval_type=EvalType.ACCURACY,
                eval_data={"score": 0.8 + (i * 0.05)},
                name=f"Test Eval {i}",
            )
            test_db.create_eval_run(eval_run)

        # Test pagination
        page1 = test_db.get_eval_runs(limit=2, page=1, deserialize=True)
        assert isinstance(page1, list)
        assert len(page1) == 2

        page2 = test_db.get_eval_runs(limit=2, page=2, deserialize=True)
        assert isinstance(page2, list)
        assert len(page2) == 2

        # Verify no overlap
        page1_ids = {run.run_id for run in page1}
        page2_ids = {run.run_id for run in page2}
        assert len(page1_ids & page2_ids) == 0

    def test_get_eval_runs_with_sorting(self, test_db: PostgresDb):
        """Test getting eval runs with sorting"""
        # Create eval runs with different timestamps by spacing them out
        eval_runs = []
        for i in range(3):
            eval_run = EvalRunRecord(
                run_id=f"test_eval_run_{i}",
                agent_id=f"test_agent_{i}",
                eval_type=EvalType.ACCURACY,
                eval_data={"score": 0.8 + (i * 0.05)},
                name=f"Test Eval {i}",
            )
            eval_runs.append(eval_run)
            test_db.create_eval_run(eval_run)
            time.sleep(0.1)  # Small delay to ensure different timestamps

        # Test default sorting (created_at desc)
        results = test_db.get_eval_runs(deserialize=True)
        assert isinstance(results, list)
        assert len(results) == 3

        # Test explicit sorting by run_id ascending
        results_asc = test_db.get_eval_runs(sort_by="run_id", sort_order="asc", deserialize=True)
        assert isinstance(results_asc, list)
        assert results_asc[0].run_id == "test_eval_run_0"
        assert results_asc[1].run_id == "test_eval_run_1"
        assert results_asc[2].run_id == "test_eval_run_2"

    def test_get_eval_runs_without_deserialization(self, test_db: PostgresDb, sample_eval_run_agent: EvalRunRecord):
        """Test getting eval runs without deserialization"""
        test_db.create_eval_run(sample_eval_run_agent)

        result, total_count = test_db.get_eval_runs(deserialize=False)

        assert isinstance(result, list)
        assert len(result) == 1
        # result[0] is a RowMapping object, which behaves like a dict but isn't exactly a dict
        assert result[0]["run_id"] == sample_eval_run_agent.run_id
        assert total_count == 1

    def test_rename_eval_run_with_deserialization(self, test_db: PostgresDb, sample_eval_run_agent: EvalRunRecord):
        """Test renaming an eval run with deserialization"""
        test_db.create_eval_run(sample_eval_run_agent)

        new_name = "Renamed Eval Run"
        result = test_db.rename_eval_run(sample_eval_run_agent.run_id, new_name, deserialize=True)

        assert result is not None
        assert isinstance(result, EvalRunRecord)
        assert result.name == new_name
        assert result.run_id == sample_eval_run_agent.run_id

    def test_rename_eval_run_without_deserialization(self, test_db: PostgresDb, sample_eval_run_agent: EvalRunRecord):
        """Test renaming an eval run without deserialization"""
        test_db.create_eval_run(sample_eval_run_agent)

        new_name = "Renamed Eval Run Dict"
        result = test_db.rename_eval_run(sample_eval_run_agent.run_id, new_name, deserialize=False)

        assert result is not None
        # Due to the current implementation, when deserialize=False, rename_eval_run still returns a RowMapping
        # which behaves like a dict but has different access patterns
        if hasattr(result, "__getitem__"):  # RowMapping behavior
            assert result["name"] == new_name
            assert result["run_id"] == sample_eval_run_agent.run_id
        else:  # EvalRunRecord behavior (if implementation changes)
            assert result.name == new_name
            assert result.run_id == sample_eval_run_agent.run_id

    def test_rename_nonexistent_eval_run(self, test_db: PostgresDb):
        """Test renaming a nonexistent eval run returns None"""
        result = test_db.rename_eval_run("nonexistent_run_id", "New Name", deserialize=True)
        assert result is None

    def test_eval_table_creation_and_structure(self, test_db: PostgresDb):
        """Test that the eval table is created with the correct structure"""
        eval_table = test_db._get_table("evals")

        assert eval_table is not None
        assert eval_table.name == "test_agno_evals"
        assert eval_table.schema == test_db.db_schema

        # Verify essential columns exist
        column_names = [col.name for col in eval_table.columns]
        expected_columns = [
            "run_id",
            "agent_id",
            "team_id",
            "workflow_id",
            "model_id",
            "model_provider",
            "name",
            "evaluated_component_name",
            "eval_type",
            "eval_data",
            "created_at",
            "updated_at",
        ]
        for col in expected_columns:
            assert col in column_names, f"Missing column: {col}"

    def test_comprehensive_eval_run_fields(self, test_db: PostgresDb):
        """Test that all EvalRunRecord fields are properly handled"""
        comprehensive_eval = EvalRunRecord(
            run_id="comprehensive_eval_run",
            agent_id="comprehensive_agent",
            model_id="gpt-4-comprehensive",
            model_provider="openai",
            name="Comprehensive Eval Test",
            evaluated_component_name="Comprehensive Agent",
            eval_type=EvalType.RELIABILITY,
            eval_data={
                "primary_score": 0.95,
                "secondary_metrics": {"latency": 150.0, "throughput": 45.2, "error_rate": 0.02},
                "test_conditions": {"environment": "production", "duration_minutes": 60, "concurrent_users": 100},
                "detailed_results": [
                    {"test_id": "test_1", "score": 0.98, "category": "accuracy"},
                    {"test_id": "test_2", "score": 0.92, "category": "speed"},
                    {"test_id": "test_3", "score": 0.95, "category": "reliability"},
                ],
            },
        )

        # Create the eval run
        result = test_db.create_eval_run(comprehensive_eval)
        assert result is not None

        # Retrieve and verify all fields are preserved
        retrieved = test_db.get_eval_run(comprehensive_eval.run_id, deserialize=True)
        assert retrieved is not None
        assert isinstance(retrieved, EvalRunRecord)

        # Verify all fields
        assert retrieved.run_id == comprehensive_eval.run_id
        assert retrieved.agent_id == comprehensive_eval.agent_id
        assert retrieved.model_id == comprehensive_eval.model_id
        assert retrieved.model_provider == comprehensive_eval.model_provider
        assert retrieved.name == comprehensive_eval.name
        assert retrieved.evaluated_component_name == comprehensive_eval.evaluated_component_name
        assert retrieved.eval_type == comprehensive_eval.eval_type
        assert retrieved.eval_data == comprehensive_eval.eval_data


class TestPostgresDbKnowledge:
    """Tests for the knowledge-related methods of PostgresDb"""

    @pytest.fixture(autouse=True)
    def cleanup_knowledge(self, test_db: PostgresDb):
        """Fixture to clean-up knowledge rows after each test"""
        yield

        with test_db.Session() as session:
            try:
                knowledge_table = test_db._get_table("knowledge")
                session.execute(knowledge_table.delete())
                session.commit()
            except Exception:
                session.rollback()

    @pytest.fixture
    def sample_knowledge_document(self) -> KnowledgeRow:
        """Fixture returning a sample KnowledgeRow for a document"""
        return KnowledgeRow(
            id="test_knowledge_doc_1",
            name="API Documentation",
            description="Comprehensive API documentation for the platform",
            metadata={
                "format": "markdown",
                "language": "en",
                "version": "1.0.0",
                "tags": ["api", "documentation", "reference"],
                "author": "Engineering Team",
                "last_reviewed": "2024-01-15",
            },
            type="document",
            size=15420,
            linked_to=None,
            access_count=45,
            status="active",
            status_message="Document is up to date and ready for use",
            created_at=int(time.time()) - 3600,  # 1 hour ago
            updated_at=int(time.time()) - 1800,  # 30 minutes ago
        )

    @pytest.fixture
    def sample_knowledge_dataset(self) -> KnowledgeRow:
        """Fixture returning a sample KnowledgeRow for a dataset"""
        return KnowledgeRow(
            id="test_knowledge_dataset_1",
            name="Customer Support Conversations",
            description="Training dataset containing customer support chat conversations",
            metadata={
                "format": "json",
                "schema_version": "2.1",
                "total_conversations": 5000,
                "date_range": {"start": "2023-01-01", "end": "2023-12-31"},
                "categories": ["support", "billing", "technical", "general"],
                "data_quality": {"completeness": 0.98, "accuracy": 0.95, "consistency": 0.92},
            },
            type="dataset",
            size=2048000,  # ~2MB
            linked_to="training_pipeline_v2",
            access_count=12,
            status="processed",
            status_message="Dataset has been processed and is ready for training",
            created_at=int(time.time()) - 7200,  # 2 hours ago
            updated_at=int(time.time()) - 3600,  # 1 hour ago
        )

    @pytest.fixture
    def sample_knowledge_model(self) -> KnowledgeRow:
        """Fixture returning a sample KnowledgeRow for a model"""
        return KnowledgeRow(
            id="test_knowledge_model_1",
            name="Text Classification Model v3.2",
            description="Fine-tuned BERT model for classifying customer support tickets",
            metadata={
                "model_type": "bert-base-uncased",
                "framework": "transformers",
                "training_data": "customer_support_conversations",
                "performance_metrics": {"accuracy": 0.94, "precision": 0.92, "recall": 0.91, "f1_score": 0.915},
                "hyperparameters": {"learning_rate": 2e-5, "batch_size": 32, "epochs": 10},
                "deployment_info": {
                    "environment": "production",
                    "endpoint": "https://api.example.com/classify",
                    "version": "3.2",
                },
            },
            type="model",
            size=440000000,  # ~440MB
            linked_to="classification_service",
            access_count=234,
            status="deployed",
            status_message="Model is deployed and serving predictions",
            created_at=int(time.time()) - 86400,  # 1 day ago
            updated_at=int(time.time()) - 7200,  # 2 hours ago
        )

    def test_upsert_knowledge_content_document(self, test_db: PostgresDb, sample_knowledge_document: KnowledgeRow):
        """Test upserting a knowledge document"""
        result = test_db.upsert_knowledge_content(sample_knowledge_document)

        assert result is not None
        assert isinstance(result, KnowledgeRow)
        assert result.id == sample_knowledge_document.id
        assert result.name == sample_knowledge_document.name
        assert result.description == sample_knowledge_document.description
        assert result.type == sample_knowledge_document.type
        assert result.metadata == sample_knowledge_document.metadata
        assert result.size == sample_knowledge_document.size

    def test_upsert_knowledge_content_dataset(self, test_db: PostgresDb, sample_knowledge_dataset: KnowledgeRow):
        """Test upserting a knowledge dataset"""
        result = test_db.upsert_knowledge_content(sample_knowledge_dataset)

        assert result is not None
        assert isinstance(result, KnowledgeRow)
        assert result.id == sample_knowledge_dataset.id
        assert result.name == sample_knowledge_dataset.name
        assert result.type == sample_knowledge_dataset.type
        assert result.linked_to == sample_knowledge_dataset.linked_to

    def test_upsert_knowledge_content_model(self, test_db: PostgresDb, sample_knowledge_model: KnowledgeRow):
        """Test upserting a knowledge model"""
        result = test_db.upsert_knowledge_content(sample_knowledge_model)

        assert result is not None
        assert isinstance(result, KnowledgeRow)
        assert result.id == sample_knowledge_model.id
        assert result.name == sample_knowledge_model.name
        assert result.type == sample_knowledge_model.type
        assert result.status == sample_knowledge_model.status

    def test_upsert_knowledge_content_update(self, test_db: PostgresDb, sample_knowledge_document: KnowledgeRow):
        """Test updating existing knowledge content"""
        # Insert initial content
        test_db.upsert_knowledge_content(sample_knowledge_document)

        # Update the content
        sample_knowledge_document.description = "Updated API documentation with new endpoints"
        sample_knowledge_document.access_count = 50
        sample_knowledge_document.status = "updated"

        result = test_db.upsert_knowledge_content(sample_knowledge_document)

        assert result is not None
        assert result.description == "Updated API documentation with new endpoints"
        assert result.access_count == 50
        assert result.status == "updated"

    def test_get_knowledge_content_by_id(self, test_db: PostgresDb, sample_knowledge_document: KnowledgeRow):
        """Test getting knowledge content by ID"""
        test_db.upsert_knowledge_content(sample_knowledge_document)

        result = test_db.get_knowledge_content(sample_knowledge_document.id)  # type: ignore

        assert result is not None
        assert isinstance(result, KnowledgeRow)
        assert result.id == sample_knowledge_document.id
        assert result.name == sample_knowledge_document.name
        assert result.description == sample_knowledge_document.description
        assert result.metadata == sample_knowledge_document.metadata

    def test_get_nonexistent_knowledge_content(self, test_db: PostgresDb):
        """Test getting nonexistent knowledge content returns None"""
        result = test_db.get_knowledge_content("nonexistent_id")
        assert result is None

    def test_get_knowledge_contents_no_pagination(self, test_db: PostgresDb):
        """Test getting all knowledge contents without pagination"""
        # Create multiple knowledge rows
        knowledge_rows = []
        for i in range(3):
            knowledge_row = KnowledgeRow(
                id=f"test_knowledge_{i}",
                name=f"Test Knowledge {i}",
                description=f"Description for test knowledge {i}",
                type="document",
                size=1000 + (i * 100),
                access_count=i * 5,
                status="active",
            )
            knowledge_rows.append(knowledge_row)
            test_db.upsert_knowledge_content(knowledge_row)

        result, total_count = test_db.get_knowledge_contents()

        assert isinstance(result, list)
        assert len(result) == 3
        assert total_count == 3
        assert all(isinstance(row, KnowledgeRow) for row in result)

    def test_get_knowledge_contents_with_pagination(self, test_db: PostgresDb):
        """Test getting knowledge contents with pagination"""
        # Create multiple knowledge rows
        for i in range(5):
            knowledge_row = KnowledgeRow(
                id=f"test_knowledge_page_{i}",
                name=f"Test Knowledge Page {i}",
                description=f"Description for test knowledge page {i}",
                type="document",
                size=1000 + (i * 100),
                access_count=i * 2,
                status="active",
            )
            test_db.upsert_knowledge_content(knowledge_row)

        # Test pagination
        page1, total_count = test_db.get_knowledge_contents(limit=2, page=1)
        assert len(page1) == 2
        assert total_count == 5

        page2, _ = test_db.get_knowledge_contents(limit=2, page=2)
        assert len(page2) == 2

        # Verify no overlap
        page1_ids = {row.id for row in page1}
        page2_ids = {row.id for row in page2}
        assert len(page1_ids & page2_ids) == 0

    def test_get_knowledge_contents_with_sorting(self, test_db: PostgresDb):
        """Test getting knowledge contents with sorting"""
        # Create knowledge rows with different sizes for sorting
        knowledge_rows = []
        sizes = [5000, 1000, 3000]
        for i, size in enumerate(sizes):
            knowledge_row = KnowledgeRow(
                id=f"test_knowledge_sort_{i}",
                name=f"Test Knowledge Sort {i}",
                description=f"Description for sorting test {i}",
                type="document",
                size=size,
                access_count=i * 3,
                status="active",
            )
            knowledge_rows.append(knowledge_row)
            test_db.upsert_knowledge_content(knowledge_row)
            time.sleep(0.1)  # Small delay for created_at timestamps

        # Test sorting by size ascending
        results_asc, _ = test_db.get_knowledge_contents(sort_by="size", sort_order="asc")
        assert len(results_asc) == 3
        assert results_asc[0].size == 1000
        assert results_asc[1].size == 3000
        assert results_asc[2].size == 5000

    def test_delete_knowledge_content(self, test_db: PostgresDb, sample_knowledge_document: KnowledgeRow):
        """Test deleting knowledge content"""
        test_db.upsert_knowledge_content(sample_knowledge_document)

        # Verify it exists
        knowledge = test_db.get_knowledge_content(sample_knowledge_document.id)  # type: ignore
        assert knowledge is not None

        # Delete it
        test_db.delete_knowledge_content(sample_knowledge_document.id)  # type: ignore

        # Verify it's gone
        knowledge = test_db.get_knowledge_content(sample_knowledge_document.id)  # type: ignore
        assert knowledge is None

    def test_delete_nonexistent_knowledge_content(self, test_db: PostgresDb):
        """Test deleting nonexistent knowledge content"""
        # Should not raise an exception
        test_db.delete_knowledge_content("nonexistent_id")

    def test_knowledge_table_creation_and_structure(self, test_db: PostgresDb):
        """Test that the knowledge table is created with the correct structure"""
        knowledge_table = test_db._get_table("knowledge")

        assert knowledge_table is not None
        assert knowledge_table.name == "test_agno_knowledge"
        assert knowledge_table.schema == test_db.db_schema

        # Verify essential columns exist
        column_names = [col.name for col in knowledge_table.columns]
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

    def test_comprehensive_knowledge_row_fields(self, test_db: PostgresDb):
        """Test that all KnowledgeRow fields are properly handled"""
        comprehensive_knowledge = KnowledgeRow(
            id="comprehensive_knowledge_test",
            name="Comprehensive Knowledge Test",
            description="A comprehensive knowledge row to test all field handling",
            metadata={
                "comprehensive": True,
                "nested_data": {
                    "level1": {"level2": {"data": "deeply nested value", "numbers": [1, 2, 3, 4, 5], "boolean": True}}
                },
                "arrays": ["item1", "item2", "item3"],
                "performance_data": {
                    "metrics": {"accuracy": 0.98, "precision": 0.97, "recall": 0.96, "f1": 0.965},
                    "benchmarks": [
                        {"name": "test1", "score": 95.5},
                        {"name": "test2", "score": 98.2},
                        {"name": "test3", "score": 92.8},
                    ],
                },
            },
            type="comprehensive_test",
            size=1234567,
            linked_to="related_comprehensive_item",
            access_count=999,
            status="comprehensive_active",
            status_message="All fields are populated and being tested comprehensively",
            created_at=int(time.time()) - 86400,
            updated_at=int(time.time()) - 3600,
        )

        # Upsert the comprehensive knowledge
        result = test_db.upsert_knowledge_content(comprehensive_knowledge)
        assert result is not None

        # Retrieve and verify all fields are preserved
        retrieved = test_db.get_knowledge_content(comprehensive_knowledge.id)  # type: ignore
        assert retrieved is not None
        assert isinstance(retrieved, KnowledgeRow)

        # Verify all fields
        assert retrieved.id == comprehensive_knowledge.id
        assert retrieved.name == comprehensive_knowledge.name
        assert retrieved.description == comprehensive_knowledge.description
        assert retrieved.metadata == comprehensive_knowledge.metadata
        assert retrieved.type == comprehensive_knowledge.type
        assert retrieved.size == comprehensive_knowledge.size
        assert retrieved.linked_to == comprehensive_knowledge.linked_to
        assert retrieved.access_count == comprehensive_knowledge.access_count
        assert retrieved.status == comprehensive_knowledge.status
        assert retrieved.status_message == comprehensive_knowledge.status_message
        assert retrieved.created_at == comprehensive_knowledge.created_at
        assert retrieved.updated_at == comprehensive_knowledge.updated_at

    def test_knowledge_with_auto_generated_id(self, test_db: PostgresDb):
        """Test knowledge row with auto-generated ID"""
        knowledge_without_id = KnowledgeRow(
            name="Auto ID Knowledge",
            description="Knowledge row that should get an auto-generated ID",
            type="auto_test",
            size=500,
            status="active",
        )

        # The ID should be auto-generated by the model validator
        assert knowledge_without_id.id is not None
        assert len(knowledge_without_id.id) > 0

        result = test_db.upsert_knowledge_content(knowledge_without_id)
        assert result is not None
        assert result.id == knowledge_without_id.id

    def test_knowledge_with_none_optional_fields(self, test_db: PostgresDb):
        """Test knowledge row with minimal required fields and None optional fields"""
        minimal_knowledge = KnowledgeRow(
            id="minimal_knowledge_test",
            name="Minimal Knowledge",
            description="Knowledge with minimal fields",
            metadata=None,
            type=None,
            size=None,
            linked_to=None,
            access_count=None,
            status=None,
            status_message=None,
            created_at=None,
            updated_at=None,
        )

        result = test_db.upsert_knowledge_content(minimal_knowledge)
        assert result is not None
        assert result.name == "Minimal Knowledge"
        assert result.description == "Knowledge with minimal fields"

        # Retrieve and verify None fields are handled properly
        retrieved = test_db.get_knowledge_content(minimal_knowledge.id)  # type: ignore
        assert retrieved is not None
        assert retrieved.name == "Minimal Knowledge"
