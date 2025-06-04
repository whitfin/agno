from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Union
from uuid import uuid4

from agno.run.response import RunResponse
from agno.run.team import TeamRunResponse
from agno.run.workflow import WorkflowRunEvent, WorkflowRunResponse
from agno.utils.log import logger
from agno.workflow.v2.task import Task


@dataclass
class Sequence:
    """A sequence of tasks that execute in order"""

    # Sequence identification
    name: str
    sequence_id: Optional[str] = None
    description: Optional[str] = None

    # Tasks to execute
    tasks: List[Task] = field(default_factory=list)

    def __post_init__(self):
        if self.sequence_id is None:
            self.sequence_id = str(uuid4())

    def execute(self, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> Iterator[WorkflowRunResponse]:
        """Execute all tasks in the sequence sequentially (synchronous)"""
        logger.info(f"Starting sequence: {self.name}")

        # Initialize sequence context
        sequence_context = context or {}
        sequence_context["sequence_name"] = self.name
        sequence_context["sequence_id"] = self.sequence_id

        # Track outputs from each task
        task_outputs = {}
        current_inputs = inputs.copy()

        collected_task_responses: List[Union[RunResponse, TeamRunResponse]] = []

        # Workflow started event
        yield WorkflowRunResponse(
            content=f"Sequence {self.name} started",
            event=WorkflowRunEvent.workflow_started,
            workflow_name=context.get("workflow_name") if context else None,
            sequence_name=self.name,
            workflow_id=context.get("workflow_id") if context else None,
            run_id=context.get("run_id") if context else None,
            workflw_session_id=context.get("workflw_session_id") if context else None,
        )

        for i, task in enumerate(self.tasks):
            logger.info(f"Executing task {i + 1}/{len(self.tasks)}: {task.name}")

            # Add task_index to context for the task
            task_context = sequence_context.copy()
            task_context["task_index"] = i

            # Merge previous task outputs with current inputs
            task_inputs = current_inputs.copy()
            task_inputs.update(task_outputs)

            # Execute the task synchronously
            task_response = None
            for event in task.execute(task_inputs, task_context):
                if isinstance(event, WorkflowRunResponse):
                    # Forward workflow events (like task_started)
                    yield event
                elif isinstance(event, (RunResponse, TeamRunResponse)):
                    # This is the final task response
                    task_response = event
                    break

            if task_response is None:
                raise RuntimeError(f"Task {task.name} did not return a response")

            # Collect the actual task response
            collected_task_responses.append(task_response)

            # Store task output
            if task_response.content:
                task_outputs[task.name] = task_response.content
                task_outputs[f"{task.name}_output"] = task_response.content
                task_outputs[f"task_{i}_output"] = task_response.content
                task_outputs["output"] = task_response.content
                task_outputs["result"] = task_response.content

            # Task completed event with full task data
            yield WorkflowRunResponse(
                content=task_response.content,
                event=WorkflowRunEvent.task_completed,
                workflow_name=context.get("workflow_name") if context else None,
                sequence_name=self.name,
                task_name=task.name,
                task_index=i,
                workflow_id=context.get("workflow_id") if context else None,
                run_id=context.get("run_id") if context else None,
                workflw_session_id=context.get("workflw_session_id") if context else None,
                images=getattr(task_response, "images", None),
                videos=getattr(task_response, "videos", None),
                audio=getattr(task_response, "audio", None),
                response_audio=getattr(task_response, "response_audio", None),
                messages=getattr(task_response, "messages", None),
                metrics=getattr(task_response, "metrics", None),
                # Include the actual task response
                task_responses=[task_response],
            )

        # Workflow completed event with all task responses
        final_output = {
            "sequence_name": self.name,
            "sequence_id": self.sequence_id,
            "status": "completed",
            "total_tasks": len(self.tasks),
            "task_summary": [
                {
                    "task_name": task.name,
                    "task_id": task.task_id,
                    "description": task.description,
                    "executor_type": task.executor_type,
                    "executor_name": task.executor_name,
                }
                for task in self.tasks
            ],
        }

        yield WorkflowRunResponse(
            content=f"Sequence {self.name} completed successfully",
            event=WorkflowRunEvent.workflow_completed,
            workflow_name=context.get("workflow_name") if context else None,
            sequence_name=self.name,
            workflow_id=context.get("workflow_id") if context else None,
            run_id=context.get("run_id") if context else None,
            workflw_session_id=context.get("workflw_session_id") if context else None,
            # Include all collected task responses
            task_responses=collected_task_responses,
            extra_data=final_output,
        )

    def add_task(self, task: Task) -> None:
        """Add a task to the sequence"""
        self.tasks.append(task)

    def remove_task(self, task_name: str) -> bool:
        """Remove a task from the sequence by name"""
        for i, task in enumerate(self.tasks):
            if task.name == task_name:
                del self.tasks[i]
                return True
        return False

    def get_task(self, task_name: str) -> Optional[Task]:
        """Get a task by name"""
        for task in self.tasks:
            if task.name == task_name:
                return task
        return None
