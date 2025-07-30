"""Integration tests for the DynamoDb class"""

import time
import uuid
from os import getenv
from typing import Generator

import pytest

from agno.db.base import SessionType
from agno.db.dynamo.dynamo import DynamoDb
from agno.db.dynamo.schemas import get_table_schema_definition
from agno.db.dynamo.utils import create_table_if_not_exists
from agno.db.schemas.evals import EvalRunRecord, EvalType
from agno.db.schemas.knowledge import KnowledgeRow
from agno.db.schemas.memory import UserMemory
from agno.session.agent import AgentSession
from agno.session.summary import SessionSummary
from agno.session.team import TeamSession

# TODO: should use localstack OR connect to an internally owned test DynamoDb setup
TEST_REGION = "us-east-1"


@pytest.fixture(scope="session")
def dynamo_client():
    """Handle the DynamoDB client lifecycle"""
    try:
        import boto3
    except ImportError:
        pytest.skip("boto3 not installed")

    # Necessary to setup the DynamoDB client
    assert TEST_REGION is not None
    assert getenv("AWS_ACCESS_KEY_ID") is not None
    assert getenv("AWS_SECRET_ACCESS_KEY") is not None

    session = boto3.Session(region_name=TEST_REGION)
    client = session.client("dynamodb")

    yield client


@pytest.fixture(scope="class")
def test_db(dynamo_client) -> Generator[DynamoDb, None, None]:
    """DynamoDb instance to be used across all tests"""
    prefix = f"test_agno_{uuid.uuid4().hex[:8]}"
    db = DynamoDb(
        db_client=dynamo_client,
        session_table=f"{prefix}_sessions",
        memory_table=f"{prefix}_memories",
        metrics_table=f"{prefix}_metrics",
        eval_table=f"{prefix}_evals",
        knowledge_table=f"{prefix}_knowledge",
    )

    # Create all tables
    create_table_if_not_exists(
        dynamodb_client=db.client,
        table_name=db.session_table_name,
        schema=get_table_schema_definition("sessions"),
    )
    create_table_if_not_exists(
        dynamodb_client=db.client,
        table_name=db.memory_table_name,
        schema=get_table_schema_definition("memories"),
    )
    create_table_if_not_exists(
        dynamodb_client=db.client,
        table_name=db.metrics_table_name,
        schema=get_table_schema_definition("metrics"),
    )
    create_table_if_not_exists(
        dynamodb_client=db.client,
        table_name=db.eval_table_name,
        schema=get_table_schema_definition("evals"),
    )
    create_table_if_not_exists(
        dynamodb_client=db.client,
        table_name=db.knowledge_table_name,
        schema=get_table_schema_definition("knowledge"),
    )

    yield db

    # Cleanup - delete tables
    try:
        for table_type in ["sessions", "memories", "metrics", "evals", "knowledge"]:
            table_name = getattr(db, f"{table_type[:-1]}_table_name", None)
            if table_name:
                dynamo_client.delete_table(TableName=table_name)
    except Exception:
        pass


class TestDynamoDbInfrastructure:
    """Tests for the infrastructure-related methods of DynamoDb"""

    def test_initialization_with_client(self, test_db):
        """Ensure we can initialize the DynamoDb instance passing a DynamoDB client"""

        assert test_db is not None

        # Asserting the tables exist, proving a sane initialization
        assert test_db._table_exists(test_db.session_table_name)
        assert test_db._table_exists(test_db.memory_table_name)
        assert test_db._table_exists(test_db.metrics_table_name)
        assert test_db._table_exists(test_db.eval_table_name)
        assert test_db._table_exists(test_db.knowledge_table_name)

    def test_initialization_with_custom_table_names(self, dynamo_client):
        """Ensure we can initialize the DynamoDb instance with custom table names"""
        custom_session_table = "custom_sessions"
        db = DynamoDb(db_client=dynamo_client, session_table=custom_session_table)

        assert db.session_table_name == custom_session_table

    def test_create_table_if_not_exists(self, test_db: DynamoDb):
        """Test table creation"""
        # Asserting the test_db fixture is there. Tables should be created.
        assert test_db is not None

        # Verify the sessions table exists and is active
        table_name = test_db.session_table_name
        response = test_db.client.describe_table(TableName=table_name)
        assert response["Table"]["TableStatus"] in ["ACTIVE", "CREATING"]

    def test_get_table_name_all_mappings(self, test_db: DynamoDb):
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


