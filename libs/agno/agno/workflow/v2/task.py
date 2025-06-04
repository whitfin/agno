from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Type, Union
from uuid import uuid4

from agno.agent import Agent
from agno.run.response import RunResponse
from agno.team import Team
from agno.utils.log import logger


@dataclass
class Task:
    """A single unit of work in a workflow sequence"""

    name: str
    # Executor options - only one should be provided
    agent: Optional[Agent] = None
    team: Optional[Team] = None
    execution_function: Optional[Callable[[Dict[str, Any]], Any]] = None

    task_id: Optional[str] = None
    description: Optional[str] = None
    expected_input: Optional[Dict[str, Type]] = None
    expected_output: Optional[str] = None

    # Task configuration
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: Optional[int] = None

    skip_on_failure: bool = False

    # Input validation mode
    # If False, only warn about missing inputs
    strict_input_validation: bool = False

    def __post_init__(self):
        if self.task_id is None:
            self.task_id = str(uuid4())

        # Validate executor configuration
        self._validate_executor_config()

        # Set the active executor
        self._set_active_executor()

    def _validate_executor_config(self):
        """Validate that only one executor type is provided"""
        executor_count = sum(
            [
                self.agent is not None,
                self.team is not None,
                self.execution_function is not None,
            ]
        )

        if executor_count == 0:
            raise ValueError(f"Task '{self.name}' must have one executor: agent=, team=, or execution_function=")

        if executor_count > 1:
            provided_executors = []
            if self.agent is not None:
                provided_executors.append("agent")
            if self.team is not None:
                provided_executors.append("team")
            if self.execution_function is not None:
                provided_executors.append("execution_function")

            raise ValueError(
                f"Task '{self.name}' can only have one executor type. "
                f"Provided: {', '.join(provided_executors)}. "
                f"Please use only one of: agent=, team=, or execution_function="
            )

    def _set_active_executor(self):
        """Set the active executor based on what was provided"""
        if self.agent is not None:
            self._active_executor = self.agent
            self._executor_type = "agent"
        elif self.team is not None:
            self._active_executor = self.team
            self._executor_type = "team"
        elif self.execution_function is not None:
            self._active_executor = self.execution_function
            self._executor_type = "function"

    def execute(self, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> RunResponse:
        """Execute the task with given inputs synchronously"""
        logger.info(f"Executing task: {self.name}")

        # Validate inputs if expected_input is defined
        if self.expected_input:
            validation_result = self._validate_inputs(inputs)
            if not validation_result and self.strict_input_validation:
                raise ValueError(f"Input validation failed for task {self.name}")

        # Execute with retries
        for attempt in range(self.max_retries + 1):
            try:
                if self._executor_type == "agent":
                    # Format inputs for agent
                    message = self._format_inputs_for_agent(inputs)
                    response = self._active_executor.run(message)
                elif self._executor_type == "team":
                    # Format inputs for team
                    message = self._format_inputs_for_team(inputs)
                    response = self._active_executor.run(message)
                elif self._executor_type == "function":
                    # Execute function directly with inputs
                    result = self._active_executor(inputs)
                    # Convert function result to RunResponse
                    response = self._convert_function_result_to_response(result)
                else:
                    raise ValueError(f"Unsupported executor type: {self._executor_type}")

                logger.info(f"Task {self.name} completed successfully")
                return response

            except Exception as e:
                self.retry_count = attempt + 1
                logger.warning(f"Task {self.name} failed (attempt {attempt + 1}): {e}")

                if attempt == self.max_retries:
                    if self.skip_on_failure:
                        logger.info(f"Task {self.name} failed but continuing due to skip_on_failure=True")
                        return RunResponse(content=f"Task {self.name} failed but skipped", event="task_failed_skipped")
                    else:
                        raise e

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

    def _validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate that required inputs are present and of correct type"""
        all_valid = True

        for key, expected_type in self.expected_input.items():
            if key not in inputs:
                if self.strict_input_validation:
                    logger.error(f"Required input '{key}' missing for task {self.name}")
                    all_valid = False
                else:
                    logger.warning(f"Expected input '{key}' missing for task {self.name}, but continuing...")
                continue

            if not isinstance(inputs[key], expected_type):
                if self.strict_input_validation:
                    logger.error(
                        f"Input '{key}' should be of type {expected_type.__name__}, got {type(inputs[key]).__name__}"
                    )
                    all_valid = False
                else:
                    logger.warning(f"Input '{key}' type mismatch for task {self.name}, but continuing...")

        return all_valid

    def _format_inputs_for_agent(self, inputs: Dict[str, Any]) -> str:
        """Format inputs as a message for an agent"""
        if len(inputs) == 1 and "message" in inputs:
            return inputs["message"]

        # Create a structured message from inputs
        message_parts = []
        if self.description:
            message_parts.append(f"Task: {self.description}")

        message_parts.append("Inputs:")
        for key, value in inputs.items():
            message_parts.append(f"- {key}: {value}")

        if self.expected_output:
            message_parts.append(f"\nExpected output: {self.expected_output}")

        return "\n".join(message_parts)

    def _format_inputs_for_team(self, inputs: Dict[str, Any]) -> str:
        """Format inputs as a message for a team"""
        return self._format_inputs_for_agent(inputs)  # Same formatting for now

    @property
    def executor_name(self) -> str:
        """Get the name of the current executor"""
        if hasattr(self._active_executor, "name"):
            return self._active_executor.name
        elif self._executor_type == "function":
            return getattr(self._active_executor, "__name__", "anonymous_function")
        else:
            return f"{self._executor_type}_executor"

    @property
    def executor_type(self) -> str:
        """Get the type of the current executor"""
        return self._executor_type
