"""Integration tests for the FirestoreDb class"""

import time
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Generator, List

import pytest

from agno.db.base import SessionType
from agno.db.firestore.firestore import FirestoreDb
from agno.db.schemas.evals import EvalFilterType, EvalRunRecord, EvalType
from agno.db.schemas.knowledge import KnowledgeRow
from agno.db.schemas.memory import UserMemory
from agno.run.base import RunStatus
from agno.run.response import RunResponse
from agno.run.team import TeamRunResponse
from agno.session.agent import AgentSession
from agno.session.summary import SessionSummary
from agno.session.team import TeamSession

# TODO: should use Firestore emulator for testing
TEST_PROJECT_ID = "test-project"


@pytest.fixture(scope="session")
def firestore_client():
    """Handle the Firestore client lifecycle"""
    try:
        from google.cloud import firestore
    except ImportError:
        pytest.skip("google-cloud-firestore not installed")
    
    # Initialize with emulator or test project
    client = firestore.Client(project=TEST_PROJECT_ID)
    
    yield client


@pytest.fixture(scope="class")
def test_db(firestore_client) -> Generator[FirestoreDb, None, None]:
    """FirestoreDb instance to be used across all tests"""
    collection_prefix = f"test_agno_{uuid.uuid4().hex[:8]}"
    db = FirestoreDb(
        db_client=firestore_client,
        session_collection=f"{collection_prefix}_sessions",
        memory_collection=f"{collection_prefix}_memories",
        metrics_collection=f"{collection_prefix}_metrics",
        eval_collection=f"{collection_prefix}_evals",
        knowledge_collection=f"{collection_prefix}_knowledge",
    )

    yield db

    # Cleanup - delete all documents in collections
    try:
        for collection_name in [
            f"{collection_prefix}_sessions",
            f"{collection_prefix}_memories", 
            f"{collection_prefix}_metrics",
            f"{collection_prefix}_evals",
            f"{collection_prefix}_knowledge"
        ]:
            collection = firestore_client.collection(collection_name)
            docs = collection.stream()
            for doc in docs:
                doc.reference.delete()
    except Exception:
        pass


class TestFirestoreDbInfrastructure:
    """Tests for the infrastructure-related methods of FirestoreDb"""

    def test_initialization_with_project_id(self):
        try:
            from google.cloud import firestore
        except ImportError:
            pytest.skip("google-cloud-firestore not installed")
            
        db = FirestoreDb(project_id=TEST_PROJECT_ID)

        assert db.project_id == TEST_PROJECT_ID
        assert db.db_client is not None
        assert db.session_collection_name == "agno_sessions"

    def test_initialization_with_client(self, firestore_client):
        db = FirestoreDb(db_client=firestore_client)

        assert db.db_client == firestore_client
        assert db.project_id is None
        assert db.session_collection_name == "agno_sessions"

    def test_initialization_with_custom_collection_names(self, firestore_client):
        custom_session_collection = "custom_sessions"
        db = FirestoreDb(db_client=firestore_client, session_collection=custom_session_collection)

        assert db.session_collection_name == custom_session_collection

    def test_initialization_requires_client_or_project(self):
        with pytest.raises(ValueError, match="One of project_id or db_client must be provided"):
            FirestoreDb()

    def test_get_collection(self, test_db: FirestoreDb):
        """Ensure the _get_collection method returns correct collection"""
        collection = test_db._get_collection("sessions")
        assert collection is not None
        assert collection.id.endswith("_sessions")

    def test_get_collection_all_mappings(self, test_db: FirestoreDb):
        """Ensure the _get_collection method returns the correct collection for all mappings"""
        # Eval collection
        collection = test_db._get_collection("evals")
        assert collection is not None
        assert collection.id.endswith("_evals")

        # Knowledge collection
        collection = test_db._get_collection("knowledge")
        assert collection is not None
        assert collection.id.endswith("_knowledge")

        # Memory collection
        collection = test_db._get_collection("memories")
        assert collection is not None
        assert collection.id.endswith("_memories")

        # Metrics collection
        collection = test_db._get_collection("metrics")
        assert collection is not None
        assert collection.id.endswith("_metrics")

    def test_get_collection_invalid_type(self, test_db: FirestoreDb):
        """Ensure _get_collection raises for invalid collection types"""
        with pytest.raises(ValueError, match="Unknown table type: fake-type"):
            test_db._get_collection("fake-type")


