from typing import Any, Dict, Optional

from agno.agent.agent import Agent
from agno.models.openai.chat import OpenAIChat
from agno.team.team import Team
from agno.workflow.v2.task import Task
from agno.workflow.v2.workflow import Workflow


# === TEAM TOOLS ===
def add_task(team: Team, task_name: str, assignee: str) -> str:
    """Add a task to the team's task list."""
    if team.workflow_session_state is None:
        team.workflow_session_state = {}

    if "tasks" not in team.workflow_session_state:
        team.workflow_session_state["tasks"] = []

    task = {"name": task_name, "assignee": assignee, "status": "pending"}
    team.workflow_session_state["tasks"].append(task)

    return f"Added task '{task_name}' assigned to {assignee}"


def delete_task(team: Team, task_name: str) -> str:
    """Delete a task from the team's task list."""
    if (
        team.workflow_session_state is None
        or "tasks" not in team.workflow_session_state
    ):
        return "No tasks found to delete"

    tasks = team.workflow_session_state["tasks"]
    for i, task in enumerate(tasks):
        if task["name"] == task_name:
            deleted_task = tasks.pop(i)
            return f"Deleted task '{task_name}' that was assigned to {deleted_task['assignee']}"

    return f"Task '{task_name}' not found"


# === AGENT TOOL ===
def display_tasks(agent: Agent) -> str:
    """Display all tasks from the agent's workflow session state."""
    if (
        agent.workflow_session_state is None
        or "tasks" not in agent.workflow_session_state
    ):
        return "No tasks found"

    tasks = agent.workflow_session_state["tasks"]
    if not tasks:
        return "Task list is empty"

    result = "Current tasks:\n"
    for i, task in enumerate(tasks, 1):
        result += f"{i}. {task['name']} (assigned to: {task['assignee']}, status: {task['status']})\n"

    return result


# === CREATE AGENTS ===
task_manager = Agent(
    name="TaskManager",
    model=OpenAIChat(id="gpt-4o-mini"),
    instructions=["You manage tasks by adding and deleting them as requested."],
)

task_coordinator = Agent(
    name="TaskCoordinator",
    model=OpenAIChat(id="gpt-4o-mini"),
    instructions=["You help coordinate tasks and provide task management support."],
)

task_viewer = Agent(
    name="TaskViewer",
    model=OpenAIChat(id="gpt-4o-mini"),
    tools=[display_tasks],
    instructions=[
        "You display and view tasks. Use the display_tasks function to show current tasks."
    ],
)

# === CREATE TEAM ===
management_team = Team(
    name="ManagementTeam",
    members=[task_manager, task_coordinator],
    tools=[add_task, delete_task],
    instructions=[
        "You are a task management team.",
        "Use add_task to create new tasks and delete_task to remove tasks.",
        "Coordinate between team members to manage tasks effectively.",
    ],
    mode="coordinate",
)

# === CREATE TASKS ===
manage_tasks_task = Task(
    name="manage_tasks",
    description="Team manages tasks by adding and deleting them",
    team=management_team,
)

display_tasks_task = Task(
    name="display_tasks",
    description="Agent displays the current tasks",
    agent=task_viewer,
)

# === CREATE WORKFLOW ===
simple_workflow = Workflow(
    name="Simple Task Management",
    tasks=[manage_tasks_task, display_tasks_task],
    workflow_session_state={"tasks": []},  # Initialize with empty task list
)

if __name__ == "__main__":
    # Example 1: Add a task
    print("=== Example 1: Add Task ===")
    simple_workflow.print_response(
        message="Add a task called 'Write Documentation' assigned to John"
    )

    print("Current workflow session state:", simple_workflow.workflow_session_state)

    # Example 2: Add another task and then display all tasks
    print("\n=== Example 2: Add Another Task and Display ===")
    simple_workflow.print_response(
        message="Add a task called 'Code Review' assigned to Sarah, then display all tasks"
    )

    print("Current workflow session state:", simple_workflow.workflow_session_state)

    # Example 3: Delete a task and display remaining tasks
    print("\n=== Example 3: Delete Task and Display ===")
    simple_workflow.print_response(
        message="Delete the 'Write Documentation' task, then display remaining tasks"
    )

    print("\nFinal workflow session state:", simple_workflow.workflow_session_state)
