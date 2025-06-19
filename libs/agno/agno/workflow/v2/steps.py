from dataclasses import dataclass
from typing import AsyncIterator, Iterator, List, Optional
from uuid import uuid4

from agno.run.base import RunStatus
from agno.run.v2.workflow import (
    StepCompletedEvent,
    StepStartedEvent,
    WorkflowRunResponse,
    WorkflowRunResponseEvent,
)
from agno.utils.log import log_debug, logger
from agno.workflow.v2.step import Step
from agno.workflow.v2.types import StepInput, StepOutput, WorkflowExecutionInput


@dataclass
class Steps:
    """A sequence of steps that execute in order"""

    # sequence_name identification
    name: Optional[str] = None
    steps_id: Optional[str] = None
    description: Optional[str] = None

    # Steps to execute
    steps: Optional[List[Step]] = None

    def __init__(
        self, name: Optional[str] = None, description: Optional[str] = None, steps: Optional[List[Step]] = None
    ):
        self.name = name
        self.description = description
        self.steps = steps if steps else []

    def initialize(self):
        if self.steps_id is None:
            log_debug(f"Initializing steps ID for {self.name}")
            self.steps_id = str(uuid4())

    def execute(
        self,
        steps_input: WorkflowExecutionInput,
        workflow_run_response: WorkflowRunResponse,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """Execute all steps in the sequence using StepInput/StepOutput (non-streaming)"""
        log_debug(f"Steps Execution Start: {self.name}", center=True)
        log_debug(f"Steps ID: {self.steps_id}")
        log_debug(f"Total steps: {len(self.steps)}")

        logger.info(f"Starting sequence: {self.name}")

        # Update steps info in the response
        workflow_run_response.steps_name = self.name

        # Track outputs from each step for chaining
        collected_step_outputs: List[StepOutput] = []

        steps_images = steps_input.images or []
        steps_videos = steps_input.videos or []
        steps_audio = steps_input.audio or []
        previous_step_content = None

        # Execute steps sequentially
        for i, step in enumerate(self.steps):
            log_debug(f"Executing step {i + 1}/{len(self.steps)}: {step.name}")
            log_debug(f"Step ID: {step.step_id}")

            logger.info(f"Executing step {i + 1}/{len(self.steps)}: {step.name}")

            # Create StepInput for this step
            log_debug(f"Created StepInput for step {step.name}")
            step_input = StepInput(
                message=steps_input.message,
                message_data=steps_input.message_data,
                previous_step_content=previous_step_content,
                images=steps_images,
                videos=steps_videos,
                audio=steps_audio,
            )

            # Execute the step (non-streaming)
            step_output = step.execute(step_input, session_id=session_id, user_id=user_id)

            # Collect the step output
            if step_output is None:
                raise RuntimeError(f"Step {step.name} did not return a StepOutput")

            # Update the input for the next step
            previous_step_content = step_output.content
            steps_images.extend(step_output.images or [])
            steps_videos.extend(step_output.videos or [])
            steps_audio.extend(step_output.audio or [])

            # Collect the StepOutput for storage
            collected_step_outputs.append(step_output)

        # Create final output data
        final_output = {
            "steps_id": self.steps_id,
            "total_steps": len(self.steps),
            "step_summary": [
                {
                    "step_name": step.name,
                    "step_id": step.step_id,
                    "description": step.description,
                    "executor_type": step.executor_type,
                    "executor_name": step.executor_name,
                }
                for step in self.steps
            ],
        }

        log_debug(f"Sequence Execution End: {self.name}", center=True, symbol="*")

        # Update the workflow_run_response with completion data
        workflow_run_response.content = collected_step_outputs[
            -1
        ].content  # Final workflow response output is the last step's output
        workflow_run_response.step_responses = collected_step_outputs
        workflow_run_response.extra_data = final_output
        workflow_run_response.images = steps_images
        workflow_run_response.videos = steps_videos
        workflow_run_response.audio = steps_audio
        workflow_run_response.status = RunStatus.completed

    def execute_stream(
        self,
        steps_input: WorkflowExecutionInput,
        workflow_run_response: WorkflowRunResponse,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        stream_intermediate_steps: bool = False,
    ) -> Iterator[WorkflowRunResponseEvent]:
        """Execute the steps with event-driven streaming support"""
        log_debug(f"Steps Streaming Execution Start: {self.name}", center=True)
        log_debug(f"Steps ID: {self.steps_id}")
        log_debug(f"Stream intermediate steps: {stream_intermediate_steps}")
        log_debug(f"Total steps: {len(self.steps)}")

        logger.info(f"Executing steps with streaming: {self.name}")

        # Track outputs from each step for chaining
        collected_step_outputs: List[StepOutput] = []
        steps_images = steps_input.images or []
        steps_videos = steps_input.videos or []
        steps_audio = steps_input.audio or []
        previous_step_content = None

        # Execute steps in steps with streaming
        for step_index, step in enumerate(self.steps):
            log_debug(f"Streaming step {step_index + 1}/{len(self.steps)}: {step.name}")

            # Create StepInput for this step
            step_input = StepInput(
                message=steps_input.message,
                message_data=steps_input.message_data,
                previous_step_content=previous_step_content,
                images=steps_images,
                videos=steps_videos,
                audio=steps_audio,
            )

            # Yield step started event
            yield StepStartedEvent(
                run_id=workflow_run_response.run_id or "",
                workflow_name=workflow_run_response.workflow_name,
                steps_name=workflow_run_response.steps_name,
                step_name=step.name,
                step_index=step_index,
                workflow_id=workflow_run_response.workflow_id,
                session_id=workflow_run_response.session_id,
            )

            # Execute step with streaming and yield all events
            for event in step.execute(
                step_input,
                session_id=session_id,
                user_id=user_id,
                stream=True,
                stream_intermediate_steps=stream_intermediate_steps,
            ):
                if isinstance(event, StepOutput):
                    # This is the final step output
                    step_output = event
                    log_debug(f"Received final StepOutput from {step.name}")

                    # Collect the step output
                    collected_step_outputs.append(step_output)

                    steps_images.extend(step_output.images or [])
                    steps_videos.extend(step_output.videos or [])
                    steps_audio.extend(step_output.audio or [])
                    previous_step_content = step_output.content

                    # Yield step completed event
                    yield StepCompletedEvent(
                        run_id=workflow_run_response.run_id or "",
                        content=step_output.content,
                        workflow_name=workflow_run_response.workflow_name,
                        steps_name=self.name,
                        step_name=step.name,
                        step_index=step_index,
                        workflow_id=workflow_run_response.workflow_id,
                        session_id=workflow_run_response.session_id,
                        images=step_output.images,
                        videos=step_output.videos,
                        audio=step_output.audio,
                        step_response=step_output,
                    )
                    log_debug(f"Yielding StepCompletedEvent for step: {step.name}")
                else:
                    yield event

        # Create final output data
        final_output = {
            "steps_id": self.steps_id,
            "status": "completed",
            "total_steps": len(self.steps),
            "step_summary": [
                {
                    "step_name": step.name,
                    "step_id": step.step_id,
                    "description": step.description,
                    "executor_type": step.executor_type,
                    "executor_name": step.executor_name,
                }
                for step in self.steps
            ],
        }

        workflow_run_response.content = collected_step_outputs[
            -1
        ].content  # Final workflow response output is the last step's output
        workflow_run_response.step_responses = collected_step_outputs
        workflow_run_response.images = steps_images
        workflow_run_response.videos = steps_videos
        workflow_run_response.audio = steps_audio
        workflow_run_response.extra_data = final_output
        workflow_run_response.status = RunStatus.completed

    async def aexecute(
        self,
        steps_input: WorkflowExecutionInput,
        workflow_run_response: WorkflowRunResponse,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """Execute all steps in the Sequence using StepInput/StepOutput (non-streaming)"""
        log_debug(f"Async Steps Execution Start: {self.name}", center=True)
        log_debug(f"Steps ID: {self.steps_id}")
        log_debug(f"Total steps: {len(self.steps)}")

        logger.info(f"Starting steps: {self.name}")

        # Update steps info in the response
        workflow_run_response.steps_name = self.name

        # Track outputs from each step for chaining
        collected_step_outputs: List[StepOutput] = []

        steps_images = steps_input.images or []
        steps_videos = steps_input.videos or []
        steps_audio = steps_input.audio or []
        previous_step_content = None

        for i, step in enumerate(self.steps):
            log_debug(f"Executing async step {i + 1}/{len(self.steps)}: {step.name}")
            log_debug(f"Step ID: {step.step_id}")

            logger.info(f"Executing step {i + 1}/{len(self.steps)}: {step.name}")

            # Create StepInput for this step
            step_input = StepInput(
                message=steps_input.message,
                message_data=steps_input.message_data,
                previous_step_content=previous_step_content,
                images=steps_images,
                videos=steps_videos,
                audio=steps_audio,
            )

            # Execute the step (non-streaming) - pass workflow_run_response
            step_output = await step.aexecute(step_input, session_id=session_id, user_id=user_id)

            # Collect the step output
            if step_output is None:
                raise RuntimeError(f"Step {step.name} did not return a StepOutput")

            # Update the input for the next step
            previous_step_content = step_output.content
            steps_images.extend(step_output.images or [])
            steps_videos.extend(step_output.videos or [])
            steps_audio.extend(step_output.audio or [])

            # Collect the StepOutput for storage
            collected_step_outputs.append(step_output)

        # Create final output data
        final_output = {
            "steps_id": self.steps_id,
            "total_steps": len(self.steps),
            "step_summary": [
                {
                    "step_name": step.name,
                    "step_id": step.step_id,
                    "description": step.description,
                    "executor_type": step.executor_type,
                    "executor_name": step.executor_name,
                }
                for step in self.steps
            ],
        }

        log_debug(f"Async Steps Execution End: {self.name}", center=True, symbol="*")

        # Update the workflow_run_response with completion data
        workflow_run_response.content = collected_step_outputs[
            -1
        ].content  # Final workflow response output is the last step's output
        workflow_run_response.step_responses = collected_step_outputs
        workflow_run_response.extra_data = final_output
        workflow_run_response.images = steps_images
        workflow_run_response.videos = steps_videos
        workflow_run_response.audio = steps_audio
        workflow_run_response.status = RunStatus.completed

    async def aexecute_stream(
        self,
        steps_input: WorkflowExecutionInput,
        workflow_run_response: WorkflowRunResponse,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        stream_intermediate_steps: bool = False,
    ) -> AsyncIterator[WorkflowRunResponseEvent]:
        """Execute the steps with event-driven streaming support"""
        log_debug(f"Async steps Streaming Execution Start: {self.name}", center=True)
        log_debug(f"Steps ID: {self.steps_id}")
        log_debug(f"Stream intermediate steps: {stream_intermediate_steps}")
        log_debug(f"Total steps: {len(self.steps)}")

        # Track outputs from each step for chaining
        collected_step_outputs: List[StepOutput] = []
        steps_images = steps_input.images or []
        steps_videos = steps_input.videos or []
        steps_audio = steps_input.audio or []
        previous_step_content = None

        # Execute steps in sequence with streaming
        for step_index, step in enumerate(self.steps):
            log_debug(f"Async streaming step {step_index + 1}/{len(self.steps)}: {step.name}")

            # Create StepInput for this step
            step_input = StepInput(
                message=steps_input.message,
                message_data=steps_input.message_data,
                previous_step_content=previous_step_content,
                images=steps_images,
                videos=steps_videos,
                audio=steps_audio,
            )

            # Yield step started event
            yield StepStartedEvent(
                run_id=workflow_run_response.run_id or "",
                workflow_name=workflow_run_response.workflow_name,
                steps_name=workflow_run_response.steps_name,
                step_name=step.name,
                step_index=step_index,
                workflow_id=workflow_run_response.workflow_id,
                session_id=workflow_run_response.session_id,
            )

            step_stream = await step.aexecute(
                step_input,
                session_id=session_id,
                user_id=user_id,
                stream=True,
                stream_intermediate_steps=stream_intermediate_steps,
            )

            async for event in step_stream:
                log_debug(f"Received async event from step {step.name}: {type(event).__name__}")

                if isinstance(event, StepOutput):
                    # This is the final step output
                    step_output = event
                    log_debug(f"Received final async StepOutput from {step.name}")

                    # Collect the step output
                    collected_step_outputs.append(step_output)

                    log_debug(f"Updated previous outputs with async streaming step {step.name} results")
                    steps_images.extend(step_output.images or [])
                    steps_videos.extend(step_output.videos or [])
                    steps_audio.extend(step_output.audio or [])
                    previous_step_content = step_output.content
                    log_debug(f"Yielding async StepCompletedEvent for step: {step.name}")
                    # Yield step completed event
                    yield StepCompletedEvent(
                        run_id=workflow_run_response.run_id or "",
                        content=step_output.content,
                        workflow_name=workflow_run_response.workflow_name,
                        steps_name=self.name,
                        step_name=step.name,
                        step_index=step_index,
                        workflow_id=workflow_run_response.workflow_id,
                        session_id=workflow_run_response.session_id,
                        images=step_output.images,
                        videos=step_output.videos,
                        audio=step_output.audio,
                        step_response=step_output,
                    )
                else:
                    yield event

        # Create final output data
        final_output = {
            "steps_id": self.steps_id,
            "status": "completed",
            "total_steps": len(self.steps),
            "step_summary": [
                {
                    "step_name": step.name,
                    "step_id": step.step_id,
                    "description": step.description,
                    "executor_type": step.executor_type,
                    "executor_name": step.executor_name,
                }
                for step in self.steps
            ],
        }

        log_debug(f"Async Steps Streaming Execution End: {self.name}", center=True, symbol="*")
        workflow_run_response.content = collected_step_outputs[
            -1
        ].content  # Final workflow response output is the last step's output
        workflow_run_response.step_responses = collected_step_outputs
        workflow_run_response.images = steps_images
        workflow_run_response.videos = steps_videos
        workflow_run_response.audio = steps_audio
        workflow_run_response.extra_data = final_output
        workflow_run_response.status = RunStatus.completed

    def add_step(self, step: Step) -> None:
        """Add a step to the sequence"""
        self.steps.append(step)

    def remove_step(self, step_name: str) -> bool:
        """Remove a step from the Sequence by name"""
        for i, step in enumerate(self.steps):
            if step.name == step_name:
                del self.steps[i]
                return True
        return False

    def get_step(self, step_name: str) -> Optional[Step]:
        """Get a step by name"""
        for step in self.steps:
            if step.name == step_name:
                return step
        return None
