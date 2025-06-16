from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional
from uuid import uuid4

from agno.media import ImageArtifact, VideoArtifact, AudioArtifact
from agno.run.v2.workflow import (
    TaskCompletedEvent,
    WorkflowCompletedEvent,
    WorkflowRunEvent,
    WorkflowRunResponse,
    WorkflowRunResponseEvent,
    WorkflowStartedEvent,
)
from agno.utils.log import logger
from agno.workflow.v2.task import Task, TaskInput, TaskOutput


@dataclass
class PipelineInput:
    """Input data for a task execution"""

    message: Optional[str] = None

    # state
    workflow_session_state: Optional[Dict[str, Any]] = None

    # Media inputs
    images: Optional[List[ImageArtifact]] = None
    videos: Optional[List[VideoArtifact]] = None
    audio: Optional[List[AudioArtifact]] = None

    def get_primary_input(self) -> str:
        """Get the primary text input (query or message)"""
        return self.query or self.message or ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "message": self.message,
            "workflow_session_state": self.workflow_session_state,
            "images": [img.to_dict() for img in self.images] if self.images else None,
            "videos": [vid.to_dict() for vid in self.videos] if self.videos else None,
            "audio": [aud.to_dict() for aud in self.audio] if self.audio else None,
        }

@dataclass
class Pipeline:
    """A pipeline of tasks that execute in order"""

    # Pipeline_name identification
    name: str
    pipeline_id: Optional[str] = None
    description: Optional[str] = None

    # Tasks to execute
    tasks: List[Task] = field(default_factory=list)

    def __post_init__(self):
        if self.pipeline_id is None:
            self.pipeline_id = str(uuid4())


    def execute(self, pipeline_input: PipelineInput, workflow_run_response: WorkflowRunResponse):
        """Execute all tasks in the pipeline using TaskInput/TaskOutput (non-streaming)"""
        logger.info(f"Starting pipeline: {self.name}")

        # Update pipeline info in the response
        workflow_run_response.pipeline_name = self.name

        # Track outputs from each task for chaining
        previous_outputs = {}
        collected_task_outputs: List[TaskOutput] = []

        for i, task in enumerate(self.tasks):
            logger.info(f"Executing task {i + 1}/{len(self.tasks)}: {task.name}")

            # Create TaskInput for this task
            task_input = self._create_task_input(pipeline_input, previous_outputs, workflow_run_response)

            # Execute the task (non-streaming) - pass workflow_run_response
            task_output = task.execute(task_input, workflow_run_response, task_index=i)

            # Collect the task output
            if task_output is None:
                raise RuntimeError(f"Task {task.name} did not return a TaskOutput")

            # Collect the TaskOutput for storage
            collected_task_outputs.append(task_output)

            # Update previous_outputs for next task
            self._update_previous_outputs(previous_outputs, task, task_output, i)

        # Create final output data
        final_output = {
            "pipeline_id": self.pipeline_id,
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

        # Update the workflow_run_response with completion data
        workflow_run_response.event = WorkflowRunEvent.workflow_completed
        workflow_run_response.content = f"Pipeline {self.name} completed successfully"
        workflow_run_response.task_responses = collected_task_outputs
        workflow_run_response.extra_data = final_output

    def execute_stream(
        self,
        pipeline_input: PipelineInput,
        workflow_run_response: WorkflowRunResponse,
        stream_intermediate_steps: bool = False,
    ) -> Iterator[WorkflowRunResponseEvent]:
        """Execute the pipeline with event-driven streaming support"""
        logger.info(f"Executing pipeline with streaming: {self.name}")

        # Update pipeline info in the response
        workflow_run_response.pipeline_name = self.name

        # Yield workflow started event
        yield WorkflowStartedEvent(
            run_id=workflow_run_response.run_id or "",
            content=f"Pipeline {self.name} started",
            workflow_name=workflow_run_response.workflow_name,
            pipeline_name=self.name,
            workflow_id=workflow_run_response.workflow_id,
            session_id=workflow_run_response.session_id,
        )

        # Track outputs from each task for chaining
        previous_outputs = {}
        collected_task_outputs: List[TaskOutput] = []

        # Execute tasks in pipeline with streaming
        for task_index, task in enumerate(self.tasks):
            # Create TaskInput for this task
            task_input = self._create_task_input(pipeline_input, previous_outputs, workflow_run_response)

            # Execute task with streaming and yield all events
            task_output = None
            for event in task.execute(
                task_input,
                workflow_run_response,
                stream=True,
                stream_intermediate_steps=stream_intermediate_steps,
                task_index=task_index,
            ):
                if isinstance(event, TaskOutput):
                    # This is the final task output
                    task_output = event

                    # Collect the task output
                    collected_task_outputs.append(task_output)

                    # Update previous_outputs for next task
                    self._update_previous_outputs(previous_outputs, task, task_output, task_index)

                    # Yield task completed event
                    yield TaskCompletedEvent(
                        run_id=workflow_run_response.run_id or "",
                        content=task_output.content,
                        workflow_name=workflow_run_response.workflow_name,
                        pipeline_name=self.name,
                        task_name=task.name,
                        task_index=task_index,
                        workflow_id=workflow_run_response.workflow_id,
                        session_id=workflow_run_response.session_id,
                        images=task_output.images,
                        videos=task_output.videos,
                        audio=task_output.audio,
                        task_responses=[task_output],
                    )
                else:
                    yield event

        # Create final output data
        final_output = {
            "pipeline_id": self.pipeline_id,
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

        # Yield workflow completed event
        yield WorkflowCompletedEvent(
            run_id=workflow_run_response.run_id or "",
            content=f"Pipeline {self.name} completed successfully",
            workflow_name=workflow_run_response.workflow_name,
            pipeline_name=self.name,
            workflow_id=workflow_run_response.workflow_id,
            session_id=workflow_run_response.session_id,
            task_responses=collected_task_outputs,
            extra_data=final_output,
        )

    async def aexecute(
        self, pipeline_input: PipelineInput, workflow_run_response: WorkflowRunResponse
    ) -> WorkflowRunResponse:
        """Execute all tasks in the pipeline using TaskInput/TaskOutput (non-streaming)"""
        logger.info(f"Starting pipeline: {self.name}")

        # Update pipeline info in the response
        workflow_run_response.pipeline_name = self.name

        # Track outputs from each task for chaining
        previous_outputs = {}
        collected_task_outputs: List[TaskOutput] = []

        for i, task in enumerate(self.tasks):
            logger.info(f"Executing task {i + 1}/{len(self.tasks)}: {task.name}")

            # Create TaskInput for this task
            task_input = self._create_task_input(pipeline_input, previous_outputs, workflow_run_response)

            # Execute the task (non-streaming) - pass workflow_run_response
            task_output = await task.aexecute(task_input, workflow_run_response, task_index=i)

            # Collect the task output
            if task_output is None:
                raise RuntimeError(f"Task {task.name} did not return a TaskOutput")

            # Collect the TaskOutput for storage
            collected_task_outputs.append(task_output)

            # Update previous_outputs for next task
            self._update_previous_outputs(previous_outputs, task, task_output, i)

        # Create final output data
        final_output = {
            "pipeline_id": self.pipeline_id,
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

        # Update the workflow_run_response with completion data
        workflow_run_response.event = WorkflowRunEvent.workflow_completed
        workflow_run_response.content = f"Pipeline {self.name} completed successfully"
        workflow_run_response.task_responses = collected_task_outputs
        workflow_run_response.extra_data = final_output

    async def aexecute_stream(
        self,
        pipeline_input: PipelineInput,
        workflow_run_response: WorkflowRunResponse,
        stream_intermediate_steps: bool = False,
    ) -> AsyncIterator[WorkflowRunResponseEvent]:
        """Execute the pipeline with event-driven streaming support"""
        logger.info(f"Executing pipeline with streaming: {self.name}")

        # Yield workflow started event
        yield WorkflowStartedEvent(
            run_id=workflow_run_response.run_id or "",
            content=f"Pipeline {self.name} started",
            workflow_name=workflow_run_response.workflow_name,
            pipeline_name=self.name,
            workflow_id=workflow_run_response.workflow_id,
            session_id=workflow_run_response.session_id,
        )

        # Track outputs from each task for chaining
        previous_outputs = {}
        collected_task_outputs: List[TaskOutput] = []

        # Execute tasks in pipeline with streaming
        for task_index, task in enumerate(self.tasks):
            # Create TaskInput for this task
            task_input = self._create_task_input(pipeline_input, previous_outputs, workflow_run_response)

            task_output = None
            task_stream = await task.aexecute(
                task_input,
                workflow_run_response,
                stream=True,
                stream_intermediate_steps=stream_intermediate_steps,
                task_index=task_index,
            )

            async for event in task_stream:
                if isinstance(event, TaskOutput):
                    # This is the final task output
                    task_output = event

                    # Collect the task output
                    collected_task_outputs.append(task_output)

                    # Update previous_outputs for next task
                    self._update_previous_outputs(previous_outputs, task, task_output, task_index)

                    # Yield task completed event
                    yield TaskCompletedEvent(
                        run_id=workflow_run_response.run_id or "",
                        content=task_output.content,
                        workflow_name=workflow_run_response.workflow_name,
                        pipeline_name=self.name,
                        task_name=task.name,
                        task_index=task_index,
                        workflow_id=workflow_run_response.workflow_id,
                        session_id=workflow_run_response.session_id,
                        images=task_output.images,
                        videos=task_output.videos,
                        audio=task_output.audio,
                        task_responses=[task_output],
                    )
                else:
                    yield event

        # Create final output data
        final_output = {
            "pipeline_id": self.pipeline_id,
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

        # Yield workflow completed event
        yield WorkflowCompletedEvent(
            run_id=workflow_run_response.run_id or "",
            content=f"Pipeline {self.name} completed successfully",
            workflow_name=workflow_run_response.workflow_name,
            pipeline_name=self.name,
            workflow_id=workflow_run_response.workflow_id,
            session_id=workflow_run_response.session_id,
            task_responses=collected_task_outputs,
            extra_data=final_output,
        )

    def _create_task_input(
        self,
        pipeline_input: PipelineInput,
        previous_outputs: Dict[str, Any],
        workflow_run_response: WorkflowRunResponse,
    ) -> TaskInput:
        """Create TaskInput for a task"""
        # Extract media from initial inputs
        images = pipeline_input.images
        videos = pipeline_input.videos
        audio = pipeline_input.audio

        # Create workflow session state from WorkflowRunResponse
        workflow_session_state = {
            "workflow_id": workflow_run_response.workflow_id,
            "workflow_name": workflow_run_response.workflow_name,
            "run_id": workflow_run_response.run_id,
            "session_id": workflow_run_response.session_id,
            "pipeline_name": workflow_run_response.pipeline_name,
        }

        return TaskInput(
            message=pipeline_input.message,
            workflow_session_state=workflow_session_state,
            previous_outputs=previous_outputs.copy() if previous_outputs else None,
            images=images,
            videos=videos,
            audio=audio,
        )

    def _update_previous_outputs(
        self, previous_outputs: Dict[str, Any], task: Task, task_output: TaskOutput, task_index: int
    ):
        """Update previous_outputs with the current task's output"""
        if task_output.content:
            # Store output with multiple keys for flexibility
            previous_outputs[task.name] = task_output.content
            previous_outputs[f"{task.name}_output"] = task_output.content
            previous_outputs[f"task_{task_index}_output"] = task_output.content
            previous_outputs["output"] = task_output.content  # Latest output
            # Alias for output
            previous_outputs["result"] = task_output.content

        # Store structured data if available
        if task_output.data:
            previous_outputs[f"{task.name}_data"] = task_output.data
            previous_outputs["data"] = task_output.data  # Latest data

        # Store media outputs
        if task_output.images:
            previous_outputs[f"{task.name}_images"] = task_output.images
            previous_outputs["images"] = task_output.images  # Latest images

        if task_output.videos:
            previous_outputs[f"{task.name}_videos"] = task_output.videos
            previous_outputs["videos"] = task_output.videos  # Latest videos

        if task_output.audio:
            previous_outputs[f"{task.name}_audio"] = task_output.audio
            previous_outputs["audio"] = task_output.audio  # Latest audio

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