class TestFirestoreDbSession:
    """Tests for session-related operations in FirestoreDb"""

    @pytest.fixture(autouse=True)
    def cleanup_sessions(self, test_db: FirestoreDb):
        yield
        collection = test_db._get_collection("sessions")
        docs = collection.stream()
        for doc in docs:
            doc.reference.delete()

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

    def test_insert_session(self, test_db: FirestoreDb, sample_agent_session: AgentSession):
        """Test basic session insertion"""
        test_db.upsert_session(sample_agent_session)

        collection = test_db._get_collection("sessions")
        doc = collection.document("test_agent_session_1").get()
        assert doc.exists
        data = doc.to_dict()
        assert data["user_id"] == "test_user_1"
        assert data["agent_id"] == "test_agent_1"

    def test_upsert_session_agent(self, test_db: FirestoreDb, sample_agent_session: AgentSession):
        """Test upserting agent session"""
        test_db.upsert_session(sample_agent_session)

        retrieved = test_db.get_session_by_id("test_agent_session_1")
        assert retrieved is not None
        assert isinstance(retrieved, AgentSession)
        assert retrieved.session_id == "test_agent_session_1"
        assert retrieved.user_id == "test_user_1"
        assert retrieved.agent_id == "test_agent_1"

    def test_upsert_session_team(self, test_db: FirestoreDb, sample_team_session: TeamSession):
        """Test upserting team session"""
        test_db.upsert_session(sample_team_session)

        retrieved = test_db.get_session_by_id("test_team_session_1")
        assert retrieved is not None
        assert isinstance(retrieved, TeamSession)
        assert retrieved.session_id == "test_team_session_1"
        assert retrieved.user_id == "test_user_2"
        assert retrieved.team_id == "test_team_1"

    def test_update_session(self, test_db: FirestoreDb, sample_agent_session: AgentSession):
        """Test updating existing session"""
        test_db.upsert_session(sample_agent_session)

        sample_agent_session.name = "Updated Agent Session"
        sample_agent_session.session_data = {"updated_key": "updated_value"}
        test_db.upsert_session(sample_agent_session)

        retrieved = test_db.get_session_by_id("test_agent_session_1")
        assert retrieved is not None
        assert retrieved.name == "Updated Agent Session"
        assert retrieved.session_data == {"updated_key": "updated_value"}

    def test_get_session_by_id_not_found(self, test_db: FirestoreDb):
        """Test retrieving non-existent session"""
        result = test_db.get_session_by_id("non_existent_session")
        assert result is None

    def test_get_session_without_deserialization(self, test_db: FirestoreDb, sample_agent_session: AgentSession):
        """Test retrieving session as dict without deserialization"""
        test_db.upsert_session(sample_agent_session)

        result = test_db.get_session_by_id("test_agent_session_1", include_records=False)
        assert result is not None
        assert isinstance(result, dict)
        assert result["session_id"] == "test_agent_session_1"
        assert result["user_id"] == "test_user_1"

    def test_delete_session(self, test_db: FirestoreDb, sample_agent_session: AgentSession):
        """Test session deletion"""
        test_db.upsert_session(sample_agent_session)

        retrieved = test_db.get_session_by_id("test_agent_session_1")
        assert retrieved is not None

        test_db.delete_session("test_agent_session_1")

        deleted = test_db.get_session_by_id("test_agent_session_1")
        assert deleted is None

    def test_get_sessions_with_user_filter(self, test_db: FirestoreDb, sample_agent_session: AgentSession, sample_team_session: TeamSession):
        """Test retrieving sessions filtered by user"""
        test_db.upsert_session(sample_agent_session)
        test_db.upsert_session(sample_team_session)

        sessions = test_db.get_sessions(user_id="test_user_1")
        assert len(sessions) == 1
        assert sessions[0].session_id == "test_agent_session_1"

    def test_get_sessions_with_session_type_filter(self, test_db: FirestoreDb, sample_agent_session: AgentSession, sample_team_session: TeamSession):
        """Test retrieving sessions filtered by session type"""
        test_db.upsert_session(sample_agent_session)
        test_db.upsert_session(sample_team_session)

        agent_sessions = test_db.get_sessions(session_type=SessionType.agent)
        assert len(agent_sessions) == 1
        assert isinstance(agent_sessions[0], AgentSession)

        team_sessions = test_db.get_sessions(session_type=SessionType.team)
        assert len(team_sessions) == 1
        assert isinstance(team_sessions[0], TeamSession)

    def test_get_sessions_no_filters(self, test_db: FirestoreDb, sample_agent_session: AgentSession, sample_team_session: TeamSession):
        """Test retrieving all sessions without filters"""
        test_db.upsert_session(sample_agent_session)
        test_db.upsert_session(sample_team_session)

        sessions = test_db.get_sessions()
        assert len(sessions) == 2

    def test_get_sessions_with_limit(self, test_db: FirestoreDb, sample_agent_session: AgentSession, sample_team_session: TeamSession):
        """Test retrieving sessions with limit"""
        test_db.upsert_session(sample_agent_session)
        test_db.upsert_session(sample_team_session)

        sessions = test_db.get_sessions(limit=1)
        assert len(sessions) == 1


