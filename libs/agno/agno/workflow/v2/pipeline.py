from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, AsyncIterator
from uuid import uuid4

from .task import Task
from agno.run.response import RunResponse, RunEvent
from agno.utils.log import logger


@dataclass
class Pipeline:
    """A sequence of tasks that execute in order"""

    # Pipeline identification
    name: str
    pipeline_id: Optional[str] = None
    description: Optional[str] = None

    # Tasks to execute
    tasks: List[Task] = field(default_factory=list)

    # Pipeline configuration
    fail_fast: bool = True  # Stop on first task failure
    parallel_execution: bool = False  # Future: support parallel task execution

    def __post_init__(self):
        if self.pipeline_id is None:
            self.pipeline_id = str(uuid4())

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> AsyncIterator[RunResponse]:
        """Execute all tasks in the pipeline sequentially"""
        logger.info(f"Starting pipeline: {self.name}")

        # Initialize pipeline context
        pipeline_context = context or {}
        pipeline_context['pipeline_name'] = self.name
        pipeline_context['pipeline_id'] = self.pipeline_id

        # Track outputs from each task
        task_outputs = {}
        current_inputs = inputs.copy()

        yield RunResponse(
            content=f"Pipeline {self.name} started",
            event=RunEvent.workflow_started
        )

        for i, task in enumerate(self.tasks):
            try:
                logger.info(
                    f"Executing task {i+1}/{len(self.tasks)}: {task.name}")

                # Merge previous task outputs with current inputs
                # This allows each task to access outputs from previous tasks
                task_inputs = current_inputs.copy()
                task_inputs.update(task_outputs)

                # Execute the task
                task_response = await task.execute(task_inputs, pipeline_context)

                # Store task output
                if task_response.content:
                    # Store with task name as key
                    task_outputs[task.name] = task_response.content

                    # Store with task name + "_output" suffix
                    task_outputs[f"{task.name}_output"] = task_response.content

                    # Store with task index for positional access
                    task_outputs[f"task_{i}_output"] = task_response.content

                    # Store with generic "output" key for single-task pipelines
                    task_outputs["output"] = task_response.content

                    # Store with "result" key as alternative
                    task_outputs["result"] = task_response.content

                # Yield intermediate response
                yield RunResponse(
                    content=task_response.content,
                    event=RunEvent.run_response,
                    extra_data={
                        'task_name': task.name,
                        'task_index': i,
                        'pipeline_name': self.name,
                        # Show available outputs
                        'task_outputs': list(task_outputs.keys())
                    }
                )

            except Exception as e:
                error_msg = f"Task {task.name} failed: {e}"
                logger.error(error_msg)

                if self.fail_fast:
                    yield RunResponse(
                        content=error_msg,
                        event=RunEvent.run_error
                    )
                    return
                else:
                    # Continue with next task
                    task_outputs[f"{task.name}_output"] = f"FAILED: {e}"
                    yield RunResponse(
                        content=error_msg,
                        event=RunEvent.run_error,
                        extra_data={'continue_pipeline': True}
                    )

        # Pipeline completed
        final_output = {
            'pipeline_name': self.name,
            'task_outputs': task_outputs,
            'status': 'completed'
        }

        yield RunResponse(
            content=str(final_output),
            event=RunEvent.workflow_completed,
            extra_data=final_output
        )

        logger.info(f"Pipeline {self.name} completed")

    def add_task(self, task: Task) -> None:
        """Add a task to the pipeline"""
        self.tasks.append(task)

    def remove_task(self, task_name: str) -> bool:
        """Remove a task from the pipeline by name"""
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
