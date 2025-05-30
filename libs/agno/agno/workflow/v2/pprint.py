import json
from typing import AsyncIterable, Iterable, Union

from pydantic import BaseModel

from agno.run.response import RunResponse
from agno.run.team import TeamRunResponse
from agno.utils.log import logger
from agno.utils.timer import Timer


def pprint_run_response(
    run_response: Union[RunResponse, Iterable[RunResponse], TeamRunResponse, Iterable[TeamRunResponse]],
    markdown: bool = False,
    show_time: bool = False,
) -> None:
    from rich.box import ROUNDED
    from rich.json import JSON
    from rich.live import Live
    from rich.markdown import Markdown
    from rich.status import Status
    from rich.table import Table

    from agno.cli.console import console

    # If run_response is a single RunResponse, wrap it in a list to make it iterable
    if isinstance(run_response, RunResponse) or isinstance(run_response, TeamRunResponse):
        single_response_content: Union[str, JSON, Markdown] = ""
        if isinstance(run_response.content, str):
            single_response_content = (
                Markdown(run_response.content) if markdown else run_response.get_content_as_string(
                    indent=4)
            )
        elif isinstance(run_response.content, BaseModel):
            try:
                single_response_content = JSON(
                    run_response.content.model_dump_json(exclude_none=True), indent=2)
            except Exception as e:
                logger.warning(f"Failed to convert response to Markdown: {e}")
        else:
            try:
                single_response_content = JSON(
                    json.dumps(run_response.content), indent=4)
            except Exception as e:
                logger.warning(f"Failed to convert response to string: {e}")

        table = Table(box=ROUNDED, border_style="blue", show_header=False)
        table.add_row(single_response_content)
        console.print(table)
    else:
        streaming_response_content: str = ""
        with Live(console=console) as live_log:
            status = Status("Working...", spinner="dots")
            live_log.update(status)
            response_timer = Timer()
            response_timer.start()
            for resp in run_response:
                if (isinstance(resp, RunResponse) or isinstance(resp, TeamRunResponse)) and isinstance(
                    resp.content, str
                ):
                    streaming_response_content += resp.content

                formatted_response = Markdown(
                    streaming_response_content) if markdown else streaming_response_content  # type: ignore
                table = Table(box=ROUNDED, border_style="blue",
                              show_header=False)
                if show_time:
                    # type: ignore
                    table.add_row(
                        f"Response\n({response_timer.elapsed:.1f}s)", formatted_response)
                else:
                    table.add_row(formatted_response)  # type: ignore
                live_log.update(table)
            response_timer.stop()


def pprint_workflow_response(
    workflow_responses: Iterable[RunResponse],
    markdown: bool = True,
    show_time: bool = True,
    show_task_details: bool = True,
) -> None:
    """Pretty print workflow responses with task-specific formatting"""
    from rich.box import ROUNDED
    from rich.console import Group
    from rich.live import Live
    from rich.markdown import Markdown
    from rich.status import Status
    from rich.table import Table
    from rich.text import Text
    from agno.utils.response import create_panel

    from agno.cli.console import console

    panels = []
    task_responses = []

    with Live(console=console) as live_log:
        status = Status("Starting workflow...", spinner="dots")
        live_log.update(status)

        response_timer = Timer()
        response_timer.start()

        for response in workflow_responses:
            if response.event == "WorkflowStarted":
                status.update("Pipeline started...")

            elif response.event == "RunResponse":
                # Extract task info
                task_name = response.extra_data.get(
                    'task_name', 'Unknown') if response.extra_data else 'Unknown'
                task_index = response.extra_data.get(
                    'task_index', 0) if response.extra_data else 0

                status.update(
                    f"Executing task {task_index + 1}: {task_name}...")

                if response.content and show_task_details:
                    task_content = response.content[:500] + "..." if len(
                        response.content) > 500 else response.content
                    task_panel = create_panel(
                        content=Markdown(
                            task_content) if markdown else task_content,
                        title=f"Task {task_index + 1}: {task_name}",
                        border_style="green"
                    )
                    panels.append(task_panel)
                    task_responses.append(response)

            elif response.event == "WorkflowCompleted":
                status.update("Workflow completed!")

                # Show final summary
                if response.extra_data:
                    final_output = response.extra_data
                    summary_content = f"""
**Status:** {final_output.get('status', 'Unknown')}
**Tasks Completed:** {len(task_responses)}
**Pipeline:** {final_output.get('pipeline_name', 'Unknown')}
                    """.strip()

                    summary_panel = create_panel(
                        content=Markdown(
                            summary_content) if markdown else summary_content,
                        title="Execution Summary",
                        border_style="blue"
                    )
                    panels.append(summary_panel)

            elif response.event == "RunError":
                status.update("Workflow failed!")
                error_panel = create_panel(
                    content=response.content,
                    title="Error",
                    border_style="red"
                )
                panels.append(error_panel)

            # Update live display
            if show_time:
                time_info = Text(
                    f"({response_timer.elapsed:.1f}s)", style="dim")
                live_log.update(Group(*panels, time_info))
            else:
                live_log.update(Group(*panels))

        response_timer.stop()

        # Final update
        if show_time:
            completion_text = Text(
                f"Completed in {response_timer.elapsed:.1f}s", style="bold green")
            live_log.update(Group(*panels, completion_text))


async def apprint_run_response(
    run_response: Union[RunResponse, AsyncIterable[RunResponse], TeamRunResponse, AsyncIterable[TeamRunResponse]],
    markdown: bool = False,
    show_time: bool = False,
) -> None:
    from rich.box import ROUNDED
    from rich.json import JSON
    from rich.live import Live
    from rich.markdown import Markdown
    from rich.status import Status
    from rich.table import Table

    from agno.cli.console import console

    # If run_response is a single RunResponse, wrap it in a list to make it iterable
    if isinstance(run_response, RunResponse) or isinstance(run_response, TeamRunResponse):
        single_response_content: Union[str, JSON, Markdown] = ""
        if isinstance(run_response.content, str):
            single_response_content = (
                Markdown(run_response.content) if markdown else run_response.get_content_as_string(
                    indent=4)
            )
        elif isinstance(run_response.content, BaseModel):
            try:
                single_response_content = JSON(
                    run_response.content.model_dump_json(exclude_none=True), indent=2)
            except Exception as e:
                logger.warning(f"Failed to convert response to Markdown: {e}")
        else:
            try:
                single_response_content = JSON(
                    json.dumps(run_response.content), indent=4)
            except Exception as e:
                logger.warning(f"Failed to convert response to string: {e}")

        table = Table(box=ROUNDED, border_style="blue", show_header=False)
        table.add_row(single_response_content)
        console.print(table)
    else:
        streaming_response_content: str = ""
        with Live(console=console) as live_log:
            status = Status("Working...", spinner="dots")
            live_log.update(status)
            response_timer = Timer()
            response_timer.start()

            async for resp in run_response:
                if (isinstance(resp, RunResponse) or isinstance(resp, TeamRunResponse)) and isinstance(
                    resp.content, str
                ):
                    streaming_response_content += resp.content

                formatted_response = Markdown(
                    streaming_response_content) if markdown else streaming_response_content  # type: ignore
                table = Table(box=ROUNDED, border_style="blue",
                              show_header=False)
                if show_time:
                    # type: ignore
                    table.add_row(
                        f"Response\n({response_timer.elapsed:.1f}s)", formatted_response)
                else:
                    table.add_row(formatted_response)  # type: ignore
                live_log.update(table)
            response_timer.stop()
