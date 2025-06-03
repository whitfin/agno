from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Union
from uuid import uuid4

from agno.run.response import RunEvent, RunResponse
from agno.storage.base import Storage
from agno.utils.log import log_debug, logger
from agno.workflow.v2.sequence import Sequence
from agno.workflow.v2.trigger import TriggerType


@dataclass
class Workflow:
    """Workflow 2.0 - Pipeline-based workflow execution"""

    # Workflow identification - make name optional with default
    name: Optional[str] = None
    workflow_id: Optional[str] = None
    description: Optional[str] = None
    version: str = "2.0"

    # Workflow configuration
    trigger: TriggerType = TriggerType.MANUAL
    pipelines: List[Sequence] = field(default_factory=list)
    storage: Optional[Storage] = None

    # Execution settings
    debug_mode: bool = False
    max_concurrent_pipelines: int = 1

    # Session management
    session_id: Optional[str] = None
    user_id: Optional[str] = None

    # Runtime state
    run_id: Optional[str] = None

    def __post_init__(self):
        # Handle inheritance - get name from class attribute if not provided
        if self.name is None:
            self.name = getattr(self.__class__, "name", self.__class__.__name__)

        # Handle other class attributes
        if hasattr(self.__class__, "description") and self.description is None:
            self.description = getattr(self.__class__, "description", None)

        if hasattr(self.__class__, "trigger"):
            self.trigger = getattr(self.__class__, "trigger", TriggerType.MANUAL)

        if hasattr(self.__class__, "storage") and self.storage is None:
            self.storage = getattr(self.__class__, "storage", None)

        if hasattr(self.__class__, "pipelines") and not self.pipelines:
            class_pipelines = getattr(self.__class__, "pipelines", [])
            if class_pipelines:
                self.pipelines = class_pipelines.copy()

        if self.workflow_id is None:
            self.workflow_id = str(uuid4())

        if self.session_id is None:
            self.session_id = str(uuid4())

    def execute_pipeline(self, pipeline_name: str, inputs: Dict[str, Any]) -> Iterator[RunResponse]:
        """Execute a specific pipeline by name synchronously"""
        pipeline = self.get_pipeline(pipeline_name)
        if not pipeline:
            raise ValueError(f"Pipeline '{pipeline_name}' not found")

        # Initialize execution
        self.run_id = str(uuid4())
        execution_start = datetime.now()

        log_debug(f"Starting workflow execution: {self.run_id}")

        # Create execution context
        context = {
            "workflow_id": self.workflow_id,
            "workflow_name": self.name,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "execution_start": execution_start,
        }

        try:
            # Execute the pipeline synchronously
            for response in pipeline.execute(inputs, context):
                # Add workflow metadata to response
                response.workflow_id = self.workflow_id
                response.session_id = self.session_id
                response.run_id = self.run_id

                yield response

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")

            yield RunResponse(
                content=f"Workflow execution failed: {e}",
                event=RunEvent.run_error,
                workflow_id=self.workflow_id,
                session_id=self.session_id,
                run_id=self.run_id,
            )

    def run(self, query: str = None, **kwargs) -> Iterator[RunResponse]:
        """Execute the workflow synchronously"""
        # Determine pipeline based on trigger type
        if self.trigger == TriggerType.MANUAL:
            if not self.pipelines:
                raise ValueError("No pipelines available in this workflow")
            elif len(self.pipelines) > 1:
                raise ValueError(
                    f"Manual trigger workflows should have exactly one pipeline, found {len(self.pipelines)}"
                )

            pipeline_name = self.pipelines[0].name
        else:
            raise ValueError(f"Pipeline selection for trigger type '{self.trigger.value}' not yet implemented")

        # Simple inputs - just use query directly
        if query is not None:
            inputs = {"query": query}

        # Execute pipeline synchronously
        for response in self.execute_pipeline(pipeline_name, inputs):
            yield response

    def print_response(
        self,
        query: str,
        markdown: bool = True,
        show_time: bool = True,
        show_task_details: bool = True,
        console: Optional[Any] = None,
    ) -> None:
        """Print workflow execution with rich formatting

        Args:
            query: The main query/input for the workflow
            markdown: Whether to render content as markdown
            show_time: Whether to show execution time
            show_task_details: Whether to show individual task outputs
            console: Rich console instance (optional)
        """
        from rich.console import Group
        from rich.live import Live
        from rich.markdown import Markdown
        from rich.status import Status
        from rich.text import Text

        from agno.utils.response import create_panel
        from agno.utils.timer import Timer

        if console is None:
            from agno.cli.console import console

        # Validate pipeline configuration based on trigger type
        if self.trigger == TriggerType.MANUAL:
            if not self.pipelines:
                console.print("[red]No pipelines available in this workflow[/red]")
                return
            elif len(self.pipelines) > 1:
                console.print(
                    f"[red]Manual trigger workflows should have exactly one pipeline, found {len(self.pipelines)}[/red]"
                )
                return

            # Use the single pipeline for manual trigger
            pipeline = self.pipelines[0]
        else:
            # For other trigger types, we'll implement pipeline selection logic later
            console.print(f"[yellow]Trigger type '{self.trigger.value}' not yet supported in print_response[/yellow]")
            return

        # Simple inputs - just use query directly
        inputs = {"query": query}

        panels = []

        # Show workflow info
        workflow_info = f"""
            **Workflow:** {self.name}
            **Pipeline:** {pipeline.name}
            **Description:** {pipeline.description or "No description"}
            **Tasks:** {len(pipeline.tasks)} tasks
            **Query:** {query}
        """.strip()

        workflow_panel = create_panel(
            content=Markdown(workflow_info) if markdown else workflow_info,
            title="Workflow Information",
            border_style="cyan",
        )
        console.print(workflow_panel)

        # Execute and show results
        streaming_content = ""
        task_responses = []

        with Live(console=console) as live_log:
            status = Status("Starting workflow...", spinner="dots")
            live_log.update(Group(*panels, status))

            response_timer = Timer()
            response_timer.start()

            try:
                for response in self.run(query=query):
                    if response.event == RunEvent.workflow_started:
                        status.update("Pipeline started...")

                    elif response.event == RunEvent.run_response:
                        # Extract task info from extra_data
                        task_name = (
                            response.extra_data.get("task_name", "Unknown") if response.extra_data else "Unknown"
                        )
                        task_index = response.extra_data.get("task_index", 0) if response.extra_data else 0

                        status.update(f"Executing task {task_index + 1}: {task_name}...")

                        if response.content:
                            streaming_content += response.content
                            task_responses.append(
                                {
                                    "task_name": task_name,
                                    "task_index": task_index,
                                    "content": response.content,
                                    "event": response.event,
                                }
                            )

                        # Show task details if enabled - display full content
                        if show_task_details and response.content:
                            task_panel = create_panel(
                                content=Markdown(response.content) if markdown else response.content,
                                title=f"Task {task_index + 1}: {task_name}",
                                border_style="green",
                            )
                            panels.append(task_panel)

                    elif response.event == RunEvent.workflow_completed:
                        status.update("Workflow completed!")

                        # Show final summary
                        if response.extra_data:
                            final_output = response.extra_data
                            summary_content = f"""
                                **Status:** {final_output.get("status", "Unknown")}
                                **Tasks Completed:** {len(task_responses)}
                                **Total Outputs:** {len(final_output.get("task_outputs", {}))}
                            """.strip()

                            summary_panel = create_panel(
                                content=Markdown(summary_content) if markdown else summary_content,
                                title="Execution Summary",
                                border_style="blue",
                            )
                            panels.append(summary_panel)

                    elif response.event == RunEvent.run_error:
                        status.update("Workflow failed!")
                        error_panel = create_panel(content=response.content, title="Error", border_style="red")
                        panels.append(error_panel)

                    # Update live display
                    if show_time:
                        time_info = Text(f"({response_timer.elapsed:.1f}s)", style="dim")
                        live_log.update(Group(*panels, time_info))
                    else:
                        live_log.update(Group(*panels))

                response_timer.stop()

                # Final update with completion time
                if show_time:
                    completion_text = Text(f"Completed in {response_timer.elapsed:.1f}s", style="bold green")
                    live_log.update(Group(*panels, completion_text))

            except Exception as e:
                response_timer.stop()
                error_panel = create_panel(
                    content=f"Workflow execution failed: {str(e)}", title="Execution Error", border_style="red"
                )
                panels.append(error_panel)
                live_log.update(Group(*panels))

    def add_pipeline(self, pipeline: Sequence) -> None:
        """Add a pipeline to the workflow"""
        self.pipelines.append(pipeline)

    def remove_pipeline(self, pipeline_name: str) -> bool:
        """Remove a pipeline by name"""
        for i, pipeline in enumerate(self.pipelines):
            if pipeline.name == pipeline_name:
                del self.pipelines[i]
                return True
        return False

    def get_pipeline(self, pipeline_name: str) -> Optional[Sequence]:
        """Get a pipeline by name"""
        for pipeline in self.pipelines:
            if pipeline.name == pipeline_name:
                return pipeline
        return None

    def list_pipelines(self) -> List[str]:
        """List all pipeline names"""
        return [pipeline.name for pipeline in self.pipelines]

    def to_dict(self) -> Dict[str, Any]:
        """Convert workflow to dictionary representation"""
        return {
            "name": self.name,
            "workflow_id": self.workflow_id,
            "description": self.description,
            "version": self.version,
            "trigger": self.trigger.value,
            "pipelines": [
                {
                    "name": p.name,
                    "description": p.description,
                    "tasks": [
                        {"name": t.name, "description": t.description, "executor_type": type(t.executor).__name__}
                        for t in p.tasks
                    ],
                }
                for p in p.pipelines
            ],
            "session_id": self.session_id,
        }
