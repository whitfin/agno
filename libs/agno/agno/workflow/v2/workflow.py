from dataclasses import dataclass, field
from datetime import datetime
from os import getenv
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, Iterator, List, Literal, Optional, Union, overload
from uuid import uuid4

from pydantic import BaseModel
from typing_extensions import get_args

from agno.media import Audio, Image, Video
from agno.run.base import RunStatus
from agno.run.response import RunResponseEvent
from agno.run.team import TeamRunResponseEvent
from agno.run.v2.workflow import (
    StepCompletedEvent,
    StepStartedEvent,
    WorkflowCompletedEvent,
    WorkflowRunEvent,
    WorkflowRunResponse,
    WorkflowRunResponseEvent,
    WorkflowStartedEvent,
)
from agno.storage.base import Storage
from agno.storage.session.v2.workflow import WorkflowSession as WorkflowSessionV2
from agno.utils.log import log_debug, log_info, logger, set_log_level_to_debug, set_log_level_to_info
from agno.utils.merge_dict import merge_dictionaries
from agno.workflow.v2.step import Step
from agno.workflow.v2.steps import Steps
from agno.workflow.v2.types import WorkflowExecutionInput, StepInput
from agno.workflow.v2.parallel import Parallel

WorkflowExecutor = Callable[
    ["Workflow", WorkflowExecutionInput],
    Union[
        Any,
        Iterator[Any],
        Awaitable[Any],
        AsyncIterator[Any],
    ],
]


