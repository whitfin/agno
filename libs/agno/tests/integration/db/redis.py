"""Integration tests for the RedisDb class"""

import time
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Generator, List

import pytest

from agno.db.base import SessionType
from agno.db.redis.redis import RedisDb
from agno.db.schemas.evals import EvalFilterType, EvalRunRecord, EvalType
from agno.db.schemas.knowledge import KnowledgeRow
from agno.db.schemas.memory import UserMemory
from agno.run.base import RunStatus
from agno.run.response import RunResponse
from agno.run.team import TeamRunResponse
from agno.session.agent import AgentSession
from agno.session.summary import SessionSummary
from agno.session.team import TeamSession

# TODO: should use Redis container for testing
TEST_DB_URL = "redis://localhost:6379"


@pytest.fixture(scope="session")
def redis_client():
    """Handle the Redis client lifecycle"""
    try:
        from redis import Redis
    except ImportError:
        pytest.skip("redis not installed")
    
    client = Redis.from_url(TEST_DB_URL, decode_responses=True)
    
    yield client
    
    client.close()


@pytest.fixture(scope="class")
def test_db(redis_client) -> Generator[RedisDb, None, None]:
    """RedisDb instance to be used across all tests"""
    prefix = f"test_agno_{uuid.uuid4().hex[:8]}"
    db = RedisDb(
        redis_client=redis_client,
        db_prefix=prefix,
        session_table="test_agno_sessions",
        memory_table="test_agno_memories",
        metrics_table="test_agno_metrics",
        eval_table="test_agno_evals",
        knowledge_table="test_agno_knowledge",
    )

    yield db

    # Cleanup - delete all keys with test prefix
    try:
        pattern = f"{prefix}:*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
    except Exception:
        pass


class TestRedisDbInfrastructure:
    """Tests for the infrastructure-related methods of RedisDb"""

    def test_initialization_with_db_url(self):
        try:
            from redis import Redis
        except ImportError:
            pytest.skip("redis not installed")
            
        db = RedisDb(db_url=TEST_DB_URL)

        assert db.db_url == TEST_DB_URL
        assert db.redis_client is not None
        assert db.db_prefix == "agno"
        assert db.session_table_name == "agno_sessions"

    def test_initialization_with_client(self, redis_client):
        db = RedisDb(redis_client=redis_client)

        assert db.redis_client == redis_client
        assert db.db_url is None
        assert db.db_prefix == "agno"

    def test_initialization_with_custom_prefix_and_tables(self, redis_client):
        custom_prefix = "custom_prefix"
        custom_session_table = "custom_sessions"
        db = RedisDb(
            redis_client=redis_client,
            db_prefix=custom_prefix,
            session_table=custom_session_table
        )

        assert db.db_prefix == custom_prefix
        assert db.session_table_name == custom_session_table

    def test_initialization_requires_client_or_url(self):
        with pytest.raises(ValueError, match="One of db_url or redis_client must be provided"):
            RedisDb()

    def test_generate_redis_key(self, test_db: RedisDb):
        """Test Redis key generation"""
        from agno.db.redis.utils import generate_redis_key
        
        key = generate_redis_key(test_db.db_prefix, "sessions", "test_id")
        expected = f"{test_db.db_prefix}:sessions:test_id"
        assert key == expected

    def test_table_name_mappings(self, test_db: RedisDb):
        """Ensure table name mapping works for all types"""
        # Session table
        assert test_db.session_table_name is not None
        assert "sessions" in test_db.session_table_name

        # Memory table
        assert test_db.memory_table_name is not None
        assert "memories" in test_db.memory_table_name

        # Metrics table
        assert test_db.metrics_table_name is not None
        assert "metrics" in test_db.metrics_table_name

        # Eval table
        assert test_db.eval_table_name is not None
        assert "evals" in test_db.eval_table_name

        # Knowledge table
        assert test_db.knowledge_table_name is not None
        assert "knowledge" in test_db.knowledge_table_name


