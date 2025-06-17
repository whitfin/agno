from dataclasses import dataclass
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, Iterator, List, Optional, Union
from pydantic import BaseModel

from agno.agent import Agent
from agno.media import AudioArtifact, ImageArtifact, VideoArtifact
from agno.run.response import RunResponse
from agno.run.team import TeamRunResponse
from agno.run.v2.workflow import (
    WorkflowRunResponseEvent,
)
from agno.team import Team
from agno.utils.log import logger


@dataclass
class TaskInput:
    """Input data for a task execution"""

    message: Optional[str] = None
    message_data: Optional[Union[BaseModel, Dict[str, Any]]] = None
    previous_task_content: Optional[Any] = None

    # Media inputs
    images: Optional[List[ImageArtifact]] = None
    videos: Optional[List[VideoArtifact]] = None
    audio: Optional[List[AudioArtifact]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        message_data_dict = {}
        if isinstance(self.message_data, BaseModel):
            message_data_dict = self.message_data.model_dump(exclude_none=True)
        elif isinstance(self.message_data, dict):
            message_data_dict = self.message_data

        if isinstance(self.previous_task_content, BaseModel):
            previous_task_content_str = self.previous_task_content.model_dump_json(indent=2, exclude_none=True)
        elif isinstance(self.previous_task_content, dict):
            import json
            previous_task_content_str = json.dumps(self.previous_task_content, indent=2, default=str)
        else:
            previous_task_content_str = str(self.previous_task_content)

        return {
            "message": self.message,
            "message_data": message_data_dict,
            "previous_task_content": previous_task_content_str,
            "images": [img.to_dict() for img in self.images] if self.images else None,
            "videos": [vid.to_dict() for vid in self.videos] if self.videos else None,
            "audio": [aud.to_dict() for aud in self.audio] if self.audio else None,
        }


@dataclass
class TaskOutput:
    """Output data from a task execution"""

    task_name: Optional[str] = None
    task_id: Optional[str] = None
    executor_type: Optional[str] = None
    executor_name: Optional[str] = None

    # Primary output
    content: Optional[str] = None

    # Execution response
    response: Optional[Union[RunResponse, TeamRunResponse]] = None

    # Media outputs
    images: Optional[List[ImageArtifact]] = None
    videos: Optional[List[VideoArtifact]] = None
    audio: Optional[List[AudioArtifact]] = None

    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "content": self.content,
            "response": self.response.to_dict() if self.response else None,
            "images": [img.to_dict() for img in self.images] if self.images else None,
            "videos": [vid.to_dict() for vid in self.videos] if self.videos else None,
            "audio": [aud.to_dict() for aud in self.audio] if self.audio else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskOutput":
        """Create TaskOutput from dictionary"""
        from agno.run.response import RunResponse
        from agno.run.team import TeamRunResponse

        # Reconstruct response if present
        response_data = data.get("response")
        response = None
        if response_data:
            # Determine if it's RunResponse or TeamRunResponse based on structure
            if "team_id" in response_data or "team_name" in response_data:
                response = TeamRunResponse.from_dict(response_data)
            else:
                response = RunResponse.from_dict(response_data)

        # Reconstruct media artifacts
        images = data.get("images")
        if images:
            images = [ImageArtifact.model_validate(img) for img in images]

        videos = data.get("videos")
        if videos:
            videos = [VideoArtifact.model_validate(vid) for vid in videos]

        audio = data.get("audio")
        if audio:
            audio = [AudioArtifact.model_validate(aud) for aud in audio]

        return cls(
            content=data.get("content"),
            response=response,
            images=images,
            videos=videos,
            audio=audio,
            success=data.get("success", True),
            error=data.get("error"),
        )


TaskExecutor = Callable[
            [TaskInput],
            Union[
                TaskOutput,
                Iterator[TaskOutput],
                Iterator[Any],
                Awaitable[TaskOutput],
                Awaitable[Any],
                AsyncIterator[TaskOutput],
                AsyncIterator[Any],
            ]
        ]

@dataclass
class Task:
    """A single unit of work in a workflow pipeline"""

    name: Optional[str] = None

    # Executor options - only one should be provided
    agent: Optional[Agent] = None
    team: Optional[Team] = None
    executor: Optional[TaskExecutor] = None

    task_id: Optional[str] = None
    description: Optional[str] = None

    # Task configuration
    max_retries: int = 3
    timeout_seconds: Optional[int] = None

    skip_on_failure: bool = False

    # Input validation mode
    # If False, only warn about missing inputs
    strict_input_validation: bool = False

    _retry_count: int = 0

    def __init__(self,
                 name: Optional[str] = None,
                 agent: Optional[Agent] = None,
                 team: Optional[Team] = None,
                 execution_function: Optional[TaskExecutor] = None,
                 task_id: Optional[str] = None,
                 description: Optional[str] = None,
                 max_retries: int = 3,
                 timeout_seconds: Optional[int] = None,
                 skip_on_failure: bool = False,
                 strict_input_validation: bool = False):
        self.name = name
        self.agent = agent
        self.team = team
        self.executor = execution_function

        # Validate executor configuration
        self._validate_executor_config()

        self.task_id = task_id
        self.description = description
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.skip_on_failure = skip_on_failure
        self.strict_input_validation = strict_input_validation

        # Set the active executor
        self._set_active_executor()

    @property
    def executor_name(self) -> str:
        """Get the name of the current executor"""
        if hasattr(self.active_executor, "name"):
            return self.active_executor.name
        elif self._executor_type == "function":
            return getattr(self.active_executor, "__name__", "anonymous_function")
        else:
            return f"{self._executor_type}_executor"

    @property
    def executor_type(self) -> str:
        """Get the type of the current executor"""
        return self._executor_type


    def _validate_executor_config(self):
        """Validate that only one executor type is provided"""
        executor_count = sum(
            [
                self.agent is not None,
                self.team is not None,
                self.executor is not None,
            ]
        )

        if executor_count == 0:
            raise ValueError(f"Task '{self.name}' must have one executor: agent=, team=, or executor=")

        if executor_count > 1:
            provided_executors = []
            if self.agent is not None:
                provided_executors.append("agent")
            if self.team is not None:
                provided_executors.append("team")
            if self.executor is not None:
                provided_executors.append("executor")

            raise ValueError(
                f"Task '{self.name}' can only have one executor type. "
                f"Provided: {', '.join(provided_executors)}. "
                f"Please use only one of: agent=, team=, or executor="
            )

    def _set_active_executor(self):
        """Set the active executor based on what was provided"""
        if self.agent is not None:
            self.active_executor = self.agent
            self._executor_type = "agent"
        elif self.team is not None:
            self.active_executor = self.team
            self._executor_type = "team"
        elif self.executor is not None:
            self.active_executor = self.executor
            self._executor_type = "function"

    def execute(
        self,
        task_input: TaskInput,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        stream: bool = False,
        stream_intermediate_steps: bool = False,
    ) -> Union[TaskOutput, Iterator[WorkflowRunResponseEvent]]:
        """Execute the task with TaskInput, with optional streaming support"""
        if stream:
            return self._execute_task_stream(task_input=task_input, session_id=session_id, user_id=user_id, stream_intermediate_steps=stream_intermediate_steps)
        else:
            return self._execute_task(task_input=task_input, session_id=session_id, user_id=user_id)

    def _execute_task(
        self, task_input: TaskInput, session_id: Optional[str] = None, user_id: Optional[str] = None
    ) -> TaskOutput:
        """Execute the task with TaskInput, returning final TaskOutput (non-streaming)"""

        # Execute with retries
        for attempt in range(self.max_retries + 1):
            try:
                if self._executor_type == "function":
                    # Execute function directly with TaskInput
                    result = self.active_executor(task_input)  # type: ignore

                    # If function returns TaskOutput, use it directly
                    if isinstance(result, TaskOutput):
                        return result

                    # Otherwise, wrap in TaskOutput
                    response = TaskOutput(content=str(result))
                else:
                    # For agents and teams, prepare message with context
                    message = self._prepare_message(task_input.message, task_input.message_data)

                    # Execute agent or team with media
                    if self._executor_type in ["agent", "team"]:
                        response = self.active_executor.run(
                            message=message,
                            images=task_input.images,
                            videos=task_input.videos,
                            audio=task_input.audio,
                            session_id=session_id,
                            user_id=user_id,
                        )
                    else:
                        raise ValueError(f"Unsupported executor type: {self._executor_type}")

                # Create TaskOutput from response
                task_output = self._create_task_output(response)

                logger.info(f"Task {self.name} completed successfully")
                return task_output

            except Exception as e:
                self.retry_count = attempt + 1
                logger.warning(f"Task {self.name} failed (attempt {attempt + 1}): {e}")

                if attempt == self.max_retries:
                    if self.skip_on_failure:
                        logger.info(f"Task {self.name} failed but continuing due to skip_on_failure=True")
                        # Create empty TaskOutput for skipped task
                        return TaskOutput(
                            content=f"Task {self.name} failed but skipped", success=False, error=str(e)
                        )
                    else:
                        raise e

    def _execute_task_stream(
        self,
        task_input: TaskInput,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        stream_intermediate_steps: bool = False,
    ) -> Iterator[Union[WorkflowRunResponseEvent, TaskOutput]]:
        """Execute the task with event-driven streaming support"""
        # Execute with retries and streaming
        for attempt in range(self.max_retries + 1):
            try:
                final_response = None

                if self._executor_type == "function":
                    # Handle custom function streaming
                    result = self.active_executor(task_input)  # type: ignore

                    if hasattr(result, "__iter__") and not isinstance(result, (str, bytes, dict, TaskOutput)):
                        try:
                            for event in result:
                                if isinstance(event, TaskOutput):
                                    final_response = event
                                else:
                                    yield event
                        except StopIteration as e:
                            if hasattr(e, "value") and isinstance(e.value, TaskOutput):
                                final_response = e.value
                        except TypeError:
                            if isinstance(result, TaskOutput):
                                final_response = result
                            else:
                                final_response = TaskOutput(content=str(result))
                    else:
                        if isinstance(result, TaskOutput):
                            final_response = result
                        else:
                            final_response = TaskOutput(content=str(result))
                else:
                    message = self._prepare_message(task_input.message, task_input.message_data)

                    if self._executor_type in ["agent", "team"]:
                        response_stream = self.active_executor.run(
                            message=message,
                            images=task_input.images,
                            videos=task_input.videos,
                            audio=task_input.audio,
                            session_id=session_id,
                            user_id=user_id,
                            stream=True,
                            stream_intermediate_steps=stream_intermediate_steps,
                        )

                        for event in response_stream:
                            yield event
                        final_response = self._create_task_output(self.active_executor.run_response)

                    else:
                        raise ValueError(f"Unsupported executor type: {self._executor_type}")

                # If we didn't get a final response, create one
                if final_response is None:
                    final_response = TaskOutput(content="")

                logger.info(f"Task {self.name} completed successfully with streaming")
                yield final_response
                return

            except Exception as e:
                self.retry_count = attempt + 1
                logger.warning(f"Task {self.name} failed (attempt {attempt + 1}): {e}")

                if attempt == self.max_retries:
                    if self.skip_on_failure:
                        logger.info(f"Task {self.name} failed but continuing due to skip_on_failure=True")
                        # Create empty TaskOutput for skipped task
                        task_output = TaskOutput(
                            content=f"Task {self.name} failed but skipped", success=False, error=str(e)
                        )
                        yield task_output
                        return
                    else:
                        raise e


    async def aexecute(
        self,
        task_input: TaskInput,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        stream: bool = False,
        stream_intermediate_steps: bool = False,
    ) -> Union[TaskOutput, AsyncIterator[WorkflowRunResponseEvent]]:
        """Execute the task with TaskInput, with optional streaming support"""
        if stream:
            return self._aexecute_task_stream(task_input=task_input, session_id=session_id, user_id=user_id, stream_intermediate_steps=stream_intermediate_steps)
        else:
            return await self._aexecute_task(task_input=task_input, session_id=session_id, user_id=user_id)

    async def _aexecute_task(
        self, task_input: TaskInput, session_id: Optional[str] = None, user_id: Optional[str] = None
    ) -> TaskOutput:
        """Execute the task with TaskInput, returning final TaskOutput (non-streaming)"""

        # Execute with retries
        for attempt in range(self.max_retries + 1):
            try:
                if self._executor_type == "function":
                    import inspect
                    if inspect.iscoroutinefunction(self.active_executor):
                        result = await self.active_executor(task_input)  # type: ignore
                    else:
                        result = self.active_executor(task_input)  # type: ignore

                    # If function returns TaskOutput, use it directly
                    if isinstance(result, TaskOutput):
                        return result

                    # Otherwise, wrap in TaskOutput
                    response = TaskOutput(content=str(result))
                else:
                # For agents and teams, prepare message with context
                    message = self._prepare_message(task_input.message, task_input.message_data)

                    # Execute agent or team with media
                    if self._executor_type in ["agent", "team"]:
                        response = await self.active_executor.arun(
                            message=message,
                            images=task_input.images,
                            videos=task_input.videos,
                            audio=task_input.audio,
                            session_id=session_id,
                            user_id=user_id,
                        )
                    else:
                        raise ValueError(f"Unsupported executor type: {self._executor_type}")

                # Create TaskOutput from response
                task_output = self._create_task_output(response)

                logger.info(f"Task {self.name} completed successfully")
                return task_output

            except Exception as e:
                self.retry_count = attempt + 1
                logger.warning(f"Task {self.name} failed (attempt {attempt + 1}): {e}")

                if attempt == self.max_retries:
                    if self.skip_on_failure:
                        logger.info(f"Task {self.name} failed but continuing due to skip_on_failure=True")
                        # Create empty TaskOutput for skipped task
                        return TaskOutput(
                            content=f"Task {self.name} failed but skipped", success=False, error=str(e)
                        )
                    else:
                        raise e

    async def _aexecute_task_stream(
        self,
        task_input: TaskInput,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        stream_intermediate_steps: bool = False,
    ) -> AsyncIterator[Union[WorkflowRunResponseEvent, TaskOutput]]:
        """Execute the task with event-driven streaming support"""
        # Execute with retries and streaming
        for attempt in range(self.max_retries + 1):
            try:
                final_response = None

                if self._executor_type == "function":
                    import inspect

                    # Check if the function is an async generator
                    if inspect.isasyncgenfunction(self.active_executor):
                        # It's an async generator - iterate over it
                        async for event in self.active_executor(task_input):
                            if isinstance(event, TaskOutput):
                                final_response = event
                            else:
                                yield event
                    elif inspect.iscoroutinefunction(self.active_executor):
                        # It's a regular async function - await it
                        result = await self.active_executor(task_input)
                        if isinstance(result, TaskOutput):
                            final_response = result
                        else:
                            final_response = TaskOutput(content=str(result))
                    elif inspect.isgeneratorfunction(self.active_executor):
                        # It's a regular generator function - iterate over it
                        for event in self.active_executor(task_input):
                            if isinstance(event, TaskOutput):
                                final_response = event
                            else:
                                yield event
                    else:
                        # It's a regular function - call it directly
                        result = self.active_executor(task_input)  # type: ignore
                        if isinstance(result, TaskOutput):
                            final_response = result
                        else:
                            final_response = TaskOutput(content=str(result))
                else:
                    message = self._prepare_message(task_input.message, task_input.message_data)

                    if self._executor_type in ["agent", "team"]:
                        response_stream = await self.active_executor.arun(  # type: ignore
                            message=message,
                            images=task_input.images,
                            videos=task_input.videos,
                            audio=task_input.audio,
                            session_id=session_id,
                            user_id=user_id,
                            stream=True,
                            stream_intermediate_steps=stream_intermediate_steps,
                        )

                        async for event in response_stream:
                            yield event
                        final_response = self._create_task_output(self.active_executor.run_response)  # type: ignore
                    else:
                        raise ValueError(f"Unsupported executor type: {self._executor_type}")

                # If we didn't get a final response, create one
                if final_response is None:
                    final_response = TaskOutput(content="")

                logger.info(f"Task {self.name} completed successfully with streaming")
                yield final_response
                return

            except Exception as e:
                self.retry_count = attempt + 1
                logger.warning(f"Task {self.name} failed (attempt {attempt + 1}): {e}")

                if attempt == self.max_retries:
                    if self.skip_on_failure:
                        logger.info(f"Task {self.name} failed but continuing due to skip_on_failure=True")
                        # Create empty TaskOutput for skipped task
                        task_output = TaskOutput(
                            content=f"Task {self.name} failed but skipped", success=False, error=str(e)
                        )
                        yield task_output
                        return
                    else:
                        raise e


    def _parse_message_data(self, message_data: Optional[Union[BaseModel, Dict[str, Any]]]) -> Optional[str]:
        """Parse the message data into a string"""
        data_str = None
        if message_data is not None:
            if isinstance(message_data, BaseModel):
                data_str = message_data.model_dump_json(indent=2, exclude_none=True)
            elif isinstance(message_data, dict):
                import json

                data_str = json.dumps(message_data, indent=2, default=str)
            else:
                data_str = str(message_data)
        return data_str

    def _prepare_message(
        self, message: Optional[str], message_data: Optional[Union[BaseModel, Dict[str, Any]]]
    ) -> Optional[str]:
        """Prepare the primary input by combining message and message_data"""

        # Convert message_data to string if provided
        data_str = self._parse_message_data(message_data)

        # Combine message and data
        if message and data_str:
            return f"{message}\n\n--- Structured Data ---\n{data_str}"
        elif message:
            return message
        elif data_str:
            return f"Process the following data:\n{data_str}"
        else:
            return None


    def _create_task_output(self, response: Union[RunResponse, TeamRunResponse, TaskOutput]) -> TaskOutput:
        """Create TaskOutput from execution response"""
        if isinstance(response, TaskOutput):
            response.task_name = self.name
            response.task_id = self.task_id
            response.executor_type = self._executor_type
            response.executor_name = self.executor_name

            return response

        # Extract media from response
        images = getattr(response, "images", None)
        videos = getattr(response, "videos", None)
        audio = getattr(response, "audio", None)

        return TaskOutput(
            task_name=self.name,
            task_id=self.task_id,
            executor_type=self._executor_type,
            executor_name=self.executor_name,
            content=response.content,
            response=response,
            images=images,
            videos=videos,
            audio=audio,
        )

    def _convert_function_result_to_response(self, result: Any) -> RunResponse:
        """Convert function execution result to RunResponse"""
        if isinstance(result, RunResponse):
            return result
        elif isinstance(result, str):
            return RunResponse(content=result)
        elif isinstance(result, dict):
            # If it's a dict, try to extract content
            content = result.get("content", str(result))
            return RunResponse(content=content)
        else:
            # Convert any other type to string
            return RunResponse(content=str(result))