@dataclass
class Workflow:
    """Steps-based workflow execution"""

    # Workflow identification - make name optional with default
    name: Optional[str] = None
    workflow_id: Optional[str] = None
    description: Optional[str] = None

    # Workflow configuration
    steps: Optional[List[Union[Step, Steps, Parallel]]] = field(default_factory=list)

    # Custom executor for the workflow
    executor: Optional[WorkflowExecutor] = None

    storage: Optional[Storage] = None

    # Session management
    session_id: Optional[str] = None
    workflow_session_id: Optional[str] = None
    workflow_session_state: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None

    # Runtime state
    run_id: Optional[str] = None
    run_response: Optional[WorkflowRunResponse] = None

    # Workflow session for storage
    workflow_session: Optional[WorkflowSessionV2] = None
    debug_mode: Optional[bool] = False

    def __init__(
        self,
        workflow_id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        storage: Optional[Storage] = None,
        steps: Optional[List[Union[Step, Steps, Parallel]]
                        ] = None,  # Updated this line
        executor: Optional[WorkflowExecutor] = None,
        session_id: Optional[str] = None,
        workflow_session_state: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        debug_mode: Optional[bool] = False,
    ):
        self.workflow_id = workflow_id
        self.name = name
        self.description = description
        self.storage = storage
        self.steps = steps
        self.executor = executor
        self.session_id = session_id
        self.workflow_session_state = workflow_session_state
        self.user_id = user_id
        self.debug_mode = debug_mode

    def initialize_workflow(self):
        if self.workflow_id is None:
            self.workflow_id = str(uuid4())
            log_debug(f"Generated new workflow_id: {self.workflow_id}")

        if self.session_id is None:
            self.session_id = str(uuid4())
            log_debug(f"Generated new session_id: {self.session_id}")

        # Set storage mode to workflow_v2
        if self.storage is not None:
            self.storage.mode = "workflow_v2"

        self._update_workflow_session_state()

        # Initialize steps (whether they are Steps objects or individual Step objects)
        steps_sequences = self._get_steps_sequences()
        for steps_sequence in steps_sequences:
            steps_sequence.initialize()
            for step in steps_sequence.steps:
                active_executor = step.active_executor

                if hasattr(active_executor, "workflow_session_id"):
                    active_executor.workflow_session_id = self.session_id
                if hasattr(active_executor, "workflow_id"):
                    active_executor.workflow_id = self.workflow_id

                if self.workflow_session_state is not None:
                    # Initialize session_state if it doesn't exist
                    if hasattr(active_executor, "workflow_session_state"):
                        if active_executor.workflow_session_state is None:
                            active_executor.workflow_session_state = {}

                # If it's a team, update all members
                if hasattr(active_executor, "members"):
                    for member in active_executor.members:
                        member.workflow_session_id = self.session_id
                        member.workflow_id = self.workflow_id

                        # Initialize session_state if it doesn't exist
                        if member.workflow_session_state is None:
                            member.workflow_session_state = {}

    def _get_steps_sequences(self) -> List[Steps]:
        """Convert steps to List[Steps] format for execution"""
        if not self.steps:
            return []

        steps_sequences = []
        for item in self.steps:
            if isinstance(item, Steps):
                steps_sequences.append(item)
            elif isinstance(item, Step):
                # Convert individual Step to Steps sequence
                steps_sequence = Steps(
                    name=f"Sequence for {item.name}",
                    description=f"Auto-generated sequence for step {item.name}",
                    steps=[item],
                )
                steps_sequences.append(steps_sequence)
            # Skip Parallel objects - they should be handled directly in workflow execution
            # elif hasattr(item, 'execute') and callable(item.execute):
            #     # For Parallel objects, we don't convert them to Steps
            #     pass

        return steps_sequences

    def _set_debug(self) -> None:
        """Set debug mode and configure logging"""
        if self.debug_mode or getenv("AGNO_DEBUG", "false").lower() == "true":
            self.debug_mode = True
            set_log_level_to_debug()

            # Propagate to steps sequences
            steps_sequences = self._get_steps_sequences()
            for steps_sequence in steps_sequences:
                # Propagate to steps in sequence
                for step in steps_sequence.steps:
                    # Propagate to step executors (agents/teams)
                    if hasattr(step, "active_executor") and step.active_executor:
                        executor = step.active_executor
                        if hasattr(executor, "debug_mode"):
                            executor.debug_mode = True

                        # If it's a team, propagate to all members
                        if hasattr(executor, "members"):
                            for member in executor.members:
                                if hasattr(member, "debug_mode"):
                                    member.debug_mode = True
        else:
            set_log_level_to_info()

    def _auto_create_steps_from_single_steps(self):
        """Auto-create Steps sequences from individual Step objects"""
        if self.steps and not self.executor:
            # Don't auto-convert if we have Parallel objects - let direct execution handle it
            has_parallel = any(hasattr(item, 'execute') and callable(item.execute) and not isinstance(item, (Step, Steps)) for item in self.steps)
            if has_parallel:
                return
                
            # Check if we have any individual Step objects that need to be converted
            individual_steps = [item for item in self.steps if isinstance(item, Step)]
            if individual_steps:
                # Create a default Steps sequence
                steps_sequence_name = "Default Steps"

                # Create Steps sequence from individual steps
                auto_steps_sequence = Steps(
                    name=steps_sequence_name,
                    description=f"Auto-generated steps sequence for workflow {self.name}",
                    steps=individual_steps,
                )

                # Replace individual steps with the Steps sequence
                steps_sequences = [item for item in self.steps if isinstance(item, Steps)]
                steps_sequences.append(auto_steps_sequence)
                self.steps = steps_sequences

                log_info(f"Auto-created steps sequence for workflow {self.name} with {len(individual_steps)} steps")

    def execute(
        self, steps_sequence: Steps, execution_input: WorkflowExecutionInput, workflow_run_response: WorkflowRunResponse
    ) -> WorkflowRunResponse:
        """Execute a specific steps sequence by name synchronously"""
        self._set_debug()

        log_debug(f"Starting workflow execution: {self.run_id}")
        workflow_run_response.status = RunStatus.running

        if self.executor:
            # Execute the workflow with the custom executor
            workflow_run_response.content = self.executor(self, execution_input)
            workflow_run_response.status = RunStatus.completed

        else:
            try:
                # Execute the steps sequence synchronously - pass WorkflowRunResponse instead of context
                steps_sequence.execute(
                    steps_input=execution_input,
                    workflow_run_response=workflow_run_response,
                    session_id=self.session_id,
                    user_id=self.user_id,
                )

                # Collect updated workflow_session_state from agents after execution
                self._collect_workflow_session_state_from_agents_and_teams()

            except Exception as e:
                logger.error(f"Workflow execution failed: {e}")
                workflow_run_response.status = RunStatus.error
                workflow_run_response.content = f"Workflow execution failed: {e}"

        # Store error response
        if self.workflow_session:
            self.workflow_session.add_run(workflow_run_response)
        self.write_to_storage()

        return workflow_run_response

    def execute_stream(
        self,
        steps_sequence: Steps,
        execution_input: WorkflowExecutionInput,
        workflow_run_response: WorkflowRunResponse,
        stream_intermediate_steps: bool = False,
    ) -> Iterator[WorkflowRunResponseEvent]:
        """Execute a specific sequence steps by name with event streaming"""
        self._set_debug()

        log_debug(f"Starting workflow execution with streaming: {self.run_id}")
        workflow_run_response.status = RunStatus.running

        if self.executor:
            yield WorkflowStartedEvent(
                run_id=workflow_run_response.run_id or "",
                workflow_name=workflow_run_response.workflow_name,
                workflow_id=workflow_run_response.workflow_id,
                session_id=workflow_run_response.session_id,
            )

            import inspect

            # Execute the workflow with the custom executor
            if inspect.isgeneratorfunction(self.executor):
                content = ""
                for chunk in self.executor(self, execution_input):
                    if (
                        isinstance(chunk, tuple(get_args(RunResponseEvent)))
                        or isinstance(chunk, tuple(get_args(TeamRunResponseEvent)))
                        or isinstance(chunk, tuple(get_args(WorkflowRunResponseEvent)))
                    ):
                        # Update the run_response with the content from the result
                        if hasattr(chunk, "content") and chunk.content is not None and isinstance(chunk.content, str):
                            content += chunk.content
                    yield chunk
                workflow_run_response.content = content
            else:
                workflow_run_response.content = self.executor(self, execution_input)

            workflow_run_response.status = RunStatus.completed
            yield WorkflowCompletedEvent(
                run_id=workflow_run_response.run_id or "",
                content=workflow_run_response.content,
                workflow_name=workflow_run_response.workflow_name,
                workflow_id=workflow_run_response.workflow_id,
                session_id=workflow_run_response.session_id,
            )
        else:
            try:
                # Update steps info in the response
                workflow_run_response.steps_name = steps_sequence.name

                log_debug("Yielding WorkflowStartedEvent")
                yield WorkflowStartedEvent(
                    run_id=workflow_run_response.run_id or "",
                    workflow_name=workflow_run_response.workflow_name,
                    steps_name=steps_sequence.name,
                    workflow_id=workflow_run_response.workflow_id,
                    session_id=workflow_run_response.session_id,
                )

                # Execute the steps sequence with streaming and yield all events
                for event in steps_sequence.execute_stream(
                    steps_input=execution_input,
                    workflow_run_response=workflow_run_response,
                    session_id=self.session_id,
                    user_id=self.user_id,
                    stream_intermediate_steps=stream_intermediate_steps,
                ):
                    yield event

                log_debug("Yielding WorkflowCompletedEvent")
                # Yield workflow completed event
                yield WorkflowCompletedEvent(
                    run_id=workflow_run_response.run_id or "",
                    content=workflow_run_response.content,
                    workflow_name=workflow_run_response.workflow_name,
                    steps_name=steps_sequence.name,
                    workflow_id=workflow_run_response.workflow_id,
                    session_id=workflow_run_response.session_id,
                    step_responses=workflow_run_response.step_responses,
                    extra_data=workflow_run_response.extra_data,
                )

                # Collect updated workflow_session_state from agents after execution
                self._collect_workflow_session_state_from_agents_and_teams()

            except Exception as e:
                logger.error(f"Workflow execution failed: {e}")

                from agno.run.v2.workflow import WorkflowErrorEvent

                error_event = WorkflowErrorEvent(
                    run_id=self.run_id or "",
                    workflow_id=self.workflow_id,
                    workflow_name=self.name,
                    steps_name=steps_sequence.name,
                    session_id=self.session_id,
                    error=str(e),
                )

                yield error_event

                # Update workflow_run_response with error
                workflow_run_response.content = error_event.error
                workflow_run_response.status = RunStatus.error

        # Store the completed workflow response
        if self.workflow_session:
            self.workflow_session.add_run(workflow_run_response)

        # Save to storage after complete execution
        self.write_to_storage()

    async def aexecute(
        self, steps_sequence: Steps, execution_input: WorkflowExecutionInput, workflow_run_response: WorkflowRunResponse
    ) -> WorkflowRunResponse:
        """Execute a specific steps sequence by name synchronously"""
        log_debug(f"Starting async workflow execution: {self.run_id}")
        workflow_run_response.status = RunStatus.running

        if self.executor:
            # Execute the workflow with the custom executor
            workflow_run_response.content = self.executor(self, execution_input)
            workflow_run_response.status = RunStatus.completed

        else:
            try:
                # Execute the steps asynchronously - pass WorkflowRunResponse instead of context
                await steps_sequence.aexecute(
                    steps_input=execution_input,
                    workflow_run_response=workflow_run_response,
                    session_id=self.session_id,
                    user_id=self.user_id,
                )

                # Collect updated workflow_session_state from agents after execution
                self._collect_workflow_session_state_from_agents_and_teams()

            except Exception as e:
                logger.error(f"Workflow execution failed: {e}")

                workflow_run_response.status = RunStatus.error
                workflow_run_response.content = f"Workflow execution failed: {e}"

        # Store error response
        if self.workflow_session:
            self.workflow_session.add_run(workflow_run_response)
        self.write_to_storage()

        return workflow_run_response

    async def aexecute_stream(
        self,
        steps_sequence: Steps,
        execution_input: WorkflowExecutionInput,
        workflow_run_response: WorkflowRunResponse,
        stream_intermediate_steps: bool = False,
    ) -> AsyncIterator[WorkflowRunResponseEvent]:
        """Execute a specific steps by name with event streaming"""
        log_debug(f"Starting async workflow execution with streaming: {self.run_id}")
        workflow_run_response.status = RunStatus.running

        if self.executor:
            yield WorkflowStartedEvent(
                run_id=workflow_run_response.run_id or "",
                workflow_name=workflow_run_response.workflow_name,
                workflow_id=workflow_run_response.workflow_id,
                session_id=workflow_run_response.session_id,
            )

            import inspect

            # Execute the workflow with the custom executor
            if inspect.isasyncgenfunction(self.executor):
                content = ""
                async for chunk in self.executor(self, execution_input):
                    content += chunk
                    yield chunk
                workflow_run_response.content = content
            elif inspect.isgeneratorfunction(self.executor):
                content = ""
                for chunk in self.executor(self, execution_input):
                    if (
                        isinstance(chunk, tuple(get_args(RunResponseEvent)))
                        or isinstance(chunk, tuple(get_args(TeamRunResponseEvent)))
                        or isinstance(chunk, tuple(get_args(WorkflowRunResponseEvent)))
                    ):
                        # Update the run_response with the content from the result
                        if hasattr(chunk, "content") and chunk.content is not None and isinstance(chunk.content, str):
                            content += chunk.content
                    yield chunk
                workflow_run_response.content = content
            else:
                workflow_run_response.content = self.executor(self, execution_input)

            workflow_run_response.status = RunStatus.completed

            yield WorkflowCompletedEvent(
                run_id=workflow_run_response.run_id or "",
                content=workflow_run_response.content,
                workflow_name=workflow_run_response.workflow_name,
                workflow_id=workflow_run_response.workflow_id,
                session_id=workflow_run_response.session_id,
            )
        else:
            try:
                # Update steps info in the response
                workflow_run_response.steps_name = steps_sequence.name

                log_debug("Yielding WorkflowStartedEvent")
                yield WorkflowStartedEvent(
                    run_id=workflow_run_response.run_id or "",
                    workflow_name=workflow_run_response.workflow_name,
                    steps_name=steps_sequence.name,
                    workflow_id=workflow_run_response.workflow_id,
                    session_id=workflow_run_response.session_id,
                )

                # Execute the steps with streaming and yield all events
                async for event in steps_sequence.aexecute_stream(
                    steps_input=execution_input,
                    workflow_run_response=workflow_run_response,
                    session_id=self.session_id,
                    user_id=self.user_id,
                    stream_intermediate_steps=stream_intermediate_steps,
                ):
                    yield event

                log_debug("Yielding WorkflowCompletedEvent")
                # Yield workflow completed event
                yield WorkflowCompletedEvent(
                    run_id=workflow_run_response.run_id or "",
                    content=workflow_run_response.content,
                    workflow_name=workflow_run_response.workflow_name,
                    steps_name=steps_sequence.name,
                    workflow_id=workflow_run_response.workflow_id,
                    session_id=workflow_run_response.session_id,
                    step_responses=workflow_run_response.step_responses,
                    extra_data=workflow_run_response.extra_data,
                )

                # Collect updated workflow_session_state from agents after execution
                self._collect_workflow_session_state_from_agents_and_teams()

            except Exception as e:
                logger.error(f"Workflow execution failed: {e}")

                from agno.run.v2.workflow import WorkflowErrorEvent

                error_event = WorkflowErrorEvent(
                    run_id=self.run_id or "",
                    workflow_id=self.workflow_id,
                    workflow_name=self.name,
                    steps_name=steps_sequence.name,
                    session_id=self.session_id,
                    error=str(e),
                )
                yield error_event
                # Update workflow_run_response with error
                workflow_run_response.content = error_event.error
                workflow_run_response.event = WorkflowRunEvent.workflow_error

        # Store error response
        if self.workflow_session:
            self.workflow_session.add_run(workflow_run_response)
        self.write_to_storage()

    def _update_workflow_session_state(self):
        if not self.workflow_session_state:
            self.workflow_session_state = {}

        self.workflow_session_state.update(
            {
                "workflow_id": self.workflow_id,
                "run_id": self.run_id,
                "session_id": self.session_id,
            }
        )
        if self.name:
            self.workflow_session_state["workflow_name"] = self.name

        return self.workflow_session_state

    @overload
    def run(
        self,
        message: str = None,
        message_data: Optional[Union[BaseModel, Dict[str, Any]]] = None,
        selector: Optional[Union[str, Callable[..., str]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        audio: Optional[List[Audio]] = None,
        images: Optional[List[Image]] = None,
        videos: Optional[List[Video]] = None,
        stream: Literal[False] = False,
        stream_intermediate_steps: Optional[bool] = None,
    ) -> WorkflowRunResponse: ...

    @overload
    def run(
        self,
        message: str = None,
        message_data: Optional[Union[BaseModel, Dict[str, Any]]] = None,
        selector: Optional[Union[str, Callable[..., str]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        audio: Optional[List[Audio]] = None,
        images: Optional[List[Image]] = None,
        videos: Optional[List[Video]] = None,
        stream: Literal[True] = True,
        stream_intermediate_steps: Optional[bool] = None,
    ) -> Iterator[WorkflowRunResponseEvent]: ...

    def run(
        self,
        message: str = None,
        message_data: Optional[Union[BaseModel, Dict[str, Any]]] = None,
        selector: Optional[Union[str, Callable[..., str]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        audio: Optional[List[Audio]] = None,
        images: Optional[List[Image]] = None,
        videos: Optional[List[Video]] = None,
        stream: bool = False,
        stream_intermediate_steps: Optional[bool] = None,
    ) -> Union[WorkflowRunResponse, Iterator[WorkflowRunResponseEvent]]:
        """Execute the workflow synchronously with optional streaming"""
        log_debug(f"Workflow Run Start: {self.name}", center=True)
        log_debug(f"Stream: {stream}")

        if user_id is not None:
            self.user_id = user_id
            log_debug(f"User ID: {user_id}")
        if session_id is not None:
            self.session_id = session_id
            log_debug(f"Session ID: {session_id}")

        self._auto_create_steps_from_single_steps()
        self.run_id = str(uuid4())

        self.initialize_workflow()

        # Load or create session
        self.load_session()

        # Create workflow run response that will be updated by reference
        workflow_run_response = WorkflowRunResponse(
            run_id=self.run_id,
            session_id=self.session_id,
            workflow_id=self.workflow_id,
            workflow_name=self.name,
            created_at=int(datetime.now().timestamp()),
        )
        self.run_response = workflow_run_response

        inputs = WorkflowExecutionInput(
            message=message,
            message_data=message_data,
            audio=audio,
            images=images,
            videos=videos,
        )
        log_debug(
            f"Created Steps input with session state keys: {list(self.workflow_session_state.keys()) if self.workflow_session_state else 'None'}"
        )

        if stream:
            return self._execute_workflow_steps_stream(
            execution_input=inputs,
            workflow_run_response=workflow_run_response,
            stream_intermediate_steps=stream_intermediate_steps,
            )
        else:
            return self._execute_workflow_steps(
                execution_input=inputs,
                workflow_run_response=workflow_run_response,
            )

    @overload
    async def arun(
        self,
        message: str = None,
        message_data: Optional[Union[BaseModel, Dict[str, Any]]] = None,
        selector: Optional[Union[str, Callable[..., str]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        audio: Optional[List[Audio]] = None,
        images: Optional[List[Image]] = None,
        videos: Optional[List[Video]] = None,
        stream: Literal[False] = False,
        stream_intermediate_steps: Optional[bool] = None,
    ) -> WorkflowRunResponse: ...

    @overload
    async def arun(
        self,
        message: str = None,
        message_data: Optional[Union[BaseModel, Dict[str, Any]]] = None,
        selector: Optional[Union[str, Callable[..., str]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        audio: Optional[List[Audio]] = None,
        images: Optional[List[Image]] = None,
        videos: Optional[List[Video]] = None,
        stream: Literal[True] = True,
        stream_intermediate_steps: Optional[bool] = None,
    ) -> AsyncIterator[WorkflowRunResponseEvent]: ...

    async def arun(
        self,
        message: str = None,
        message_data: Optional[Union[BaseModel, Dict[str, Any]]] = None,
        selector: Optional[Union[str, Callable[..., str]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        audio: Optional[List[Audio]] = None,
        images: Optional[List[Image]] = None,
        videos: Optional[List[Video]] = None,
        stream: bool = False,
        stream_intermediate_steps: bool = False,
    ) -> Union[WorkflowRunResponse, AsyncIterator[WorkflowRunResponseEvent]]:
        """Execute the workflow synchronously with optional streaming"""
        log_debug(f"Async Workflow Run Start: {self.name}", center=True)
        log_debug(f"Stream: {stream}")

        # Set user_id and session_id if provided
        if user_id is not None:
            self.user_id = user_id
            log_debug(f"User ID: {user_id}")
        if session_id is not None:
            self.session_id = session_id
            log_debug(f"Session ID: {session_id}")

        self._auto_create_steps_from_single_steps()
        self.run_id = str(uuid4())

        self.initialize_workflow()

        # Load or create session
        self.load_session()

        steps_sequences = self._get_steps_sequences()
        if steps_sequences:
            selected_steps_name = self._get_steps_sequence_name(
                selector=selector, message=message, message_data=message_data, user_id=user_id, session_id=session_id
            )

            steps_sequence = self.get_steps_sequence(selected_steps_name)
            log_debug(f"Steps sequence found with {len(steps_sequence.steps)} steps")
            if not steps_sequence:
                raise ValueError(f"Steps sequence '{selected_steps_name}' not found")
        else:
            steps_sequence = None
            selected_steps_name = "Custom Executor"

        # Create workflow run response that will be updated by reference
        workflow_run_response = WorkflowRunResponse(
            run_id=self.run_id,
            session_id=self.session_id,
            workflow_id=self.workflow_id,
            workflow_name=self.name,
            steps_name=selected_steps_name,
            created_at=int(datetime.now().timestamp()),
        )
        self.run_response = workflow_run_response

        inputs = WorkflowExecutionInput(
            message=message,
            message_data=message_data,
            audio=audio,
            images=images,
            videos=videos,
        )
        log_debug(
            f"Created async steps input with session state keys: {list(self.workflow_session_state.keys()) if self.workflow_session_state else 'None'}"
        )

        if stream:
            return self.aexecute_stream(
                steps_sequence=steps_sequence,
                execution_input=inputs,
                workflow_run_response=workflow_run_response,
                stream_intermediate_steps=stream_intermediate_steps,
            )
        else:
            return await self.aexecute(
                steps_sequence=steps_sequence, execution_input=inputs, workflow_run_response=workflow_run_response
            )

    def _get_steps_sequence_name(
        self,
        selector: Optional[Union[str, Callable[..., str]]] = None,
        message: Optional[str] = None,
        message_data: Optional[Union[BaseModel, Dict[str, Any]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """Get steps sequence name from selector or default to first sequence"""
        steps_sequences = self._get_steps_sequences()

        if selector:
            if isinstance(selector, str):
                # String selector - direct steps sequence name
                selected_name = selector
                log_debug(f"Using string selector: {selected_name}")
            elif callable(selector):
                # Callable selector - call with context
                try:
                    selected_name = selector(
                        message=message,
                        message_data=message_data,
                        user_id=user_id,
                        session_id=session_id,
                        steps_sequences=[s.name for s in steps_sequences],
                        workflow=self,
                    )
                    log_debug(f"Callable selector returned: {selected_name}")
                except Exception as e:
                    log_debug(f"Selector function failed: {e}")
                    raise ValueError(f"Steps sequence selector function failed: {e}")
            else:
                raise ValueError(f"Invalid selector type: {type(selector)}. Must be string or callable.")

            # Validate selected steps sequence exists
            target_steps_sequence = self.get_steps_sequence(selected_name)
            if not target_steps_sequence:
                available_sequences = [seq.name for seq in steps_sequences]
                raise ValueError(
                    f"Selector returned invalid steps sequence '{selected_name}'. Available sequences: {available_sequences}"
                )
            return selected_name
        else:
            # Default to first steps sequence if no selector provided
            if not steps_sequences:
                raise ValueError("No steps sequences available in workflow")
            selected_steps_name = steps_sequences[0].name
            log_debug(f"No selector provided, defaulting to first steps sequence: {selected_steps_name}")
            return selected_steps_name

    def get_workflow_session(self) -> WorkflowSessionV2:
        """Get a WorkflowSessionV2 object for storage"""
        workflow_data = {}
        steps_sequences = self._get_steps_sequences()
        if steps_sequences:
            workflow_data["steps_sequences"] = [
                {
                    "name": steps_sequence.name,
                    "description": steps_sequence.description,
                    "steps": [
                        {
                            "name": step.name,
                            "description": step.description,
                            "executor_type": step.executor_type,
                        }
                        for step in steps_sequence.steps
                    ],
                }
                for steps_sequence in steps_sequences
            ]
        elif self.executor:
            workflow_data["executor"] = self.executor.__name__

        return WorkflowSessionV2(
            session_id=self.session_id,
            user_id=self.user_id,
            workflow_id=self.workflow_id,
            workflow_name=self.name,
            runs=self.workflow_session.runs if self.workflow_session else [],
            workflow_data=workflow_data,
            session_data={},
        )

    def load_workflow_session(self, session: WorkflowSessionV2):
        """Load workflow session from storage"""
        if self.workflow_id is None and session.workflow_id is not None:
            self.workflow_id = session.workflow_id
        if self.user_id is None and session.user_id is not None:
            self.user_id = session.user_id
        if self.session_id is None and session.session_id is not None:
            self.session_id = session.session_id
        if self.name is None and session.workflow_name is not None:
            self.name = session.workflow_name

        self.workflow_session = session
        log_debug(f"Loaded WorkflowSessionV2: {session.session_id}")

    def read_from_storage(self) -> Optional[WorkflowSessionV2]:
        """Load the WorkflowSessionV2 from storage"""
        if self.storage is not None and self.session_id is not None:
            session = self.storage.read(session_id=self.session_id)
            if session and isinstance(session, WorkflowSessionV2):
                self.load_workflow_session(session)
                return session
        return None

    def write_to_storage(self) -> Optional[WorkflowSessionV2]:
        """Save the WorkflowSessionV2 to storage"""
        if self.storage is not None:
            session_to_save = self.get_workflow_session()
            saved_session = self.storage.upsert(session=session_to_save)
            if saved_session and isinstance(saved_session, WorkflowSessionV2):
                self.workflow_session = saved_session
                return saved_session
        return None

    def load_session(self, force: bool = False) -> Optional[str]:
        """Load an existing session from storage or create a new one"""
        log_debug(f"Current session_id: {self.session_id}")

        if self.workflow_session is not None and not force:
            if self.session_id is not None and self.workflow_session.session_id == self.session_id:
                log_debug("Using existing workflow session")
                return self.workflow_session.session_id

        if self.storage is not None:
            # Try to load existing session
            log_debug(f"Reading WorkflowSessionV2: {self.session_id}")
            existing_session = self.read_from_storage()

            # Create new session if it doesn't exist
            if existing_session is None:
                log_debug("Creating new WorkflowSessionV2")
                self.workflow_session = WorkflowSessionV2(
                    session_id=self.session_id,  # type: ignore
                    user_id=self.user_id,
                    workflow_id=self.workflow_id,
                    workflow_name=self.name,
                )
                saved_session = self.write_to_storage()
                if saved_session is None:
                    raise Exception("Failed to create new WorkflowSessionV2 in storage")
                log_debug(f"Created WorkflowSessionV2: {saved_session.session_id}")

        return self.session_id

    def new_session(self) -> None:
        """Create a new workflow session"""
        log_debug("Creating new workflow session")

        self.workflow_session = None
        self.session_id = str(uuid4())

        log_debug(f"New session ID: {self.session_id}")
        self.load_session(force=True)

    def print_response(
        self,
        message: Optional[str] = None,
        message_data: Optional[Union[BaseModel, Dict[str, Any]]] = None,
        selector: Optional[Union[str, Callable[..., str]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        audio: Optional[List[Audio]] = None,
        images: Optional[List[Image]] = None,
        videos: Optional[List[Video]] = None,
        stream: bool = False,
        stream_intermediate_steps: bool = False,
        markdown: bool = True,
        show_time: bool = True,
        show_step_details: bool = True,
        console: Optional[Any] = None,
    ) -> None:
        """Print workflow execution with rich formatting and optional streaming

        Args:
            message: The main query/input for the workflow
            message_data: Attached message data to the input
            selector: Either callable or string. If string, it will be used as the steps name. If callable, it will be used to select the steps.
            user_id: User ID
            session_id: Session ID
            audio: Audio input
            images: Image input
            videos: Video input
            stream: Whether to stream the response content
            stream_intermediate_steps: Whether to stream intermediate steps
            markdown: Whether to render content as markdown
            show_time: Whether to show execution time
            show_step_details: Whether to show individual step outputs
            console: Rich console instance (optional)
        """

        self._auto_create_steps_from_single_steps()

        if stream:
            self._print_response_stream(
                message=message,
                message_data=message_data,
                selector=selector,
                user_id=user_id,
                session_id=session_id,
                audio=audio,
                images=images,
                videos=videos,
                stream_intermediate_steps=stream_intermediate_steps,
                markdown=markdown,
                show_time=show_time,
                show_step_details=show_step_details,
                console=console,
            )
        else:
            self._print_response(
                message=message,
                message_data=message_data,
                selector=selector,
                user_id=user_id,
                session_id=session_id,
                audio=audio,
                images=images,
                videos=videos,
                markdown=markdown,
                show_time=show_time,
                show_step_details=show_step_details,
                console=console,
            )

    def _print_response(
        self,
        message: str,
        message_data: Optional[Union[BaseModel, Dict[str, Any]]] = None,
        selector: Optional[Union[str, Callable[..., str]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        audio: Optional[List[Audio]] = None,
        images: Optional[List[Image]] = None,
        videos: Optional[List[Video]] = None,
        markdown: bool = True,
        show_time: bool = True,
        show_step_details: bool = True,
        console: Optional[Any] = None,
    ) -> None:
        """Print workflow execution with rich formatting (non-streaming)"""
        from rich.live import Live
        from rich.markdown import Markdown
        from rich.status import Status
        from rich.text import Text

        from agno.utils.response import create_panel
        from agno.utils.timer import Timer

        if console is None:
            from agno.cli.console import console

        # Check if we have direct execution (mixed step types) or old-style Steps sequences
        has_direct_execution = any(isinstance(item, (Step, Parallel))
                                for item in (self.steps or []))

        if has_direct_execution:
            # Direct execution mode - skip Steps sequence validation
            workflow_info = f"""**Workflow:** {self.name}"""
            if self.description:
                workflow_info += f"""\n\n**Description:** {self.description}"""
            workflow_info += f"""\n\n**Steps:** {len(self.steps)} steps (direct execution)"""
        else:
            # Original Steps sequence mode
            steps_sequences = self._get_steps_sequences()
            if not steps_sequences and not self.executor:
                console.print(
                    "[red]No steps sequences available in this workflow[/red]")
                return

            if steps_sequences:
                steps_sequence_name = self._get_steps_sequence_name(
                    selector=selector, message=message, message_data=message_data, user_id=user_id, session_id=session_id
                )
                steps_sequence = self.get_steps_sequence(steps_sequence_name)
                if not steps_sequence:
                    console.print(
                        f"[red]Steps sequence '{steps_sequence_name}' not found[/red]")
                    return
            else:
                # For workflows with custom executor but no steps sequences
                steps_sequence_name = "Custom Executor"
                steps_sequence = None

            workflow_info = f"""**Workflow:** {self.name}"""
            if self.description:
                workflow_info += f"""\n\n**Description:** {self.description}"""
            if steps_sequence:
                if steps_sequence_name and steps_sequence_name != "Default Steps":
                    workflow_info += f"""\n\n**Steps Sequence:** {steps_sequence_name}"""
                workflow_info += f"""\n\n**Steps:** {len(steps_sequence.steps)} steps"""

        # Show workflow info
        media_info = []
        if audio:
            media_info.append(f"Audio files: {len(audio)}")
        if images:
            media_info.append(f"Images: {len(images)}")
        if videos:
            media_info.append(f"Videos: {len(videos)}")

        if message:
            workflow_info += f"""\n\n**Message:** {message}"""
        if message_data:
            if isinstance(message_data, BaseModel):
                data_display = message_data.model_dump_json(
                    indent=2, exclude_none=True)
            elif isinstance(message_data, dict):
                import json

                data_display = json.dumps(message_data, indent=2, default=str)
            else:
                data_display = str(message_data)
            workflow_info += f"""\n\n**Structured Data:**\n```json\n{data_display}\n```"""
        if user_id:
            workflow_info += f"""\n\n**User ID:** {user_id}"""
        if session_id:
            workflow_info += f"""\n\n**Session ID:** {session_id}"""
        workflow_info = workflow_info.strip()

        workflow_panel = create_panel(
            content=Markdown(workflow_info) if markdown else workflow_info,
            title="Workflow Information",
            border_style="cyan",
        )
        console.print(workflow_panel)

        # Start timer
        response_timer = Timer()
        response_timer.start()

        with Live(console=console) as live_log:
            status = Status("Starting workflow...", spinner="dots")
            live_log.update(status)

            try:
                # Execute workflow and get the response directly
                workflow_response: WorkflowRunResponse = self.run(
                    message=message,
                    selector=selector,
                    message_data=message_data,
                    user_id=user_id,
                    session_id=session_id,
                    audio=audio,
                    images=images,
                    videos=videos,
                )

                response_timer.stop()

                # Show individual step responses if available
                if show_step_details and workflow_response.step_responses:
                    for i, step_output in enumerate(workflow_response.step_responses):
                        if step_output.content:
                            step_panel = create_panel(
                                content=Markdown(
                                    step_output.content) if markdown else step_output.content,
                                title=f"Step {i + 1}: {step_output.step_name} (Completed)",
                                border_style="green",
                            )
                            console.print(step_panel)

                # Show final summary
                if workflow_response.extra_data:
                    status = workflow_response.status.value
                    summary_content = ""
                    summary_content += f"""\n\n**Status:** {status}"""
                    summary_content += f"""\n\n**Steps Completed:** {len(workflow_response.step_responses) if workflow_response.step_responses else 0}"""
                    summary_content = summary_content.strip()

                    summary_panel = create_panel(
                        content=Markdown(
                            summary_content) if markdown else summary_content,
                        title="Execution Summary",
                        border_style="blue",
                    )
                    console.print(summary_panel)

                # Final completion message
                if show_time:
                    completion_text = Text(
                        f"Completed in {response_timer.elapsed:.1f}s", style="bold green")
                    console.print(completion_text)

            except Exception as e:
                import traceback

                traceback.print_exc()
                response_timer.stop()
                error_panel = create_panel(
                    content=f"Workflow execution failed: {str(e)}", title="Execution Error", border_style="red"
                )
                console.print(error_panel)

    def _print_response_stream(
        self,
        message: str,
        message_data: Optional[Union[BaseModel, Dict[str, Any]]] = None,
        selector: Optional[Union[str, Callable[..., str]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        audio: Optional[List[Audio]] = None,
        images: Optional[List[Image]] = None,
        videos: Optional[List[Video]] = None,
        stream_intermediate_steps: bool = False,
        markdown: bool = True,
        show_time: bool = True,
        show_step_details: bool = True,
        console: Optional[Any] = None,
    ) -> None:
        """Print workflow execution with clean streaming - green step blocks displayed once"""
        from rich.console import Group
        from rich.live import Live
        from rich.markdown import Markdown
        from rich.status import Status
        from rich.text import Text

        from agno.utils.response import create_panel
        from agno.utils.timer import Timer

        if console is None:
            from agno.cli.console import console

        steps_sequences = self._get_steps_sequences()
        if not steps_sequences and not self.executor:
            console.print(
                "[red]No steps sequences available in this workflow[/red]")
            return

        if steps_sequences:
            steps_sequence_name = self._get_steps_sequence_name(
                selector=selector, message=message, message_data=message_data, user_id=user_id, session_id=session_id
            )
            steps_sequence = self.get_steps_sequence(steps_sequence_name)
            if not steps_sequence:
                console.print(
                    f"[red]Steps sequence '{steps_sequence_name}' not found[/red]")
                return
        else:
            # For workflows with custom executor but no steps sequences
            steps_sequence_name = "Custom Executor"
            steps_sequence = None

        # Show workflow info (same as before)
        media_info = []
        if audio:
            media_info.append(f"Audio files: {len(audio)}")
        if images:
            media_info.append(f"Images: {len(images)}")
        if videos:
            media_info.append(f"Videos: {len(videos)}")

        workflow_info = f"""**Workflow:** {self.name}"""
        if self.description:
            workflow_info += f"""\n\n**Description:** {self.description}"""
        if steps_sequence:
            if steps_sequence_name and steps_sequence_name != "Default Steps":
                workflow_info += f"""\n\n**Steps Sequence:** {steps_sequence_name}"""
            workflow_info += f"""\n\n**Steps:** {len(steps_sequence.steps)} steps"""
        if message:
            workflow_info += f"""\n\n**Message:** {message}"""
        if message_data:
            if isinstance(message_data, BaseModel):
                data_display = message_data.model_dump_json(indent=2, exclude_none=True)
            elif isinstance(message_data, dict):
                import json

                data_display = json.dumps(message_data, indent=2, default=str)
            else:
                data_display = str(message_data)
            workflow_info += f"""\n\n**Structured Data:**\n```json\n{data_display}\n```"""
        if user_id:
            workflow_info += f"""\n\n**User ID:** {user_id}"""
        if session_id:
            workflow_info += f"""\n\n**Session ID:** {session_id}"""
        workflow_info = workflow_info.strip()

        workflow_panel = create_panel(
            content=Markdown(workflow_info) if markdown else workflow_info,
            title="Workflow Information",
            border_style="cyan",
        )
        console.print(workflow_panel)

        # Start timer
        response_timer = Timer()
        response_timer.start()

        # Streaming execution variables
        current_step_content = ""
        current_step_name = ""
        current_step_index = 0
        step_responses = []
        step_started_printed = False

        with Live(console=console, refresh_per_second=10) as live_log:
            status = Status("Starting workflow...", spinner="dots")
            live_log.update(status)

            try:
                for response in self.run(
                    message=message,
                    message_data=message_data,
                    selector=selector,
                    user_id=user_id,
                    session_id=session_id,
                    audio=audio,
                    images=images,
                    videos=videos,
                    stream=True,
                    stream_intermediate_steps=stream_intermediate_steps,
                ):
                    # Handle the new event types
                    if isinstance(response, WorkflowStartedEvent):
                        status.update("Workflow started...")
                        live_log.update(status)

                    elif isinstance(response, StepStartedEvent):
                        current_step_name = response.step_name or "Unknown"
                        current_step_index = response.step_index or 0
                        current_step_content = ""
                        step_started_printed = False
                        status.update(f"Starting step {current_step_index + 1}: {current_step_name}...")
                        live_log.update(status)

                    elif isinstance(response, StepCompletedEvent):
                        step_name = response.step_name or "Unknown"
                        step_index = response.step_index or 0

                        status.update(f"Completed step {step_index + 1}: {step_name}")

                        if response.content:
                            step_responses.append(
                                {
                                    "step_name": step_name,
                                    "step_index": step_index,
                                    "content": response.content,
                                    "event": response.event,
                                }
                            )

                        # Print the final step result in green (only once)
                        if show_step_details and current_step_content and not step_started_printed:
                            live_log.update(status, refresh=True)

                            final_step_panel = create_panel(
                                content=Markdown(current_step_content) if markdown else current_step_content,
                                title=f"Step {step_index + 1}: {step_name} (Completed)",
                                border_style="green",
                            )
                            console.print(final_step_panel)
                            step_started_printed = True

                    elif isinstance(response, WorkflowCompletedEvent):
                        status.update("Workflow completed!")
                        live_log.update(status, refresh=True)

                        # Show final summary
                        if response.extra_data:
                            status = response.status
                            summary_content = ""
                            if steps_sequence_name != "Default Steps":
                                summary_content += f"""\n\n**Steps Sequence:** {steps_sequence_name}"""
                            summary_content += f"""\n\n**Status:** {status}"""
                            summary_content += f"""\n\n**Steps Completed:** {len(response.step_responses) if response.step_responses else 0}"""
                            summary_content = summary_content.strip()

                            summary_panel = create_panel(
                                content=Markdown(summary_content) if markdown else summary_content,
                                title="Execution Summary",
                                border_style="blue",
                            )
                            console.print(summary_panel)

                    else:
                        if isinstance(response, str):
                            response_str = response
                        else:
                            from agno.run.response import RunResponseContentEvent

                            # Check if this is a streaming content event from agent or team
                            if isinstance(
                                response,
                                (RunResponseContentEvent, WorkflowRunResponseEvent),
                            ):
                                # Extract the content from the streaming event
                                response_str = response.content
                            else:
                                continue

                        # Filter out empty responses and add to current step content
                        if response_str and response_str.strip():
                            current_step_content += response_str

                            # Live update the step panel with streaming content
                            if show_step_details and not step_started_printed:
                                # Show the streaming content live in green panel
                                live_step_panel = create_panel(
                                    content=Markdown(current_step_content) if markdown else current_step_content,
                                    title=f"Step {current_step_index + 1}: {current_step_name} (Streaming...)",
                                    border_style="green",
                                )

                                # Create group with status and current step content
                                group = Group(status, live_step_panel)
                                live_log.update(group)

                response_timer.stop()

                # Final completion message
                if show_time:
                    completion_text = Text(f"Completed in {response_timer.elapsed:.1f}s", style="bold green")
                    console.print(completion_text)

            except Exception as e:
                response_timer.stop()
                error_panel = create_panel(
                    content=f"Workflow execution failed: {str(e)}", title="Execution Error", border_style="red"
                )
                console.print(error_panel)

    async def aprint_response(
        self,
        message: Optional[str] = None,
        message_data: Optional[Union[BaseModel, Dict[str, Any]]] = None,
        selector: Optional[Union[str, Callable[..., str]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        audio: Optional[List[Audio]] = None,
        images: Optional[List[Image]] = None,
        videos: Optional[List[Video]] = None,
        stream: bool = False,
        stream_intermediate_steps: bool = False,
        markdown: bool = True,
        show_time: bool = True,
        show_step_details: bool = True,
        console: Optional[Any] = None,
    ) -> None:
        """Print workflow execution with rich formatting and optional streaming

        Args:
            message: The main message/input for the workflow
            message_data: Attached message data to the input
            selector: Either callable or string. If string, it will be used as the steps name. If callable, it will be used to select the steps sequence.
            user_id: User ID
            session_id: Session ID
            audio: Audio input
            images: Image input
            videos: Video input
            stream_intermediate_steps: Whether to stream intermediate steps
            stream: Whether to stream the response content
            markdown: Whether to render content as markdown
            show_time: Whether to show execution time
            show_step_details: Whether to show individual step outputs
            console: Rich console instance (optional)
        """
        self._auto_create_steps_from_single_steps()
        if stream:
            await self._aprint_response_stream(
                message=message,
                message_data=message_data,
                selector=selector,
                user_id=user_id,
                session_id=session_id,
                audio=audio,
                images=images,
                videos=videos,
                stream_intermediate_steps=stream_intermediate_steps,
                markdown=markdown,
                show_time=show_time,
                show_step_details=show_step_details,
                console=console,
            )
        else:
            await self._aprint_response(
                message=message,
                message_data=message_data,
                selector=selector,
                user_id=user_id,
                session_id=session_id,
                audio=audio,
                images=images,
                videos=videos,
                markdown=markdown,
                show_time=show_time,
                show_step_details=show_step_details,
                console=console,
            )

    async def _aprint_response(
        self,
        message: str,
        message_data: Optional[Union[BaseModel, Dict[str, Any]]] = None,
        selector: Optional[Union[str, Callable[..., str]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        audio: Optional[List[Audio]] = None,
        images: Optional[List[Image]] = None,
        videos: Optional[List[Video]] = None,
        markdown: bool = True,
        show_time: bool = True,
        show_step_details: bool = True,
        console: Optional[Any] = None,
    ) -> None:
        """Print workflow execution with rich formatting (non-streaming)"""
        from rich.live import Live
        from rich.markdown import Markdown
        from rich.status import Status
        from rich.text import Text

        from agno.utils.response import create_panel
        from agno.utils.timer import Timer

        if console is None:
            from agno.cli.console import console

        # Validate steps configuration based on trigger type
        steps_sequences = self._get_steps_sequences()
        if not steps_sequences and not self.executor:
            console.print(
                "[red]No steps sequences available in this workflow[/red]")
            return

        if steps_sequences:
            steps_sequence_name = self._get_steps_sequence_name(
                selector=selector, message=message, message_data=message_data, user_id=user_id, session_id=session_id
            )
            steps_sequence = self.get_steps_sequence(steps_sequence_name)
            if not steps_sequence:
                console.print(
                    f"[red]Steps sequence '{steps_sequence_name}' not found[/red]")
                return
        else:
            # For workflows with custom executor but no steps sequences
            steps_sequence_name = "Custom Executor"
            steps_sequence = None

        # Show workflow info
        media_info = []
        if audio:
            media_info.append(f"Audio files: {len(audio)}")
        if images:
            media_info.append(f"Images: {len(images)}")
        if videos:
            media_info.append(f"Videos: {len(videos)}")

        workflow_info = f"""**Workflow:** {self.name}"""
        if self.description:
            workflow_info += f"""\n\n**Description:** {self.description}"""
        if steps_sequence_name != "Default Steps":
            workflow_info += f"""\n\n**Steps Sequence:** {steps_sequence_name}"""
        workflow_info += f"""\n\n**Steps:** {len(steps_sequence.steps)} steps"""
        if message:
            workflow_info += f"""\n\n**Message:** {message}"""
        if message_data:
            if isinstance(message_data, BaseModel):
                data_display = message_data.model_dump_json(indent=2, exclude_none=True)
            elif isinstance(message_data, dict):
                import json

                data_display = json.dumps(message_data, indent=2, default=str)
            else:
                data_display = str(message_data)
            workflow_info += f"""\n\n**Structured Data:**\n```json\n{data_display}\n```"""
        if user_id:
            workflow_info += f"""\n\n**User ID:** {user_id}"""
        if session_id:
            workflow_info += f"""\n\n**Session ID:** {session_id}"""
        workflow_info = workflow_info.strip()

        workflow_panel = create_panel(
            content=Markdown(workflow_info) if markdown else workflow_info,
            title="Workflow Information",
            border_style="cyan",
        )
        console.print(workflow_panel)

        # Start timer
        response_timer = Timer()
        response_timer.start()

        with Live(console=console) as live_log:
            status = Status("Starting async workflow...\n", spinner="dots")
            live_log.update(status)

            try:
                # Execute workflow and get the response directly
                workflow_response: WorkflowRunResponse = await self.arun(
                    message=message,
                    message_data=message_data,
                    selector=selector,
                    user_id=user_id,
                    session_id=session_id,
                    audio=audio,
                    images=images,
                    videos=videos,
                )

                response_timer.stop()

                # Show individual step responses if available
                if show_step_details and workflow_response.step_responses:
                    for i, step_output in enumerate(workflow_response.step_responses):
                        if step_output.content:
                            step_panel = create_panel(
                                content=Markdown(step_output.content) if markdown else step_output.content,
                                title=f"Step {i + 1}: {step_output.step_name} (Completed)",
                                border_style="green",
                            )
                            console.print(step_panel)

                # Show final summary
                if workflow_response.extra_data:
                    status = workflow_response.status.value
                    summary_content = ""
                    if steps_sequence_name != "Default Steps":
                        summary_content += f"""\n\n**Steps Sequence:** {steps_sequence_name}"""
                    summary_content += f"""\n\n**Status:** {status}"""
                    summary_content += f"""\n\n**Steps Completed:** {len(workflow_response.step_responses) if workflow_response.step_responses else 0}"""
                    summary_content = summary_content.strip()

                    summary_panel = create_panel(
                        content=Markdown(summary_content) if markdown else summary_content,
                        title="Execution Summary",
                        border_style="blue",
                    )
                    console.print(summary_panel)

                # Final completion message
                if show_time:
                    completion_text = Text(f"Completed in {response_timer.elapsed:.1f}s", style="bold green")
                    console.print(completion_text)

            except Exception as e:
                response_timer.stop()
                error_panel = create_panel(
                    content=f"Workflow execution failed: {str(e)}", title="Execution Error", border_style="red"
                )
                console.print(error_panel)

    async def _aprint_response_stream(
        self,
        message: str,
        message_data: Optional[Union[BaseModel, Dict[str, Any]]] = None,
        selector: Optional[Union[str, Callable[..., str]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        audio: Optional[List[Audio]] = None,
        images: Optional[List[Image]] = None,
        videos: Optional[List[Video]] = None,
        stream_intermediate_steps: bool = False,
        markdown: bool = True,
        show_time: bool = True,
        show_step_details: bool = True,
        console: Optional[Any] = None,
    ) -> None:
        """Print workflow execution with clean streaming - green step blocks displayed once"""
        from rich.console import Group
        from rich.live import Live
        from rich.markdown import Markdown
        from rich.status import Status
        from rich.text import Text

        from agno.utils.response import create_panel
        from agno.utils.timer import Timer

        if console is None:
            from agno.cli.console import console

        steps_sequences = self._get_steps_sequences()
        if not steps_sequences and not self.executor:
            console.print(
                "[red]No steps sequences available in this workflow[/red]")
            return

        if steps_sequences:
            steps_sequence_name = self._get_steps_sequence_name(
                selector=selector, message=message, message_data=message_data, user_id=user_id, session_id=session_id
            )
            steps_sequence = self.get_steps_sequence(steps_sequence_name)
            if not steps_sequence:
                console.print(
                    f"[red]Steps sequence '{steps_sequence_name}' not found[/red]")
                return
        else:
            # For workflows with custom executor but no steps sequences
            steps_sequence_name = "Custom Executor"
            steps_sequence = None

        # Show workflow info (same as before)
        media_info = []
        if audio:
            media_info.append(f"Audio files: {len(audio)}")
        if images:
            media_info.append(f"Images: {len(images)}")
        if videos:
            media_info.append(f"Videos: {len(videos)}")

        workflow_info = f"""**Workflow:** {self.name}"""
        if self.description:
            workflow_info += f"""\n\n**Description:** {self.description}"""
        if steps_sequence_name != "Default Steps":
            workflow_info += f"""\n\n**Steps Sequence:** {steps_sequence_name}"""
        workflow_info += f"""\n\n**Steps:** {len(steps_sequence.steps)} steps"""
        if message:
            workflow_info += f"""\n\n**Message:** {message}"""
        if message_data:
            if isinstance(message_data, BaseModel):
                data_display = message_data.model_dump_json(indent=2, exclude_none=True)
            elif isinstance(message_data, dict):
                import json

                data_display = json.dumps(message_data, indent=2, default=str)
            else:
                data_display = str(message_data)
            workflow_info += f"""\n\n**Structured Data:**\n```json\n{data_display}\n```"""
        if user_id:
            workflow_info += f"""\n\n**User ID:** {user_id}"""
        if session_id:
            workflow_info += f"""\n\n**Session ID:** {session_id}"""
        workflow_info = workflow_info.strip()

        workflow_panel = create_panel(
            content=Markdown(workflow_info) if markdown else workflow_info,
            title="Workflow Information",
            border_style="cyan",
        )
        console.print(workflow_panel)

        # Start timer
        response_timer = Timer()
        response_timer.start()

        # Streaming execution variables
        current_step_content = ""
        current_step_name = ""
        current_step_index = 0
        step_responses = []
        step_started_printed = False

        with Live(console=console, refresh_per_second=10) as live_log:
            status = Status("Starting async workflow...", spinner="dots")
            live_log.update(status)

            try:
                async for response in await self.arun(
                    message=message,
                    message_data=message_data,
                    selector=selector,
                    user_id=user_id,
                    session_id=session_id,
                    audio=audio,
                    images=images,
                    videos=videos,
                    stream=True,
                    stream_intermediate_steps=stream_intermediate_steps,
                ):
                    # Handle the new event types
                    if isinstance(response, WorkflowStartedEvent):
                        status.update("Workflow started...")
                        live_log.update(status)

                    elif isinstance(response, StepStartedEvent):
                        current_step_name = response.step_name or "Unknown"
                        current_step_index = response.step_index or 0
                        current_step_content = ""
                        step_started_printed = False
                        status.update(f"Starting step {current_step_index + 1}: {current_step_name}...")
                        live_log.update(status)

                    elif isinstance(response, StepCompletedEvent):
                        step_name = response.step_name or "Unknown"
                        step_index = response.step_index or 0

                        status.update(f"Completed step {step_index + 1}: {step_name}")

                        if response.content:
                            step_responses.append(
                                {
                                    "step_name": step_name,
                                    "step_index": step_index,
                                    "content": response.content,
                                    "event": response.event,
                                }
                            )

                        # Print the final step result in green (only once)
                        if show_step_details and current_step_content and not step_started_printed:
                            live_log.update(status, refresh=True)

                            final_step_panel = create_panel(
                                content=Markdown(current_step_content) if markdown else current_step_content,
                                title=f"Step {step_index + 1}: {step_name} (Completed)",
                                border_style="green",
                            )
                            console.print(final_step_panel)
                            step_started_printed = True

                    elif isinstance(response, WorkflowCompletedEvent):
                        status.update("Workflow completed!")
                        live_log.update(status, refresh=True)

                        # Show final summary
                        if response.extra_data:
                            status = response.status
                            summary_content = ""
                            if steps_sequence_name != "Default Steps":
                                summary_content += f"""\n\n**Step Sequence:** {steps_sequence_name}"""
                            summary_content += f"""\n\n**Status:** {status}"""
                            summary_content += f"""\n\n**Steps Completed:** {len(response.step_responses) if response.step_responses else 0}"""
                            summary_content = summary_content.strip()

                            summary_panel = create_panel(
                                content=Markdown(summary_content) if markdown else summary_content,
                                title="Execution Summary",
                                border_style="blue",
                            )
                            console.print(summary_panel)

                    else:
                        response_str = None

                        if isinstance(response, str):
                            response_str = response
                        else:
                            from agno.run.response import RunResponseContentEvent

                            # Check if this is a streaming content event from agent or team
                            if isinstance(
                                response,
                                (RunResponseContentEvent, WorkflowRunResponseEvent),
                            ):
                                # Extract the content from the streaming event
                                response_str = response.content
                            else:
                                continue

                        # Filter out empty responses and add to current step content
                        if response_str and response_str.strip():
                            current_step_content += response_str

                            # Live update the step panel with streaming content
                            if show_step_details and not step_started_printed:
                                # Show the streaming content live in green panel
                                live_step_panel = create_panel(
                                    content=Markdown(current_step_content) if markdown else current_step_content,
                                    title=f"Step {current_step_index + 1}: {current_step_name} (Streaming...)",
                                    border_style="green",
                                )

                                # Create group with status and current step content
                                group = Group(status, live_step_panel)
                                live_log.update(group)

                response_timer.stop()

                # Final completion message
                if show_time:
                    completion_text = Text(f"Completed in {response_timer.elapsed:.1f}s", style="bold green")
                    console.print(completion_text)

            except Exception as e:
                response_timer.stop()
                error_panel = create_panel(
                    content=f"Workflow execution failed: {str(e)}", title="Execution Error", border_style="red"
                )
                console.print(error_panel)

    def add_steps_sequence(self, steps_sequence: Steps) -> None:
        """Add a steps sequence to the workflow"""
        if self.steps is None:
            self.steps = []
        self.steps.append(steps_sequence)

    def remove_steps_sequence(self, steps_sequence_name: str) -> bool:
        """Remove a steps sequence by name"""
        if not self.steps:
            return False

        for i, item in enumerate(self.steps):
            if isinstance(item, Steps) and item.name == steps_sequence_name:
                del self.steps[i]
                return True
        return False

    def get_steps_sequence(self, steps_sequence_name: str) -> Optional[Steps]:
        """Get a steps sequence by name"""
        steps_sequences = self._get_steps_sequences()
        for steps_sequence in steps_sequences:
            if steps_sequence.name == steps_sequence_name:
                return steps_sequence
        return None

    def list_steps_sequences(self) -> List[str]:
        """List all steps sequence names"""
        steps_sequences = self._get_steps_sequences()
        return [steps_sequence.name for steps_sequence in steps_sequences]

    def to_dict(self) -> Dict[str, Any]:
        """Convert workflow to dictionary representation"""
        steps_sequences = self._get_steps_sequences()
        return {
            "name": self.name,
            "workflow_id": self.workflow_id,
            "description": self.description,
            "steps_sequences": [
                {
                    "name": s.name,
                    "description": s.description,
                    "steps": [
                        {
                            "name": t.name,
                            "description": t.description,
                            "executor_type": t.executor_type,
                        }
                        for t in s.steps
                    ],
                }
                for s in steps_sequences
            ],
            "session_id": self.session_id,
        }

    def _collect_workflow_session_state_from_agents_and_teams(self):
        """Collect updated workflow_session_state from agents after step execution"""
        log_debug("Collecting workflow session state from agents and teams")

        if self.workflow_session_state is None:
            self.workflow_session_state = {}
            log_debug("Initialized empty workflow session state")

        # Collect state from all agents in all steps sequences
        steps_sequences = self._get_steps_sequences()
        for steps_sequence in steps_sequences:
            log_debug(
                f"Collecting state from steps sequence: {steps_sequence.name}")
            for step in steps_sequence.steps:
                executor = step.active_executor
                if hasattr(executor, "workflow_session_state") and executor.workflow_session_state:
                    merge_dictionaries(
                        self.workflow_session_state, executor.workflow_session_state)
                    log_debug("Merged executor session state into workflow")

                # If it's a team, collect from all members
                if hasattr(executor, "members"):
                    log_debug(
                        f"Collecting state from {len(executor.members)} team members")
                    for member in executor.members:
                        if hasattr(member, "workflow_session_state") and member.workflow_session_state:
                            log_debug(
                                f"Found session state in team member {type(member).__name__}: {list(member.workflow_session_state.keys())}"
                            )
                            merge_dictionaries(
                                self.workflow_session_state, member.workflow_session_state)
                            log_debug(
                                "Merged team member session state into workflow")

    def _execute_workflow_steps(
        self,
        execution_input: WorkflowExecutionInput,
        workflow_run_response: WorkflowRunResponse,
    ) -> WorkflowRunResponse:
        """Execute workflow steps directly without forcing Steps wrapper"""
        self._set_debug()

        log_debug(f"Starting direct workflow execution: {self.run_id}")
        workflow_run_response.status = RunStatus.running

        if self.executor:
            # Execute the workflow with the custom executor
            workflow_run_response.content = self.executor(self, execution_input)
            workflow_run_response.status = RunStatus.completed
        else:
            try:
                collected_step_outputs = []
                previous_step_content = None
                workflow_images = execution_input.images or []
                workflow_videos = execution_input.videos or []
                workflow_audio = execution_input.audio or []

                for i, step_item in enumerate(self.steps):
                    # Execute different step types
                    if isinstance(step_item, Step):
                        step_input = StepInput(
                            message=execution_input.message,
                            message_data=execution_input.message_data,
                            previous_step_content=previous_step_content,
                            images=workflow_images,
                            videos=workflow_videos,
                            audio=workflow_audio,
                        )
                        step_output = step_item.execute(
                            step_input, self.session_id, self.user_id)

                        if step_output:
                            collected_step_outputs.append(step_output)
                            previous_step_content = step_output.content
                            workflow_images.extend(step_output.images or [])
                            workflow_videos.extend(step_output.videos or [])
                            workflow_audio.extend(step_output.audio or [])

                    elif hasattr(step_item, 'execute') and callable(step_item.execute):
                        # This handles Parallel class (which has an execute method)
                        step_input = StepInput(
                            message=execution_input.message,
                            message_data=execution_input.message_data,
                            previous_step_content=previous_step_content,
                            images=workflow_images,
                            videos=workflow_videos,
                            audio=workflow_audio,
                        )
                        step_output = step_item.execute(
                            step_input, self.session_id, self.user_id)

                        if step_output:
                            collected_step_outputs.append(step_output)
                            previous_step_content = step_output.content
                            workflow_images.extend(step_output.images or [])
                            workflow_videos.extend(step_output.videos or [])
                            workflow_audio.extend(step_output.audio or [])

                    elif isinstance(step_item, Steps):
                        # For existing Steps sequences, execute them
                        # Steps.execute() modifies workflow_run_response directly
                        step_item.execute(
                            execution_input, workflow_run_response, self.session_id, self.user_id)

                        # Steps execution updates workflow_run_response directly
                        # Get the outputs that were added
                        if workflow_run_response.step_responses:
                            new_outputs = workflow_run_response.step_responses[len(
                                collected_step_outputs):]
                            collected_step_outputs.extend(new_outputs)
                            if new_outputs:
                                last_output = new_outputs[-1]
                                previous_step_content = last_output.content
                                workflow_images.extend(last_output.images or [])
                                workflow_videos.extend(last_output.videos or [])
                                workflow_audio.extend(last_output.audio or [])
                    else:
                        raise ValueError(
                            f"Unsupported step type: {type(step_item)}")

                # Update workflow response only if we executed individual steps/parallel
                # (Steps execution already updates the response)
                if not any(isinstance(item, Steps) for item in self.steps):
                    workflow_run_response.content = collected_step_outputs[-1].content if collected_step_outputs else ""
                    workflow_run_response.step_responses = collected_step_outputs
                    workflow_run_response.images = workflow_images
                    workflow_run_response.videos = workflow_videos
                    workflow_run_response.audio = workflow_audio

                workflow_run_response.status = RunStatus.completed

                # Collect updated workflow_session_state from agents after execution
                self._collect_workflow_session_state_from_agents_and_teams()

            except Exception as e:
                logger.error(f"Workflow execution failed: {e}")
                workflow_run_response.status = RunStatus.error
                workflow_run_response.content = f"Workflow execution failed: {e}"

        # Store response
        if self.workflow_session:
            self.workflow_session.add_run(workflow_run_response)
        self.write_to_storage()

        return workflow_run_response


    def _execute_workflow_steps_stream(
        self,
        execution_input: WorkflowExecutionInput,
        workflow_run_response: WorkflowRunResponse,
        stream_intermediate_steps: bool = False,
    ) -> Iterator[WorkflowRunResponseEvent]:
        """Execute workflow steps with streaming support"""
        self._set_debug()

        log_debug(
            f"Starting direct workflow execution with streaming: {self.run_id}")
        workflow_run_response.status = RunStatus.running

        if self.executor:
            # Handle custom executor with streaming
            yield WorkflowStartedEvent(
                run_id=workflow_run_response.run_id or "",
                workflow_name=workflow_run_response.workflow_name,
                workflow_id=workflow_run_response.workflow_id,
                session_id=workflow_run_response.session_id,
            )

            import inspect
            if inspect.isgeneratorfunction(self.executor):
                content = ""
                for chunk in self.executor(self, execution_input):
                    yield chunk
                    if hasattr(chunk, "content") and chunk.content:
                        content += chunk.content
                workflow_run_response.content = content
            else:
                workflow_run_response.content = self.executor(
                    self, execution_input)

            workflow_run_response.status = RunStatus.completed
            yield WorkflowCompletedEvent(
                run_id=workflow_run_response.run_id or "",
                content=workflow_run_response.content,
                workflow_name=workflow_run_response.workflow_name,
                workflow_id=workflow_run_response.workflow_id,
                session_id=workflow_run_response.session_id,
            )
        else:
            try:
                yield WorkflowStartedEvent(
                    run_id=workflow_run_response.run_id or "",
                    workflow_name=workflow_run_response.workflow_name,
                    workflow_id=workflow_run_response.workflow_id,
                    session_id=workflow_run_response.session_id,
                )

                collected_step_outputs = []
                previous_step_content = None
                workflow_images = execution_input.images or []
                workflow_videos = execution_input.videos or []
                workflow_audio = execution_input.audio or []

                for step_index, step_item in enumerate(self.steps):
                    step_name = getattr(step_item, 'name',
                                        f'Step {step_index + 1}')

                    yield StepStartedEvent(
                        run_id=workflow_run_response.run_id or "",
                        workflow_name=workflow_run_response.workflow_name,
                        step_name=step_name,
                        step_index=step_index,
                        workflow_id=workflow_run_response.workflow_id,
                        session_id=workflow_run_response.session_id,
                    )

                    step_input = StepInput(
                        message=execution_input.message,
                        message_data=execution_input.message_data,
                        previous_step_content=previous_step_content,
                        images=workflow_images,
                        videos=workflow_videos,
                        audio=workflow_audio,
                    )

                    # Execute different step types with streaming
                    if isinstance(step_item, Step):
                        for event in step_item.execute(step_input, self.session_id, self.user_id, stream=True, stream_intermediate_steps=stream_intermediate_steps):
                            if isinstance(event, StepOutput):
                                step_output = event
                            else:
                                yield event
                    elif hasattr(step_item, 'execute') and callable(step_item.execute):
                        # This handles Parallel class
                        step_output = step_item.execute(
                            step_input, self.session_id, self.user_id)
                    elif isinstance(step_item, Steps):
                        # For existing Steps sequences
                        for event in step_item.execute_stream(execution_input, workflow_run_response, self.session_id, self.user_id, stream_intermediate_steps):
                            if isinstance(event, StepCompletedEvent):
                                step_output = event.step_response
                            else:
                                yield event
                    else:
                        raise ValueError(
                            f"Unsupported step type: {type(step_item)}")

                    if step_output:
                        collected_step_outputs.append(step_output)
                        previous_step_content = step_output.content
                        workflow_images.extend(step_output.images or [])
                        workflow_videos.extend(step_output.videos or [])
                        workflow_audio.extend(step_output.audio or [])

                        yield StepCompletedEvent(
                            run_id=workflow_run_response.run_id or "",
                            content=step_output.content,
                            workflow_name=workflow_run_response.workflow_name,
                            step_name=step_name,
                            step_index=step_index,
                            workflow_id=workflow_run_response.workflow_id,
                            session_id=workflow_run_response.session_id,
                            step_response=step_output,
                        )

                # Update workflow response
                workflow_run_response.content = collected_step_outputs[-1].content if collected_step_outputs else ""
                workflow_run_response.step_responses = collected_step_outputs
                workflow_run_response.images = workflow_images
                workflow_run_response.videos = workflow_videos
                workflow_run_response.audio = workflow_audio
                workflow_run_response.status = RunStatus.completed

                yield WorkflowCompletedEvent(
                    run_id=workflow_run_response.run_id or "",
                    content=workflow_run_response.content,
                    workflow_name=workflow_run_response.workflow_name,
                    workflow_id=workflow_run_response.workflow_id,
                    session_id=workflow_run_response.session_id,
                    step_responses=workflow_run_response.step_responses,
                )

                # Collect updated workflow_session_state from agents after execution
                self._collect_workflow_session_state_from_agents_and_teams()

            except Exception as e:
                logger.error(f"Workflow execution failed: {e}")
                from agno.run.v2.workflow import WorkflowErrorEvent

                error_event = WorkflowErrorEvent(
                    run_id=self.run_id or "",
                    workflow_id=self.workflow_id,
                    workflow_name=self.name,
                    session_id=self.session_id,
                    error=str(e),
                )
                yield error_event

                workflow_run_response.content = error_event.error
                workflow_run_response.status = RunStatus.error

        # Store response
        if self.workflow_session:
            self.workflow_session.add_run(workflow_run_response)
        self.write_to_storage()
