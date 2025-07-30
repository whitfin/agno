"""Integration tests for the SqliteDb class"""

import tempfile
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Generator, List

import pytest

from agno.db.base import SessionType
from agno.db.sqlite.sqlite import SqliteDb
from agno.db.schemas.evals import EvalFilterType, EvalRunRecord, EvalType
from agno.db.schemas.knowledge import KnowledgeRow
from agno.db.schemas.memory import UserMemory
from agno.run.base import RunStatus
from agno.run.response import RunResponse
from agno.run.team import TeamRunResponse
from agno.session.agent import AgentSession
from agno.session.summary import SessionSummary
from agno.session.team import TeamSession


@pytest.fixture(scope="session")
def temp_db_file():
    """Create a temporary SQLite database file"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
        temp_path = temp_file.name
        
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture(scope="class")
def test_db(temp_db_file) -> Generator[SqliteDb, None, None]:
    """SqliteDb instance to be used across all tests"""
    db = SqliteDb(
        db_file=temp_db_file,
        session_table="test_agno_sessions",
        memory_table="test_agno_memories",
        metrics_table="test_agno_metrics",
        eval_table="test_agno_evals",
        knowledge_table="test_agno_knowledge",
    )

    # Force table creation by accessing the sessions table
    db._get_table("sessions")

    yield db

    # Cleanup is handled by temp_db_file fixture


class TestSqliteDbInfrastructure:
    """Tests for the infrastructure-related methods of SqliteDb"""

    def test_initialization_with_db_file(self, temp_db_file):
        db = SqliteDb(db_file=temp_db_file)

        assert db.db_file == temp_db_file
        assert db.db_engine is not None
        assert db.Session is not None
        assert db.session_table_name == "agno_sessions"

    def test_initialization_with_custom_table_names(self, temp_db_file):
        custom_session_table = "custom_sessions"
        db = SqliteDb(db_file=temp_db_file, session_table=custom_session_table)

        assert db.session_table_name == custom_session_table

    def test_initialization_creates_file(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=True) as temp_file:
            temp_path = temp_file.name
        
        # File should not exist initially
        assert not Path(temp_path).exists()
        
        db = SqliteDb(db_file=temp_path)
        
        # File should be created after initialization
        assert Path(temp_path).exists()
        
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)

    def test_create_table(self, test_db: SqliteDb):
        """Ensure the _create_table method creates the table correctly"""
        from sqlalchemy.schema import Table
        
        table = test_db._create_table(
            table_name="test_agno_sessions", table_type="sessions"
        )

        # Verify the Table object
        assert isinstance(table, Table)
        assert table.name == "test_agno_sessions"

        # Verify the table was created
        with test_db.Session() as session:
            result = session.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='test_agno_sessions'"
            )
            assert result.fetchone() is not None

    def test_get_table(self, test_db: SqliteDb):
        """Ensure the _get_table method returns and cache results as expected"""
        from sqlalchemy.schema import Table
        
        table = test_db._get_table("sessions")
        assert isinstance(table, Table)
        assert table.name == "test_agno_sessions"

        # Verify table is cached (second call returns same object)
        table2 = test_db._get_table("sessions")
        assert table is table2

    def test_get_table_all_mappings(self, test_db: SqliteDb):
        """Ensure the _get_table method returns the correct table for all mappings"""
        from sqlalchemy.schema import Table
        
        # Eval table
        table = test_db._get_table("evals")
        assert isinstance(table, Table)
        assert table.name == "test_agno_evals"

        # Knowledge table
        table = test_db._get_table("knowledge")
        assert isinstance(table, Table)
        assert table.name == "test_agno_knowledge"

        # Memory table
        table = test_db._get_table("memories")
        assert isinstance(table, Table)
        assert table.name == "test_agno_memories"

        # Metrics table
        table = test_db._get_table("metrics")
        assert isinstance(table, Table)
        assert table.name == "test_agno_metrics"

    def test_get_table_invalid_type(self, test_db: SqliteDb):
        """Ensure _get_table raises for invalid table types"""
        with pytest.raises(ValueError, match="Unknown table type: fake-type"):
            test_db._get_table("fake-type")


class TestSqliteDbSession:
    """Tests for session-related operations in SqliteDb"""

    @pytest.fixture(autouse=True)
    def cleanup_sessions(self, test_db: SqliteDb):
        yield
        table = test_db._get_table("sessions")
        with test_db.Session() as session:
            session.execute(table.delete())
            session.commit()

    @pytest.fixture
    def sample_agent_session(self) -> AgentSession:
        return AgentSession(
            user_id="test_user_1",
            session_id="test_agent_session_1",
            name="Test Agent Session",
            title="Agent Test",
            summary=SessionSummary(content="Test summary"),
            session_data={"key": "value"},
            agent_id="test_agent_1",
            agent_name="Test Agent",
            model="gpt-4",
        )

    @pytest.fixture
    def sample_team_session(self) -> TeamSession:
        return TeamSession(
            user_id="test_user_2",
            session_id="test_team_session_1",
            name="Test Team Session",
            title="Team Test",
            summary=SessionSummary(content="Team test summary"),
            session_data={"team_key": "team_value"},
            team_id="test_team_1",
            team_name="Test Team",
        )

    def test_insert_session(self, test_db: SqliteDb, sample_agent_session: AgentSession):
        """Test basic session insertion"""
        test_db.upsert_session(sample_agent_session)

        table = test_db._get_table("sessions")
        with test_db.Session() as session:
            result = session.execute(
                table.select().where(table.c.session_id == "test_agent_session_1")
            ).fetchone()
            assert result is not None
            assert result.user_id == "test_user_1"
            assert result.agent_id == "test_agent_1"

    def test_upsert_session_agent(self, test_db: SqliteDb, sample_agent_session: AgentSession):
        """Test upserting agent session"""
        test_db.upsert_session(sample_agent_session)

        retrieved = test_db.get_session_by_id("test_agent_session_1")
        assert retrieved is not None
        assert isinstance(retrieved, AgentSession)
        assert retrieved.session_id == "test_agent_session_1"
        assert retrieved.user_id == "test_user_1"
        assert retrieved.agent_id == "test_agent_1"

    def test_upsert_session_team(self, test_db: SqliteDb, sample_team_session: TeamSession):
        """Test upserting team session"""
        test_db.upsert_session(sample_team_session)

        retrieved = test_db.get_session_by_id("test_team_session_1")
        assert retrieved is not None
        assert isinstance(retrieved, TeamSession)
        assert retrieved.session_id == "test_team_session_1"
        assert retrieved.user_id == "test_user_2"
        assert retrieved.team_id == "test_team_1"

    def test_update_session(self, test_db: SqliteDb, sample_agent_session: AgentSession):
        """Test updating existing session"""
        test_db.upsert_session(sample_agent_session)

        sample_agent_session.name = "Updated Agent Session"
        sample_agent_session.session_data = {"updated_key": "updated_value"}
        test_db.upsert_session(sample_agent_session)

        retrieved = test_db.get_session_by_id("test_agent_session_1")
        assert retrieved is not None
        assert retrieved.name == "Updated Agent Session"
        assert retrieved.session_data == {"updated_key": "updated_value"}

    def test_get_session_by_id_not_found(self, test_db: SqliteDb):
        """Test retrieving non-existent session"""
        result = test_db.get_session_by_id("non_existent_session")
        assert result is None

    def test_get_session_without_deserialization(self, test_db: SqliteDb, sample_agent_session: AgentSession):
        """Test retrieving session as dict without deserialization"""
        test_db.upsert_session(sample_agent_session)

        result = test_db.get_session_by_id("test_agent_session_1", include_records=False)
        assert result is not None
        assert isinstance(result, dict)
        assert result["session_id"] == "test_agent_session_1"
        assert result["user_id"] == "test_user_1"

    def test_delete_session(self, test_db: SqliteDb, sample_agent_session: AgentSession):
        """Test session deletion"""
        test_db.upsert_session(sample_agent_session)

        retrieved = test_db.get_session_by_id("test_agent_session_1")
        assert retrieved is not None

        test_db.delete_session("test_agent_session_1")

        deleted = test_db.get_session_by_id("test_agent_session_1")
        assert deleted is None

    def test_get_sessions_with_user_filter(self, test_db: SqliteDb, sample_agent_session: AgentSession, sample_team_session: TeamSession):
        """Test retrieving sessions filtered by user"""
        test_db.upsert_session(sample_agent_session)
        test_db.upsert_session(sample_team_session)

        sessions = test_db.get_sessions(user_id="test_user_1")
        assert len(sessions) == 1
        assert sessions[0].session_id == "test_agent_session_1"

    def test_get_sessions_with_session_type_filter(self, test_db: SqliteDb, sample_agent_session: AgentSession, sample_team_session: TeamSession):
        """Test retrieving sessions filtered by session type"""
        test_db.upsert_session(sample_agent_session)
        test_db.upsert_session(sample_team_session)

        agent_sessions = test_db.get_sessions(session_type=SessionType.agent)
        assert len(agent_sessions) == 1
        assert isinstance(agent_sessions[0], AgentSession)

        team_sessions = test_db.get_sessions(session_type=SessionType.team)
        assert len(team_sessions) == 1
        assert isinstance(team_sessions[0], TeamSession)

    def test_get_sessions_no_filters(self, test_db: SqliteDb, sample_agent_session: AgentSession, sample_team_session: TeamSession):
        """Test retrieving all sessions without filters"""
        test_db.upsert_session(sample_agent_session)
        test_db.upsert_session(sample_team_session)

        sessions = test_db.get_sessions()
        assert len(sessions) == 2

    def test_get_sessions_with_limit(self, test_db: SqliteDb, sample_agent_session: AgentSession, sample_team_session: TeamSession):
        """Test retrieving sessions with limit"""
        test_db.upsert_session(sample_agent_session)
        test_db.upsert_session(sample_team_session)

        sessions = test_db.get_sessions(limit=1)
        assert len(sessions) == 1


class TestSqliteDbMemory:
    """Tests for memory-related operations in SqliteDb"""

    @pytest.fixture(autouse=True)
    def cleanup_memories(self, test_db: SqliteDb):
        yield
        table = test_db._get_table("memories")
        with test_db.Session() as session:
            session.execute(table.delete())
            session.commit()

    @pytest.fixture
    def sample_memory(self) -> UserMemory:
        return UserMemory(
            id="test_memory_1",
            user_id="test_user_1",
            memory="Test memory content",
            memory_data={"key": "value"},
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )

    def test_upsert_memory(self, test_db: SqliteDb, sample_memory: UserMemory):
        """Test upserting memory"""
        test_db.upsert_memory(sample_memory)

        retrieved = test_db.get_memory_by_id("test_memory_1")
        assert retrieved is not None
        assert retrieved.id == "test_memory_1"
        assert retrieved.user_id == "test_user_1"
        assert retrieved.memory == "Test memory content"

    def test_get_memory_by_id_not_found(self, test_db: SqliteDb):
        """Test retrieving non-existent memory"""
        result = test_db.get_memory_by_id("non_existent_memory")
        assert result is None

    def test_delete_memory(self, test_db: SqliteDb, sample_memory: UserMemory):
        """Test memory deletion"""
        test_db.upsert_memory(sample_memory)

        retrieved = test_db.get_memory_by_id("test_memory_1")
        assert retrieved is not None

        test_db.delete_memory("test_memory_1")

        deleted = test_db.get_memory_by_id("test_memory_1")
        assert deleted is None

    def test_get_memories_with_user_filter(self, test_db: SqliteDb):
        """Test retrieving memories filtered by user"""
        memory1 = UserMemory(
            id="test_memory_1",
            user_id="test_user_1",
            memory="Memory 1",
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )
        memory2 = UserMemory(
            id="test_memory_2",
            user_id="test_user_2",
            memory="Memory 2",
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )

        test_db.upsert_memory(memory1)
        test_db.upsert_memory(memory2)

        memories = test_db.get_memories(user_id="test_user_1")
        assert len(memories) == 1
        assert memories[0].id == "test_memory_1"


class TestSqliteDbMetrics:
    """Tests for metrics-related operations in SqliteDb"""

    @pytest.fixture(autouse=True)
    def cleanup_metrics(self, test_db: SqliteDb):
        yield
        table = test_db._get_table("metrics")
        with test_db.Session() as session:
            session.execute(table.delete())
            session.commit()

    def test_calculate_metrics_basic(self, test_db: SqliteDb):
        """Test basic metrics calculation"""
        # Create sample session for metrics calculation
        session = AgentSession(
            user_id="test_user_1",
            session_id="test_session_1",
            name="Test Session",
            agent_id="test_agent_1",
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )
        test_db.upsert_session(session)

        # Calculate metrics
        test_db.calculate_metrics()

        # Verify metrics were created
        table = test_db._get_table("metrics")
        with test_db.Session() as session:
            result = session.execute(table.select()).fetchall()
            assert len(result) > 0


class TestSqliteDbEvals:
    """Tests for evaluation-related operations in SqliteDb"""

    @pytest.fixture(autouse=True)
    def cleanup_evals(self, test_db: SqliteDb):
        yield
        table = test_db._get_table("evals")
        with test_db.Session() as session:
            session.execute(table.delete())
            session.commit()

    @pytest.fixture
    def sample_eval_record(self) -> EvalRunRecord:
        return EvalRunRecord(
            id="test_eval_1",
            eval_id="eval_1",
            eval_type=EvalType.agent,
            eval_name="Test Eval",
            run_id="run_1",
            run_name="Test Run",
            user_id="test_user_1",
            agent_id="test_agent_1",
            session_id="test_session_1",
            thread_id="thread_1",
            run_data={"score": 0.85},
            eval_data={"accuracy": 0.9},
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )

    def test_upsert_eval_record(self, test_db: SqliteDb, sample_eval_record: EvalRunRecord):
        """Test upserting evaluation record"""
        test_db.upsert_eval_record(sample_eval_record)

        retrieved = test_db.get_eval_record_by_id("test_eval_1")
        assert retrieved is not None
        assert retrieved.id == "test_eval_1"
        assert retrieved.eval_id == "eval_1"
        assert retrieved.eval_type == EvalType.agent

    def test_get_eval_record_by_id_not_found(self, test_db: SqliteDb):
        """Test retrieving non-existent evaluation record"""
        result = test_db.get_eval_record_by_id("non_existent_eval")
        assert result is None

    def test_delete_eval_record(self, test_db: SqliteDb, sample_eval_record: EvalRunRecord):
        """Test evaluation record deletion"""
        test_db.upsert_eval_record(sample_eval_record)

        retrieved = test_db.get_eval_record_by_id("test_eval_1")
        assert retrieved is not None

        test_db.delete_eval_record("test_eval_1")

        deleted = test_db.get_eval_record_by_id("test_eval_1")
        assert deleted is None

    def test_get_eval_records_with_filters(self, test_db: SqliteDb, sample_eval_record: EvalRunRecord):
        """Test retrieving evaluation records with filters"""
        test_db.upsert_eval_record(sample_eval_record)

        records = test_db.get_eval_records(user_id="test_user_1")
        assert len(records) == 1
        assert records[0].id == "test_eval_1"

        records = test_db.get_eval_records(eval_type=EvalType.agent)
        assert len(records) == 1
        assert records[0].eval_type == EvalType.agent


class TestSqliteDbKnowledge:
    """Tests for knowledge-related operations in SqliteDb"""

    @pytest.fixture(autouse=True)
    def cleanup_knowledge(self, test_db: SqliteDb):
        yield
        table = test_db._get_table("knowledge")
        with test_db.Session() as session:
            session.execute(table.delete())
            session.commit()

    @pytest.fixture
    def sample_knowledge_row(self) -> KnowledgeRow:
        return KnowledgeRow(
            id="test_knowledge_1",
            name="Test Knowledge",
            description="Test knowledge description",
            type="document",
            size=1024,
            metadata={"key": "value"},
            access_count=5,
            status="active",
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )

    def test_upsert_knowledge_row(self, test_db: SqliteDb, sample_knowledge_row: KnowledgeRow):
        """Test upserting knowledge row"""
        test_db.upsert_knowledge_row(sample_knowledge_row)

        retrieved = test_db.get_knowledge_row_by_id("test_knowledge_1")
        assert retrieved is not None
        assert retrieved.id == "test_knowledge_1"
        assert retrieved.name == "Test Knowledge"
        assert retrieved.type == "document"

    def test_get_knowledge_row_by_id_not_found(self, test_db: SqliteDb):
        """Test retrieving non-existent knowledge row"""
        result = test_db.get_knowledge_row_by_id("non_existent_knowledge")
        assert result is None

    def test_delete_knowledge_row(self, test_db: SqliteDb, sample_knowledge_row: KnowledgeRow):
        """Test knowledge row deletion"""
        test_db.upsert_knowledge_row(sample_knowledge_row)

        retrieved = test_db.get_knowledge_row_by_id("test_knowledge_1")
        assert retrieved is not None

        test_db.delete_knowledge_row("test_knowledge_1")

        deleted = test_db.get_knowledge_row_by_id("test_knowledge_1")
        assert deleted is None

    def test_get_knowledge_rows_with_filters(self, test_db: SqliteDb, sample_knowledge_row: KnowledgeRow):
        """Test retrieving knowledge rows with filters"""
        test_db.upsert_knowledge_row(sample_knowledge_row)

        rows = test_db.get_knowledge_rows(type="document")
        assert len(rows) == 1
        assert rows[0].id == "test_knowledge_1"
        assert rows[0].type == "document"