class TestFirestoreDbMemory:
    """Tests for memory-related operations in FirestoreDb"""

    @pytest.fixture(autouse=True)
    def cleanup_memories(self, test_db: FirestoreDb):
        yield
        collection = test_db._get_collection("memories")
        docs = collection.stream()
        for doc in docs:
            doc.reference.delete()

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

    def test_upsert_memory(self, test_db: FirestoreDb, sample_memory: UserMemory):
        """Test upserting memory"""
        test_db.upsert_memory(sample_memory)

        retrieved = test_db.get_memory_by_id("test_memory_1")
        assert retrieved is not None
        assert retrieved.id == "test_memory_1"
        assert retrieved.user_id == "test_user_1"
        assert retrieved.memory == "Test memory content"

    def test_get_memory_by_id_not_found(self, test_db: FirestoreDb):
        """Test retrieving non-existent memory"""
        result = test_db.get_memory_by_id("non_existent_memory")
        assert result is None

    def test_delete_memory(self, test_db: FirestoreDb, sample_memory: UserMemory):
        """Test memory deletion"""
        test_db.upsert_memory(sample_memory)

        retrieved = test_db.get_memory_by_id("test_memory_1")
        assert retrieved is not None

        test_db.delete_memory("test_memory_1")

        deleted = test_db.get_memory_by_id("test_memory_1")
        assert deleted is None

    def test_get_memories_with_user_filter(self, test_db: FirestoreDb):
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


class TestFirestoreDbMetrics:
    """Tests for metrics-related operations in FirestoreDb"""

    @pytest.fixture(autouse=True)
    def cleanup_metrics(self, test_db: FirestoreDb):
        yield
        collection = test_db._get_collection("metrics")
        docs = collection.stream()
        for doc in docs:
            doc.reference.delete()

    def test_calculate_metrics_basic(self, test_db: FirestoreDb):
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
        collection = test_db._get_collection("metrics")
        docs = list(collection.stream())
        assert len(docs) > 0