class TestDynamoDbSession:
    """Tests for session-related operations in DynamoDb"""

    @pytest.fixture(autouse=True)
    def cleanup_sessions(self, test_db: DynamoDb):
        yield
        # DynamoDB cleanup - scan and delete all items
        try:
            table_name = test_db.session_table_name
            response = test_db.db_client.scan(TableName=table_name)
            for item in response.get("Items", []):
                test_db.db_client.delete_item(TableName=table_name, Key={"id": item["id"]})
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

    def test_insert_session(self, test_db: DynamoDb, sample_agent_session: AgentSession):
        """Test basic session insertion"""
        test_db.upsert_session(sample_agent_session)

        # Verify insertion in DynamoDB
        response = test_db.db_client.get_item(
            TableName=test_db.session_table_name, Key={"id": {"S": "test_agent_session_1"}}
        )
        assert "Item" in response
        assert response["Item"]["user_id"]["S"] == "test_user_1"
        assert response["Item"]["agent_id"]["S"] == "test_agent_1"

    def test_upsert_session_agent(self, test_db: DynamoDb, sample_agent_session: AgentSession):
        """Test upserting agent session"""
        test_db.upsert_session(sample_agent_session)

        retrieved = test_db.get_session_by_id("test_agent_session_1")
        assert retrieved is not None
        assert isinstance(retrieved, AgentSession)
        assert retrieved.session_id == "test_agent_session_1"
        assert retrieved.user_id == "test_user_1"
        assert retrieved.agent_id == "test_agent_1"

    def test_upsert_session_team(self, test_db: DynamoDb, sample_team_session: TeamSession):
        """Test upserting team session"""
        test_db.upsert_session(sample_team_session)

        retrieved = test_db.get_session_by_id("test_team_session_1")
        assert retrieved is not None
        assert isinstance(retrieved, TeamSession)
        assert retrieved.session_id == "test_team_session_1"
        assert retrieved.user_id == "test_user_2"
        assert retrieved.team_id == "test_team_1"

    def test_update_session(self, test_db: DynamoDb, sample_agent_session: AgentSession):
        """Test updating existing session"""
        test_db.upsert_session(sample_agent_session)

        sample_agent_session.name = "Updated Agent Session"
        sample_agent_session.session_data = {"updated_key": "updated_value"}
        test_db.upsert_session(sample_agent_session)

        retrieved = test_db.get_session_by_id("test_agent_session_1")
        assert retrieved is not None
        assert retrieved.name == "Updated Agent Session"
        assert retrieved.session_data == {"updated_key": "updated_value"}

    def test_get_session_by_id_not_found(self, test_db: DynamoDb):
        """Test retrieving non-existent session"""
        result = test_db.get_session_by_id("non_existent_session")
        assert result is None

    def test_get_session_without_deserialization(self, test_db: DynamoDb, sample_agent_session: AgentSession):
        """Test retrieving session as dict without deserialization"""
        test_db.upsert_session(sample_agent_session)

        result = test_db.get_session_by_id("test_agent_session_1", include_records=False)
        assert result is not None
        assert isinstance(result, dict)
        assert result["session_id"] == "test_agent_session_1"
        assert result["user_id"] == "test_user_1"

    def test_delete_session(self, test_db: DynamoDb, sample_agent_session: AgentSession):
        """Test session deletion"""
        test_db.upsert_session(sample_agent_session)

        retrieved = test_db.get_session_by_id("test_agent_session_1")
        assert retrieved is not None

        test_db.delete_session("test_agent_session_1")

        deleted = test_db.get_session_by_id("test_agent_session_1")
        assert deleted is None

    def test_get_sessions_with_user_filter(
        self, test_db: DynamoDb, sample_agent_session: AgentSession, sample_team_session: TeamSession
    ):
        """Test retrieving sessions filtered by user"""
        test_db.upsert_session(sample_agent_session)
        test_db.upsert_session(sample_team_session)

        sessions = test_db.get_sessions(user_id="test_user_1")
        assert len(sessions) == 1
        assert sessions[0].session_id == "test_agent_session_1"

    def test_get_sessions_with_session_type_filter(
        self, test_db: DynamoDb, sample_agent_session: AgentSession, sample_team_session: TeamSession
    ):
        """Test retrieving sessions filtered by session type"""
        test_db.upsert_session(sample_agent_session)
        test_db.upsert_session(sample_team_session)

        agent_sessions = test_db.get_sessions(session_type=SessionType.agent)
        assert len(agent_sessions) == 1
        assert isinstance(agent_sessions[0], AgentSession)

        team_sessions = test_db.get_sessions(session_type=SessionType.team)
        assert len(team_sessions) == 1
        assert isinstance(team_sessions[0], TeamSession)

    def test_get_sessions_no_filters(
        self, test_db: DynamoDb, sample_agent_session: AgentSession, sample_team_session: TeamSession
    ):
        """Test retrieving all sessions without filters"""
        test_db.upsert_session(sample_agent_session)
        test_db.upsert_session(sample_team_session)

        sessions = test_db.get_sessions()
        assert len(sessions) == 2

    def test_get_sessions_with_limit(
        self, test_db: DynamoDb, sample_agent_session: AgentSession, sample_team_session: TeamSession
    ):
        """Test retrieving sessions with limit"""
        test_db.upsert_session(sample_agent_session)
        test_db.upsert_session(sample_team_session)

        sessions = test_db.get_sessions(limit=1)
        assert len(sessions) == 1


