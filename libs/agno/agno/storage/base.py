from abc import ABC, abstractmethod
from typing import List, Optional

from agno.storage.session import Session


class Storage(ABC):
    def __init__(
        self,
        agent_sessions_table: Optional[str] = None,
        team_sessions_table: Optional[str] = None,
        workflow_sessions_table: Optional[str] = None,
        user_memories_table: Optional[str] = None,
        learnings_table: Optional[str] = None,
        evals_table: Optional[str] = None,
    ):
        if (
            not agent_sessions_table_name
            and not team_sessions_table_name
            and not workflow_sessions_table_name
            and not memory_table_name
            and not learnings_table_name
            and not eval_runs_table_name
        ):
            raise ValueError("At least one of the tables must be provided")

        self.agent_sessions_table_name = agent_sessions_table_name
        self.team_sessions_table_name = team_sessions_table_name
        self.workflow_sessions_table_name = workflow_sessions_table_name
        self.memory_table_name = memory_table_name
        self.learnings_table_name = learnings_table_name
        self.eval_runs_table_name = eval_runs_table_name

    # --- READ ---

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[Session]:
        raise NotImplementedError

    @abstractmethod
    def get_all_session_ids(self, agent_id: Optional[str] = None) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def get_all_sessions(self, entity_id: Optional[str] = None) -> List[Session]:
        raise NotImplementedError

    # --- WRITE ---

    @abstractmethod
    def create_table(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_session(self, session_id: Optional[str] = None):
        raise NotImplementedError

    # @abstractmethod
    # def upsert(self, session: Session) -> Optional[Session]:
    #     raise NotImplementedError

    # --- UTILITIES ---

    # @abstractmethod
    # def create_table(self, table_name: str, schema: str) -> None:
    #     raise NotImplementedError

    # @abstractmethod
    # def validate_table_schema(self, table_name: str, schema: str) -> None:
    #     raise NotImplementedError

    # @abstractmethod
    # def upgrade_schema(self) -> None:
    #     raise NotImplementedError