class TestRedisDbSession:
    """Tests for session-related operations in RedisDb"""

    @pytest.fixture(autouse=True)
    def cleanup_sessions(self, test_db: RedisDb):
        yield
        # Redis cleanup - delete all session keys
        try:
            pattern = f"{test_db.db_prefix}:{test_db.session_table_name}:*"
            keys = test_db.redis_client.keys(pattern)
            if keys:
                test_db.redis_client.delete(*keys)
        except Exception:
            pass

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

    def test_insert_session(self, test_db: RedisDb, sample_agent_session: AgentSession):
        """Test basic session insertion"""
        test_db.upsert_session(sample_agent_session)

        # Verify insertion in Redis
        from agno.db.redis.utils import generate_redis_key
        key = generate_redis_key(test_db.db_prefix, test_db.session_table_name, "test_agent_session_1")
        data = test_db.redis_client.hgetall(key)
        assert data is not None
        assert data["user_id"] == "test_user_1"
        assert data["agent_id"] == "test_agent_1"

    def test_upsert_session_agent(self, test_db: RedisDb, sample_agent_session: AgentSession):
        """Test upserting agent session"""
        test_db.upsert_session(sample_agent_session)

        retrieved = test_db.get_session_by_id("test_agent_session_1")
        assert retrieved is not None
        assert isinstance(retrieved, AgentSession)
        assert retrieved.session_id == "test_agent_session_1"
        assert retrieved.user_id == "test_user_1"
        assert retrieved.agent_id == "test_agent_1"

    def test_upsert_session_team(self, test_db: RedisDb, sample_team_session: TeamSession):
        """Test upserting team session"""
        test_db.upsert_session(sample_team_session)

        retrieved = test_db.get_session_by_id("test_team_session_1")
        assert retrieved is not None
        assert isinstance(retrieved, TeamSession)
        assert retrieved.session_id == "test_team_session_1"
        assert retrieved.user_id == "test_user_2"
        assert retrieved.team_id == "test_team_1"

    def test_update_session(self, test_db: RedisDb, sample_agent_session: AgentSession):
        """Test updating existing session"""
        test_db.upsert_session(sample_agent_session)

        sample_agent_session.name = "Updated Agent Session"
        sample_agent_session.session_data = {"updated_key": "updated_value"}
        test_db.upsert_session(sample_agent_session)

        retrieved = test_db.get_session_by_id("test_agent_session_1")
        assert retrieved is not None
        assert retrieved.name == "Updated Agent Session"
        assert retrieved.session_data == {"updated_key": "updated_value"}

    def test_get_session_by_id_not_found(self, test_db: RedisDb):
        """Test retrieving non-existent session"""
        result = test_db.get_session_by_id("non_existent_session")
        assert result is None

    def test_get_session_without_deserialization(self, test_db: RedisDb, sample_agent_session: AgentSession):
        """Test retrieving session as dict without deserialization"""
        test_db.upsert_session(sample_agent_session)

        result = test_db.get_session_by_id("test_agent_session_1", include_records=False)
        assert result is not None
        assert isinstance(result, dict)
        assert result["session_id"] == "test_agent_session_1"
        assert result["user_id"] == "test_user_1"

    def test_delete_session(self, test_db: RedisDb, sample_agent_session: AgentSession):
        """Test session deletion"""
        test_db.upsert_session(sample_agent_session)

        retrieved = test_db.get_session_by_id("test_agent_session_1")
        assert retrieved is not None

        test_db.delete_session("test_agent_session_1")

        deleted = test_db.get_session_by_id("test_agent_session_1")
        assert deleted is None

    def test_get_sessions_with_user_filter(self, test_db: RedisDb, sample_agent_session: AgentSession, sample_team_session: TeamSession):
        """Test retrieving sessions filtered by user"""
        test_db.upsert_session(sample_agent_session)
        test_db.upsert_session(sample_team_session)

        sessions = test_db.get_sessions(user_id="test_user_1")
        assert len(sessions) == 1
        assert sessions[0].session_id == "test_agent_session_1"

    def test_get_sessions_with_session_type_filter(self, test_db: RedisDb, sample_agent_session: AgentSession, sample_team_session: TeamSession):
        """Test retrieving sessions filtered by session type"""
        test_db.upsert_session(sample_agent_session)
        test_db.upsert_session(sample_team_session)

        agent_sessions = test_db.get_sessions(session_type=SessionType.agent)
        assert len(agent_sessions) == 1
        assert isinstance(agent_sessions[0], AgentSession)

        team_sessions = test_db.get_sessions(session_type=SessionType.team)
        assert len(team_sessions) == 1
        assert isinstance(team_sessions[0], TeamSession)

    def test_get_sessions_no_filters(self, test_db: RedisDb, sample_agent_session: AgentSession, sample_team_session: TeamSession):
        """Test retrieving all sessions without filters"""
        test_db.upsert_session(sample_agent_session)
        test_db.upsert_session(sample_team_session)

        sessions = test_db.get_sessions()
        assert len(sessions) == 2

    def test_get_sessions_with_limit(self, test_db: RedisDb, sample_agent_session: AgentSession, sample_team_session: TeamSession):
        """Test retrieving sessions with limit"""
        test_db.upsert_session(sample_agent_session)
        test_db.upsert_session(sample_team_session)

        sessions = test_db.get_sessions(limit=1)
        assert len(sessions) == 1