class TestDynamoDbMemory:
    """Tests for memory-related operations in DynamoDb"""

    @pytest.fixture(autouse=True)
    def cleanup_memories(self, test_db: DynamoDb):
        yield
        # DynamoDB cleanup
        try:
            table_name = test_db.memory_table_name
            response = test_db.db_client.scan(TableName=table_name)
            for item in response.get("Items", []):
                test_db.db_client.delete_item(TableName=table_name, Key={"id": item["id"]})
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

    def test_upsert_memory(self, test_db: DynamoDb, sample_memory: UserMemory):
        """Test upserting memory"""
        test_db.upsert_memory(sample_memory)

        retrieved = test_db.get_memory_by_id("test_memory_1")
        assert retrieved is not None
        assert retrieved.id == "test_memory_1"
        assert retrieved.user_id == "test_user_1"
        assert retrieved.memory == "Test memory content"

    def test_get_memory_by_id_not_found(self, test_db: DynamoDb):
        """Test retrieving non-existent memory"""
        result = test_db.get_memory_by_id("non_existent_memory")
        assert result is None

    def test_delete_memory(self, test_db: DynamoDb, sample_memory: UserMemory):
        """Test memory deletion"""
        test_db.upsert_memory(sample_memory)

        retrieved = test_db.get_memory_by_id("test_memory_1")
        assert retrieved is not None

        test_db.delete_memory("test_memory_1")

        deleted = test_db.get_memory_by_id("test_memory_1")
        assert deleted is None

    def test_get_memories_with_user_filter(self, test_db: DynamoDb):
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


class TestDynamoDbMetrics:
    """Tests for metrics-related operations in DynamoDb"""

    @pytest.fixture(autouse=True)
    def cleanup_metrics(self, test_db: DynamoDb):
        yield
        # DynamoDB cleanup
        try:
            table_name = test_db.metrics_table_name
            response = test_db.db_client.scan(TableName=table_name)
            for item in response.get("Items", []):
                test_db.db_client.delete_item(TableName=table_name, Key={"id": item["id"]})
        except Exception:
            pass

    def test_calculate_metrics_basic(self, test_db: DynamoDb):
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
        response = test_db.db_client.scan(TableName=test_db.metrics_table_name)
        assert len(response.get("Items", [])) > 0


