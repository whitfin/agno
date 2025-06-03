from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional
from uuid import uuid4

from agno.run.response import RunEvent, RunResponse
from agno.utils.log import logger

from .task import Task


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

    def execute(self, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> Iterator[RunResponse]:
        """Execute all tasks in the sequence sequentially (synchronous)"""
        logger.info(f"Starting sequence: {self.name}")

        # Initialize sequence context
        sequence_context = context or {}
        sequence_context["sequence_name"] = self.name
        sequence_context["sequence_id"] = self.sequence_id

        # Track outputs from each task
        task_outputs = {}
        current_inputs = inputs.copy()

        yield RunResponse(content=f"Sequence {self.name} started", event=RunEvent.workflow_started)

        for i, task in enumerate(self.tasks):
            logger.info(f"Executing task {i + 1}/{len(self.tasks)}: {task.name}")

            # Merge previous task outputs with current inputs
            # This allows each task to access outputs from previous tasks
            task_inputs = current_inputs.copy()
            task_inputs.update(task_outputs)

            # Execute the task synchronously
            task_response = task.execute(task_inputs, sequence_context)

            # Store task output
            if task_response.content:
                # Store with task name as key
                task_outputs[task.name] = task_response.content

                # Store with task name + "_output" suffix
                task_outputs[f"{task.name}_output"] = task_response.content

                # Store with task index for positional access
                task_outputs[f"task_{i}_output"] = task_response.content

                # Store with generic "output" key for single-task sequences
                task_outputs["output"] = task_response.content

                # Store with "result" key as alternative
                task_outputs["result"] = task_response.content

            # Yield intermediate response
            yield RunResponse(
                content=task_response.content,
                event=RunEvent.run_response,
                extra_data={
                    "task_name": task.name,
                    "task_index": i,
                    "sequence_name": self.name,
                    # Show available outputs
                    "task_outputs": list(task_outputs.keys()),
                },
            )

        # Sequence completed
        final_output = {"sequence_name": self.name, "task_outputs": task_outputs, "status": "completed"}

        yield RunResponse(content=str(final_output), event=RunEvent.workflow_completed, extra_data=final_output)

        logger.info(f"Sequence {self.name} completed")

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
