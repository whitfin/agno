import inspect
from dataclasses import dataclass
from typing import AsyncIterator, Awaitable, Callable, Iterator, List, Optional, Union

from agno.run.response import RunResponseEvent
from agno.run.team import TeamRunResponseEvent
from agno.run.v2.workflow import (
    LoopExecutionCompletedEvent,
    LoopExecutionStartedEvent,
    LoopIterationCompletedEvent,
    LoopIterationStartedEvent,
    WorkflowRunResponse,
    WorkflowRunResponseEvent,
)
from agno.utils.log import log_debug, logger
from agno.workflow.v2.step import Step
from agno.workflow.v2.types import StepInput, StepOutput

WorkflowSteps = List[
    Union[
        Callable[
            [StepInput], Union[StepOutput, Awaitable[StepOutput], Iterator[StepOutput], AsyncIterator[StepOutput]]
        ],
        Step,
        "Steps",  # noqa: F821
        "Loop",  # noqa: F821
        "Parallel",  # noqa: F821
        "Condition",  # noqa: F821
    ]
]


@dataclass
class Loop:
    """A loop of steps that execute in order"""

    steps: WorkflowSteps

    name: Optional[str] = None
    description: Optional[str] = None

    max_iterations: int = 3  # Default to 3
    end_condition: Optional[Callable[[List[StepOutput]], bool]] = None

    def __init__(
        self,
        steps: WorkflowSteps,
        name: Optional[str] = None,
        description: Optional[str] = None,
        max_iterations: int = 3,
        end_condition: Optional[Callable[[List[StepOutput]], bool]] = None,
    ):
        self.steps = steps
        self.name = name
        self.description = description
        self.max_iterations = max_iterations
        self.end_condition = end_condition

    def execute(
        self,
        step_input: StepInput,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[StepOutput]:
        """Execute loop steps with iteration control"""
        logger.info(f"Executing loop: {self.name} (max_iterations: {self.max_iterations})")

        all_results = []
        iteration = 0

        while iteration < self.max_iterations:
            log_debug(f"Loop iteration {iteration + 1}/{self.max_iterations}")

            # Execute all steps in this iteration
            iteration_results = []
            current_step_input = step_input

            for step in self.steps:
                if isinstance(step, Step):
                    step_output = step.execute(current_step_input, session_id=session_id, user_id=user_id)
                    iteration_results.append(step_output)

                    # Update step input for next step with previous step's content
                    current_step_input = StepInput(
                        message=step_input.message,
                        message_data=step_input.message_data,
                        previous_step_content=step_output.content,
                        images=current_step_input.images + (step_output.images or []),
                        videos=current_step_input.videos + (step_output.videos or []),
                        audio=current_step_input.audio + (step_output.audio or []),
                    )
                else:
                    raise ValueError(f"Invalid step type in loop: {type(step)}")

            all_results.append(iteration_results)
            iteration += 1

            # Check end condition
            if self.end_condition:
                try:
                    should_break = self.end_condition(iteration_results)
                    log_debug(f"End condition returned: {should_break}")
                    if should_break:
                        log_debug(f"Loop ending early due to end_condition at iteration {iteration}")
                        break
                except Exception as e:
                    logger.warning(f"End condition evaluation failed: {e}")
                    # Continue with loop if end condition fails

        log_debug(f"Loop completed after {iteration} iterations")

        # Return flattened results from all iterations
        flattened_results = []
        for iteration_results in all_results:
            flattened_results.extend(iteration_results)

        return flattened_results

    def execute_stream(
        self,
        step_input: StepInput,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        stream_intermediate_steps: bool = False,
        workflow_run_response: Optional[WorkflowRunResponse] = None,
        step_index: Optional[int] = None,
    ) -> Iterator[Union[WorkflowRunResponseEvent, StepOutput]]:
        """Execute loop steps with streaming support"""
        log_debug(f"Streaming loop: {self.name} (max_iterations: {self.max_iterations})")

        # Yield loop started event
        yield LoopExecutionStartedEvent(
            run_id=workflow_run_response.run_id or "",
            workflow_name=workflow_run_response.workflow_name or "",
            workflow_id=workflow_run_response.workflow_id or "",
            session_id=workflow_run_response.session_id or "",
            step_name=self.name,
            step_index=step_index,
            max_iterations=self.max_iterations,
        )

        all_results = []
        iteration = 0

        while iteration < self.max_iterations:
            log_debug(f"Loop iteration {iteration + 1}/{self.max_iterations}")

            # Yield iteration started event
            yield LoopIterationStartedEvent(
                run_id=workflow_run_response.run_id or "",
                workflow_name=workflow_run_response.workflow_name or "",
                workflow_id=workflow_run_response.workflow_id or "",
                session_id=workflow_run_response.session_id or "",
                step_name=self.name,
                step_index=step_index,
                iteration=iteration + 1,
                max_iterations=self.max_iterations,
            )

            # Execute all steps in this iteration
            iteration_results = []
            current_step_input = step_input

            for i, step in enumerate(self.steps):
                if isinstance(step, Step):
                    # Stream step execution
                    for event in step.execute_stream(
                        current_step_input,
                        session_id=session_id,
                        user_id=user_id,
                        stream_intermediate_steps=stream_intermediate_steps,
                        workflow_run_response=workflow_run_response,
                        step_index=step_index,
                    ):
                        if isinstance(event, StepOutput):
                            iteration_results.append(event)

                            # Update step input for next step
                            current_step_input = StepInput(
                                message=step_input.message,
                                message_data=step_input.message_data,
                                previous_step_content=event.content,
                                images=current_step_input.images + (event.images or []),
                                videos=current_step_input.videos + (event.videos or []),
                                audio=current_step_input.audio + (event.audio or []),
                            )
                        else:
                            # Yield other events (streaming content, step events, etc.)
                            yield event
                else:
                    raise ValueError(f"Invalid step type in loop: {type(step)}")

            all_results.append(iteration_results)

            # Check end condition
            should_continue = True
            if self.end_condition:
                try:
                    should_break = self.end_condition(iteration_results)
                    should_continue = not should_break
                    log_debug(f"End condition returned: {should_break}, should_continue: {should_continue}")
                except Exception as e:
                    logger.warning(f"End condition evaluation failed: {e}")

            # Yield iteration completed event
            yield LoopIterationCompletedEvent(
                run_id=workflow_run_response.run_id or "",
                workflow_name=workflow_run_response.workflow_name or "",
                workflow_id=workflow_run_response.workflow_id or "",
                session_id=workflow_run_response.session_id or "",
                step_name=self.name,
                step_index=step_index,
                iteration=iteration + 1,
                max_iterations=self.max_iterations,
                iteration_results=iteration_results,
                should_continue=should_continue,
            )

            iteration += 1

            if not should_continue:
                log_debug(f"Loop ending early due to end_condition at iteration {iteration}")
                break

        # Yield loop completed event
        yield LoopExecutionCompletedEvent(
            run_id=workflow_run_response.run_id or "",
            workflow_name=workflow_run_response.workflow_name or "",
            workflow_id=workflow_run_response.workflow_id or "",
            session_id=workflow_run_response.session_id or "",
            step_name=self.name,
            step_index=step_index,
            total_iterations=iteration,
            max_iterations=self.max_iterations,
            all_results=all_results,
        )

    async def aexecute(
        self,
        step_input: StepInput,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[StepOutput]:
        """Execute loop steps asynchronously with iteration control"""
        logger.info(f"Async executing loop: {self.name} (max_iterations: {self.max_iterations})")

        all_results = []
        iteration = 0

        while iteration < self.max_iterations:
            log_debug(f"Async loop iteration {iteration + 1}/{self.max_iterations}")

            # Execute all steps in this iteration
            iteration_results = []
            current_step_input = step_input

            for step in self.steps:
                if isinstance(step, Step):
                    step_output = await step.aexecute(current_step_input, session_id=session_id, user_id=user_id)
                    iteration_results.append(step_output)

                    # Update step input for next step with previous step's content
                    current_step_input = StepInput(
                        message=step_input.message,
                        message_data=step_input.message_data,
                        previous_step_content=step_output.content,
                        images=current_step_input.images + (step_output.images or []),
                        videos=current_step_input.videos + (step_output.videos or []),
                        audio=current_step_input.audio + (step_output.audio or []),
                    )
                else:
                    raise ValueError(f"Invalid step type in loop: {type(step)}")

            all_results.append(iteration_results)
            iteration += 1

            # Check end condition
            if self.end_condition:
                try:
                    if inspect.iscoroutinefunction(self.end_condition):
                        should_break = await self.end_condition(iteration_results)
                    else:
                        should_break = self.end_condition(iteration_results)
                    log_debug(f"End condition returned: {should_break}")
                    if should_break:
                        log_debug(f"Loop ending early due to end_condition at iteration {iteration}")
                        break
                except Exception as e:
                    logger.warning(f"End condition evaluation failed: {e}")

        log_debug(f"Async loop completed after {iteration} iterations")

        # Return flattened results from all iterations
        flattened_results = []
        for iteration_results in all_results:
            flattened_results.extend(iteration_results)

        return flattened_results

    async def aexecute_stream(
        self,
        step_input: StepInput,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        stream_intermediate_steps: bool = False,
        workflow_run_response: Optional[WorkflowRunResponse] = None,
        step_index: Optional[int] = None,
    ) -> AsyncIterator[Union[WorkflowRunResponseEvent, TeamRunResponseEvent, RunResponseEvent, StepOutput]]:
        """Execute loop steps with async streaming support"""
        log_debug(f"Async streaming loop: {self.name} (max_iterations: {self.max_iterations})")

        # Yield loop started event
        yield LoopExecutionStartedEvent(
            run_id=workflow_run_response.run_id or "",
            workflow_name=workflow_run_response.workflow_name or "",
            workflow_id=workflow_run_response.workflow_id or "",
            session_id=workflow_run_response.session_id or "",
            step_name=self.name,
            step_index=step_index,
            max_iterations=self.max_iterations,
        )

        all_results = []
        iteration = 0

        while iteration < self.max_iterations:
            log_debug(f"Async loop iteration {iteration + 1}/{self.max_iterations}")

            # Yield iteration started event
            yield LoopIterationStartedEvent(
                run_id=workflow_run_response.run_id or "",
                workflow_name=workflow_run_response.workflow_name or "",
                workflow_id=workflow_run_response.workflow_id or "",
                session_id=workflow_run_response.session_id or "",
                step_name=self.name,
                step_index=step_index,
                iteration=iteration + 1,
                max_iterations=self.max_iterations,
            )

            # Execute all steps in this iteration
            iteration_results = []
            current_step_input = step_input

            for i, step in enumerate(self.steps):
                if isinstance(step, Step):
                    # Stream step execution
                    async for event in step.aexecute_stream(
                        current_step_input,
                        session_id=session_id,
                        user_id=user_id,
                        stream_intermediate_steps=stream_intermediate_steps,
                        workflow_run_response=workflow_run_response,
                        step_index=step_index,
                    ):
                        if isinstance(event, StepOutput):
                            iteration_results.append(event)

                            # Update step input for next step
                            current_step_input = StepInput(
                                message=step_input.message,
                                message_data=step_input.message_data,
                                previous_step_content=event.content,
                                images=current_step_input.images + (event.images or []),
                                videos=current_step_input.videos + (event.videos or []),
                                audio=current_step_input.audio + (event.audio or []),
                            )
                        else:
                            # Yield other events (streaming content, step events, etc.)
                            yield event
                else:
                    raise ValueError(f"Invalid step type in loop: {type(step)}")

            all_results.append(iteration_results)

            # Check end condition
            should_continue = True
            if self.end_condition:
                try:
                    if inspect.iscoroutinefunction(self.end_condition):
                        should_break = await self.end_condition(iteration_results)
                    else:
                        should_break = self.end_condition(iteration_results)
                    should_continue = not should_break
                    log_debug(f"End condition returned: {should_break}, should_continue: {should_continue}")
                except Exception as e:
                    logger.warning(f"End condition evaluation failed: {e}")

            # Yield iteration completed event
            yield LoopIterationCompletedEvent(
                run_id=workflow_run_response.run_id or "",
                workflow_name=workflow_run_response.workflow_name or "",
                workflow_id=workflow_run_response.workflow_id or "",
                session_id=workflow_run_response.session_id or "",
                step_name=self.name,
                step_index=step_index,
                iteration=iteration + 1,
                max_iterations=self.max_iterations,
                iteration_results=iteration_results,
                should_continue=should_continue,
            )

            iteration += 1

            if not should_continue:
                log_debug(f"Loop ending early due to end_condition at iteration {iteration}")
                break

        # Yield loop completed event
        yield LoopExecutionCompletedEvent(
            run_id=workflow_run_response.run_id or "",
            workflow_name=workflow_run_response.workflow_name or "",
            workflow_id=workflow_run_response.workflow_id or "",
            session_id=workflow_run_response.session_id or "",
            step_name=self.name,
            step_index=step_index,
            total_iterations=iteration,
            max_iterations=self.max_iterations,
            all_results=all_results,
        )