class TestDynamoDbEvals:
    """Tests for evaluation-related operations in DynamoDb"""

    @pytest.fixture(autouse=True)
    def cleanup_evals(self, test_db: DynamoDb):
        yield
        # DynamoDB cleanup
        try:
            table_name = test_db.eval_table_name
            response = test_db.db_client.scan(TableName=table_name)
            for item in response.get("Items", []):
                test_db.db_client.delete_item(TableName=table_name, Key={"id": item["id"]})
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

    def test_upsert_eval_record(self, test_db: DynamoDb, sample_eval_record: EvalRunRecord):
        """Test upserting evaluation record"""
        test_db.upsert_eval_record(sample_eval_record)

        retrieved = test_db.get_eval_record_by_id("test_eval_1")
        assert retrieved is not None
        assert retrieved.id == "test_eval_1"
        assert retrieved.eval_id == "eval_1"
        assert retrieved.eval_type == EvalType.agent

    def test_get_eval_record_by_id_not_found(self, test_db: DynamoDb):
        """Test retrieving non-existent evaluation record"""
        result = test_db.get_eval_record_by_id("non_existent_eval")
        assert result is None

    def test_delete_eval_record(self, test_db: DynamoDb, sample_eval_record: EvalRunRecord):
        """Test evaluation record deletion"""
        test_db.upsert_eval_record(sample_eval_record)

        retrieved = test_db.get_eval_record_by_id("test_eval_1")
        assert retrieved is not None

        test_db.delete_eval_record("test_eval_1")

        deleted = test_db.get_eval_record_by_id("test_eval_1")
        assert deleted is None

    def test_get_eval_records_with_filters(self, test_db: DynamoDb, sample_eval_record: EvalRunRecord):
        """Test retrieving evaluation records with filters"""
        test_db.upsert_eval_record(sample_eval_record)

        records = test_db.get_eval_records(user_id="test_user_1")
        assert len(records) == 1
        assert records[0].id == "test_eval_1"

        records = test_db.get_eval_records(eval_type=EvalType.agent)
        assert len(records) == 1
        assert records[0].eval_type == EvalType.agent


class TestDynamoDbKnowledge:
    """Tests for knowledge-related operations in DynamoDb"""

    @pytest.fixture(autouse=True)
    def cleanup_knowledge(self, test_db: DynamoDb):
        yield
        # DynamoDB cleanup
        try:
            table_name = test_db.knowledge_table_name
            response = test_db.db_client.scan(TableName=table_name)
            for item in response.get("Items", []):
                test_db.db_client.delete_item(TableName=table_name, Key={"id": item["id"]})
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

    def test_upsert_knowledge_row(self, test_db: DynamoDb, sample_knowledge_row: KnowledgeRow):
        """Test upserting knowledge row"""
        test_db.upsert_knowledge_row(sample_knowledge_row)

        retrieved = test_db.get_knowledge_row_by_id("test_knowledge_1")
        assert retrieved is not None
        assert retrieved.id == "test_knowledge_1"
        assert retrieved.name == "Test Knowledge"
        assert retrieved.type == "document"

    def test_get_knowledge_row_by_id_not_found(self, test_db: DynamoDb):
        """Test retrieving non-existent knowledge row"""
        result = test_db.get_knowledge_row_by_id("non_existent_knowledge")
        assert result is None

    def test_delete_knowledge_row(self, test_db: DynamoDb, sample_knowledge_row: KnowledgeRow):
        """Test knowledge row deletion"""
        test_db.upsert_knowledge_row(sample_knowledge_row)

        retrieved = test_db.get_knowledge_row_by_id("test_knowledge_1")
        assert retrieved is not None

        test_db.delete_knowledge_row("test_knowledge_1")

        deleted = test_db.get_knowledge_row_by_id("test_knowledge_1")
        assert deleted is None

    def test_get_knowledge_rows_with_filters(self, test_db: DynamoDb, sample_knowledge_row: KnowledgeRow):
        """Test retrieving knowledge rows with filters"""
        test_db.upsert_knowledge_row(sample_knowledge_row)

        rows = test_db.get_knowledge_rows(type="document")
        assert len(rows) == 1
        assert rows[0].id == "test_knowledge_1"
        assert rows[0].type == "document"