class TestRedisDbMemory:
    """Tests for memory-related operations in RedisDb"""

    @pytest.fixture(autouse=True)
    def cleanup_memories(self, test_db: RedisDb):
        yield
        # Redis cleanup
        try:
            pattern = f"{test_db.db_prefix}:{test_db.memory_table_name}:*"
            keys = test_db.redis_client.keys(pattern)
            if keys:
                test_db.redis_client.delete(*keys)
        except Exception:
            pass

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

    def test_upsert_memory(self, test_db: RedisDb, sample_memory: UserMemory):
        """Test upserting memory"""
        test_db.upsert_memory(sample_memory)

        retrieved = test_db.get_memory_by_id("test_memory_1")
        assert retrieved is not None
        assert retrieved.id == "test_memory_1"
        assert retrieved.user_id == "test_user_1"
        assert retrieved.memory == "Test memory content"

    def test_get_memory_by_id_not_found(self, test_db: RedisDb):
        """Test retrieving non-existent memory"""
        result = test_db.get_memory_by_id("non_existent_memory")
        assert result is None

    def test_delete_memory(self, test_db: RedisDb, sample_memory: UserMemory):
        """Test memory deletion"""
        test_db.upsert_memory(sample_memory)

        retrieved = test_db.get_memory_by_id("test_memory_1")
        assert retrieved is not None

        test_db.delete_memory("test_memory_1")

        deleted = test_db.get_memory_by_id("test_memory_1")
        assert deleted is None

    def test_get_memories_with_user_filter(self, test_db: RedisDb):
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


class TestRedisDbMetrics:
    """Tests for metrics-related operations in RedisDb"""

    @pytest.fixture(autouse=True)
    def cleanup_metrics(self, test_db: RedisDb):
        yield
        # Redis cleanup
        try:
            pattern = f"{test_db.db_prefix}:{test_db.metrics_table_name}:*"
            keys = test_db.redis_client.keys(pattern)
            if keys:
                test_db.redis_client.delete(*keys)
        except Exception:
            pass

    def test_calculate_metrics_basic(self, test_db: RedisDb):
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
        pattern = f"{test_db.db_prefix}:{test_db.metrics_table_name}:*"
        keys = test_db.redis_client.keys(pattern)
        assert len(keys) > 0


