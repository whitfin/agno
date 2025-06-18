from typing import Any, Dict, Optional

from agno.agent.agent import Agent
from agno.models.openai.chat import OpenAIChat
from agno.team.team import Team
from agno.workflow.v2.step import Step
from agno.workflow.v2.workflow import Workflow


# === TEAM TOOLS ===
def add_step(team: Team, step_name: str, assignee: str) -> str:
    """Add a step to the team's step list."""
    if team.workflow_session_state is None:
        team.workflow_session_state = {}

    if "steps" not in team.workflow_session_state:
        team.workflow_session_state["steps"] = []

    step = {"name": step_name, "assignee": assignee, "status": "pending"}
    team.workflow_session_state["steps"].append(step)

    return f"Added step '{step_name}' assigned to {assignee}"


def delete_step(team: Team, step_name: str) -> str:
    """Delete a step from the team's step list."""
    if (
        team.workflow_session_state is None
        or "steps" not in team.workflow_session_state
    ):
        return "No steps found to delete"

    steps = team.workflow_session_state["steps"]
    for i, step in enumerate(steps):
        if step["name"] == step_name:
            deleted_step = steps.pop(i)
            return f"Deleted step '{step_name}' that was assigned to {deleted_step['assignee']}"

    return f"Step '{step_name}' not found"


# === AGENT TOOL ===
def display_steps(agent: Agent) -> str:
    """Display all steps from the agent's workflow session state."""
    if (
        agent.workflow_session_state is None
        or "steps" not in agent.workflow_session_state
    ):
        return "No steps found"

    steps = agent.workflow_session_state["steps"]
    if not steps:
        return "Step list is empty"

    result = "Current steps:\n"
    for i, step in enumerate(steps, 1):
        result += f"{i}. {step['name']} (assigned to: {step['assignee']}, status: {step['status']})\n"

    return result


# === CREATE AGENTS ===
step_manager = Agent(
    name="StepManager",
    model=OpenAIChat(id="gpt-4o-mini"),
    instructions=["You manage steps by adding and deleting them as requested."],
)

step_coordinator = Agent(
    name="StepCoordinator",
    model=OpenAIChat(id="gpt-4o-mini"),
    instructions=["You help coordinate steps and provide step management support."],
)

step_viewer = Agent(
    name="StepViewer",
    model=OpenAIChat(id="gpt-4o-mini"),
    tools=[display_steps],
    instructions=[
        "You display and view steps. Use the display_steps function to show current steps."
    ],
)

# === CREATE TEAM ===
management_team = Team(
    name="ManagementTeam",
    members=[step_manager, step_coordinator],
    tools=[add_step, delete_step],
    instructions=[
        "You are a step management team.",
        "Use add_step to create new steps and delete_step to remove steps.",
        "Coordinate between team members to manage steps effectively.",
    ],
    mode="coordinate",
)

# === CREATE STEPS ===
manage_steps_step = Step(
    name="manage_steps",
    description="Team manages steps by adding and deleting them",
    team=management_team,
)

display_steps_step = Step(
    name="display_steps",
    description="Agent displays the current steps",
    agent=step_viewer,
)

# === CREATE WORKFLOW ===
simple_workflow = Workflow(
    name="Simple Step Management",
    steps=[manage_steps_step, display_steps_step],
    workflow_session_state={"steps": []},  # Initialize with empty step list
)

if __name__ == "__main__":
    # Example 1: Add a step
    print("=== Example 1: Add Step ===")
    simple_workflow.print_response(
        message="Add a step called 'Write Documentation' assigned to John"
    )

    print("Current workflow session state:", simple_workflow.workflow_session_state)

    # Example 2: Add another step and then display all steps
    print("\n=== Example 2: Add Another Step and Display ===")
    simple_workflow.print_response(
        message="Add a step called 'Code Review' assigned to Sarah, then display all steps"
    )

    print("Current workflow session state:", simple_workflow.workflow_session_state)

    # Example 3: Delete a step and display remaining steps
    print("\n=== Example 3: Delete Step and Display ===")
    simple_workflow.print_response(
        message="Delete the 'Write Documentation' step, then display remaining steps"
    )

    print("\nFinal workflow session state:", simple_workflow.workflow_session_state)
