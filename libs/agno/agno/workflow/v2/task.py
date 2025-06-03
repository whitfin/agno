from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Type, Union
from uuid import uuid4

from agno.agent import Agent
from agno.run.response import RunResponse
from agno.team import Team
from agno.utils.log import logger


@dataclass
class Task:
    """A single unit of work in a workflow sequence"""

    name: str
    executor: Union[Agent, Team]

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
                if isinstance(self.executor, Agent):
                    # Format inputs for agent
                    message = self._format_inputs_for_agent(inputs)
                    response = self.executor.run(message)
                elif isinstance(self.executor, Team):
                    # Format inputs for team
                    message = self._format_inputs_for_team(inputs)
                    response = self.executor.run(message)
                else:
                    raise ValueError(f"Unsupported executor type: {type(self.executor)}")

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