class TestRedisDbEvals:
    """Tests for evaluation-related operations in RedisDb"""

    @pytest.fixture(autouse=True)
    def cleanup_evals(self, test_db: RedisDb):
        yield
        # Redis cleanup
        try:
            pattern = f"{test_db.db_prefix}:{test_db.eval_table_name}:*"
            keys = test_db.redis_client.keys(pattern)
            if keys:
                test_db.redis_client.delete(*keys)
        except Exception:
            pass

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

    def test_upsert_eval_record(self, test_db: RedisDb, sample_eval_record: EvalRunRecord):
        """Test upserting evaluation record"""
        test_db.upsert_eval_record(sample_eval_record)

        retrieved = test_db.get_eval_record_by_id("test_eval_1")
        assert retrieved is not None
        assert retrieved.id == "test_eval_1"
        assert retrieved.eval_id == "eval_1"
        assert retrieved.eval_type == EvalType.agent

    def test_get_eval_record_by_id_not_found(self, test_db: RedisDb):
        """Test retrieving non-existent evaluation record"""
        result = test_db.get_eval_record_by_id("non_existent_eval")
        assert result is None

    def test_delete_eval_record(self, test_db: RedisDb, sample_eval_record: EvalRunRecord):
        """Test evaluation record deletion"""
        test_db.upsert_eval_record(sample_eval_record)

        retrieved = test_db.get_eval_record_by_id("test_eval_1")
        assert retrieved is not None

        test_db.delete_eval_record("test_eval_1")

        deleted = test_db.get_eval_record_by_id("test_eval_1")
        assert deleted is None

    def test_get_eval_records_with_filters(self, test_db: RedisDb, sample_eval_record: EvalRunRecord):
        """Test retrieving evaluation records with filters"""
        test_db.upsert_eval_record(sample_eval_record)

        records = test_db.get_eval_records(user_id="test_user_1")
        assert len(records) == 1
        assert records[0].id == "test_eval_1"

        records = test_db.get_eval_records(eval_type=EvalType.agent)
        assert len(records) == 1
        assert records[0].eval_type == EvalType.agent


class TestRedisDbKnowledge:
    """Tests for knowledge-related operations in RedisDb"""

    @pytest.fixture(autouse=True)
    def cleanup_knowledge(self, test_db: RedisDb):
        yield
        # Redis cleanup
        try:
            pattern = f"{test_db.db_prefix}:{test_db.knowledge_table_name}:*"
            keys = test_db.redis_client.keys(pattern)
            if keys:
                test_db.redis_client.delete(*keys)
        except Exception:
            pass

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

    def test_upsert_knowledge_row(self, test_db: RedisDb, sample_knowledge_row: KnowledgeRow):
        """Test upserting knowledge row"""
        test_db.upsert_knowledge_row(sample_knowledge_row)

        retrieved = test_db.get_knowledge_row_by_id("test_knowledge_1")
        assert retrieved is not None
        assert retrieved.id == "test_knowledge_1"
        assert retrieved.name == "Test Knowledge"
        assert retrieved.type == "document"

    def test_get_knowledge_row_by_id_not_found(self, test_db: RedisDb):
        """Test retrieving non-existent knowledge row"""
        result = test_db.get_knowledge_row_by_id("non_existent_knowledge")
        assert result is None

    def test_delete_knowledge_row(self, test_db: RedisDb, sample_knowledge_row: KnowledgeRow):
        """Test knowledge row deletion"""
        test_db.upsert_knowledge_row(sample_knowledge_row)

        retrieved = test_db.get_knowledge_row_by_id("test_knowledge_1")
        assert retrieved is not None

        test_db.delete_knowledge_row("test_knowledge_1")

        deleted = test_db.get_knowledge_row_by_id("test_knowledge_1")
        assert deleted is None

    def test_get_knowledge_rows_with_filters(self, test_db: RedisDb, sample_knowledge_row: KnowledgeRow):
        """Test retrieving knowledge rows with filters"""
        test_db.upsert_knowledge_row(sample_knowledge_row)

        rows = test_db.get_knowledge_rows(type="document")
        assert len(rows) == 1
        assert rows[0].id == "test_knowledge_1"
        assert rows[0].type == "document"