class TestFirestoreDbEvals:
    """Tests for evaluation-related operations in FirestoreDb"""

    @pytest.fixture(autouse=True)
    def cleanup_evals(self, test_db: FirestoreDb):
        yield
        collection = test_db._get_collection("evals")
        docs = collection.stream()
        for doc in docs:
            doc.reference.delete()

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

    def test_upsert_eval_record(self, test_db: FirestoreDb, sample_eval_record: EvalRunRecord):
        """Test upserting evaluation record"""
        test_db.upsert_eval_record(sample_eval_record)

        retrieved = test_db.get_eval_record_by_id("test_eval_1")
        assert retrieved is not None
        assert retrieved.id == "test_eval_1"
        assert retrieved.eval_id == "eval_1"
        assert retrieved.eval_type == EvalType.agent

    def test_get_eval_record_by_id_not_found(self, test_db: FirestoreDb):
        """Test retrieving non-existent evaluation record"""
        result = test_db.get_eval_record_by_id("non_existent_eval")
        assert result is None

    def test_delete_eval_record(self, test_db: FirestoreDb, sample_eval_record: EvalRunRecord):
        """Test evaluation record deletion"""
        test_db.upsert_eval_record(sample_eval_record)

        retrieved = test_db.get_eval_record_by_id("test_eval_1")
        assert retrieved is not None

        test_db.delete_eval_record("test_eval_1")

        deleted = test_db.get_eval_record_by_id("test_eval_1")
        assert deleted is None

    def test_get_eval_records_with_filters(self, test_db: FirestoreDb, sample_eval_record: EvalRunRecord):
        """Test retrieving evaluation records with filters"""
        test_db.upsert_eval_record(sample_eval_record)

        records = test_db.get_eval_records(user_id="test_user_1")
        assert len(records) == 1
        assert records[0].id == "test_eval_1"

        records = test_db.get_eval_records(eval_type=EvalType.agent)
        assert len(records) == 1
        assert records[0].eval_type == EvalType.agent


class TestFirestoreDbKnowledge:
    """Tests for knowledge-related operations in FirestoreDb"""

    @pytest.fixture(autouse=True)
    def cleanup_knowledge(self, test_db: FirestoreDb):
        yield
        collection = test_db._get_collection("knowledge")
        docs = collection.stream()
        for doc in docs:
            doc.reference.delete()

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

    def test_upsert_knowledge_row(self, test_db: FirestoreDb, sample_knowledge_row: KnowledgeRow):
        """Test upserting knowledge row"""
        test_db.upsert_knowledge_row(sample_knowledge_row)

        retrieved = test_db.get_knowledge_row_by_id("test_knowledge_1")
        assert retrieved is not None
        assert retrieved.id == "test_knowledge_1"
        assert retrieved.name == "Test Knowledge"
        assert retrieved.type == "document"

    def test_get_knowledge_row_by_id_not_found(self, test_db: FirestoreDb):
        """Test retrieving non-existent knowledge row"""
        result = test_db.get_knowledge_row_by_id("non_existent_knowledge")
        assert result is None

    def test_delete_knowledge_row(self, test_db: FirestoreDb, sample_knowledge_row: KnowledgeRow):
        """Test knowledge row deletion"""
        test_db.upsert_knowledge_row(sample_knowledge_row)

        retrieved = test_db.get_knowledge_row_by_id("test_knowledge_1")
        assert retrieved is not None

        test_db.delete_knowledge_row("test_knowledge_1")

        deleted = test_db.get_knowledge_row_by_id("test_knowledge_1")
        assert deleted is None

    def test_get_knowledge_rows_with_filters(self, test_db: FirestoreDb, sample_knowledge_row: KnowledgeRow):
        """Test retrieving knowledge rows with filters"""
        test_db.upsert_knowledge_row(sample_knowledge_row)

        rows = test_db.get_knowledge_rows(type="document")
        assert len(rows) == 1
        assert rows[0].id == "test_knowledge_1"
        assert rows[0].type == "document"