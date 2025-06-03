from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Optional

from agno.run.workflow import WorkflowRunResponse
from agno.utils.log import logger


@dataclass
class WorkflowSession:
    """Workflow Session that is stored in the database"""

    # Session UUID
    session_id: str
    # ID of the user interacting with this agent
    user_id: Optional[str] = None
    # Agent Memory
    memory: Optional[Dict[str, Any]] = None
    # Session Data: session_name, session_state, images, videos, audio
    session_data: Optional[Dict[str, Any]] = None
    # Extra Data stored with this agent
    extra_data: Optional[Dict[str, Any]] = None
    # The unix timestamp when this session was created
    created_at: Optional[int] = None
    # The unix timestamp when this session was last updated
    updated_at: Optional[int] = None

    # ID of the workflow that this session is associated with
    workflow_id: Optional[str] = None
    # Workflow Data
    workflow_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def monitoring_data(self) -> Dict[str, Any]:
        return asdict(self)

    def telemetry_data(self) -> Dict[str, Any]:
        return {
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Optional[WorkflowSession]:
        if data is None or data.get("session_id") is None:
            logger.warning("WorkflowSession is missing session_id")
            return None

        return cls(
            session_id=data.get("session_id"),  # type: ignore
            workflow_id=data.get("workflow_id"),
            user_id=data.get("user_id"),
            memory=data.get("memory"),
            workflow_data=data.get("workflow_data"),
            session_data=data.get("session_data"),
            extra_data=data.get("extra_data"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class WorkflowSessionV2:
    """Workflow Session V2 for sequence-based workflows"""

    # Session UUID - this is the workflow_session_id that gets set on agents/teams
    session_id: str
    # ID of the user interacting with this workflow
    user_id: Optional[str] = None

    # ID of the workflow that this session is associated with
    workflow_id: Optional[str] = None
    # Workflow name
    workflow_name: Optional[str] = None

    # Workflow runs - stores all WorkflowRunResponse objects
    runs: Optional[List[Dict[str, Any]]] = None

    # Session Data: session_name, session_state, images, videos, audio
    session_data: Optional[Dict[str, Any]] = None
    # Workflow configuration and metadata
    workflow_data: Optional[Dict[str, Any]] = None
    # Extra Data stored with this workflow session
    extra_data: Optional[Dict[str, Any]] = None

    # The unix timestamp when this session was created
    created_at: Optional[int] = None
    # The unix timestamp when this session was last updated
    updated_at: Optional[int] = None

    def __post_init__(self):
        if self.runs is None:
            self.runs = []

    def add_run(self, run_response: WorkflowRunResponse) -> None:
        """Add a workflow run response to this session"""
        if self.runs is None:
            self.runs = []
        self.runs.append(run_response.to_dict())

    def get_runs(self) -> List[WorkflowRunResponse]:
        """Get all runs as WorkflowRunResponse objects"""
        if self.runs is None:
            return []
        return [WorkflowRunResponse.from_dict(run) for run in self.runs]

    def get_runs_for_run_id(self, run_id: str) -> List[WorkflowRunResponse]:
        """Get all runs for a specific run_id"""
        if self.runs is None:
            return []
        return [WorkflowRunResponse.from_dict(run) for run in self.runs if run.get("run_id") == run_id]

    def get_task_runs(self, run_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all task execution data"""
        if self.runs is None:
            return []

        task_runs = []
        for run in self.runs:
            if run_id and run.get("run_id") != run_id:
                continue

            if run.get("event") in ["TaskStarted", "TaskCompleted"]:
                task_data = {
                    "run_id": run.get("run_id"),
                    "task_name": run.get("task_name"),
                    "task_index": run.get("task_index"),
                    "event": run.get("event"),
                    "content": run.get("content"),
                    "created_at": run.get("created_at"),
                    "extra_data": run.get("extra_data", {}),
                }

                # Add media content if present
                if run.get("images"):
                    task_data["images"] = run.get("images")
                if run.get("videos"):
                    task_data["videos"] = run.get("videos")
                if run.get("audio"):
                    task_data["audio"] = run.get("audio")
                if run.get("messages"):
                    task_data["messages"] = run.get("messages")
                if run.get("metrics"):
                    task_data["metrics"] = run.get("metrics")

                task_runs.append(task_data)

        return task_runs

    def get_task_outputs(self, run_id: Optional[str] = None) -> Dict[str, Any]:
        """Get all task outputs for a specific run"""
        task_runs = self.get_task_runs(run_id)
        outputs = {}

        for task_run in task_runs:
            if task_run["event"] == "TaskCompleted":
                task_name = task_run["task_name"]
                outputs[task_name] = {
                    "content": task_run["content"],
                    "task_index": task_run["task_index"],
                    "created_at": task_run["created_at"],
                    "extra_data": task_run.get("extra_data", {}),
                }

                # Include media if present
                for media_type in ["images", "videos", "audio", "messages", "metrics"]:
                    if media_type in task_run:
                        outputs[task_name][media_type] = task_run[media_type]

        return outputs

    def get_workflow_summary(self, run_id: Optional[str] = None) -> Dict[str, Any]:
        """Get a summary of workflow execution"""
        if self.runs is None:
            return {}

        runs_to_analyze = [run for run in self.runs if not run_id or run.get("run_id") == run_id]

        workflow_started = next((run for run in runs_to_analyze if run.get("event") == "WorkflowStarted"), None)
        workflow_completed = next((run for run in runs_to_analyze if run.get("event") == "WorkflowCompleted"), None)
        task_runs = self.get_task_runs(run_id)

        summary = {
            "run_id": run_id,
            "workflow_name": self.workflow_name,
            "sequence_name": workflow_started.get("sequence_name") if workflow_started else None,
            "status": "completed" if workflow_completed else "running",
            "started_at": workflow_started.get("created_at") if workflow_started else None,
            "completed_at": workflow_completed.get("created_at") if workflow_completed else None,
            "total_tasks": len([t for t in task_runs if t["event"] == "TaskCompleted"]),
            "task_summary": [],
        }

        # Group tasks by name and get their data
        task_groups = {}
        for task_run in task_runs:
            task_name = task_run["task_name"]
            if task_name not in task_groups:
                task_groups[task_name] = {"started": None, "completed": None}

            if task_run["event"] == "TaskStarted":
                task_groups[task_name]["started"] = task_run
            elif task_run["event"] == "TaskCompleted":
                task_groups[task_name]["completed"] = task_run

        for task_name, task_data in task_groups.items():
            if task_data["completed"]:
                task_summary = {
                    "task_name": task_name,
                    "task_index": task_data["completed"]["task_index"],
                    "status": "completed",
                    "started_at": task_data["started"]["created_at"] if task_data["started"] else None,
                    "completed_at": task_data["completed"]["created_at"],
                    "has_content": bool(task_data["completed"]["content"]),
                    "has_media": any(key in task_data["completed"] for key in ["images", "videos", "audio"]),
                    "extra_data": task_data["completed"].get("extra_data", {}),
                }
                summary["task_summary"].append(task_summary)

        return summary

    def get_latest_run_id(self) -> Optional[str]:
        """Get the most recent run_id"""
        if not self.runs:
            return None
        # Find the most recent run by created_at timestamp
        latest_run = max(self.runs, key=lambda x: x.get("created_at", 0))
        return latest_run.get("run_id")

    def clear_runs(self) -> None:
        """Clear all runs from this session"""
        self.runs = []

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def monitoring_data(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Optional[WorkflowSessionV2]:
        if data is None or data.get("session_id") is None:
            logger.warning("WorkflowSessionV2 is missing session_id")
            return None

        return cls(
            session_id=data.get("session_id"),  # type: ignore
            user_id=data.get("user_id"),
            workflow_id=data.get("workflow_id"),
            workflow_name=data.get("workflow_name"),
            runs=data.get("runs"),
            session_data=data.get("session_data"),
            workflow_data=data.get("workflow_data"),
            extra_data=data.get("extra_data"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
