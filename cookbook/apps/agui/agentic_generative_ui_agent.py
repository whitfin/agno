from __future__ import annotations

from agno.agent import Agent
from agno.tools.function import Function
from agno.models.openai import OpenAIChat

# Tool for updating step state (frontend-only tool)
update_steps_tool = Function(
    name="update_steps",
    description="Update the current state of task execution steps to show progress to the user.",
    parameters={
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Brief description of what this step involves"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "completed"],
                            "description": "Current status of the step"
                        }
                    },
                    "required": ["description", "status"],
                    "additionalProperties": False
                },
                "description": "Array of steps with their current status"
            }
        },
        "required": ["steps"],
        "additionalProperties": False
    },
    entrypoint=lambda steps: "Steps updated successfully"
)

# Tool for starting a step (frontend-only tool)
start_step_tool = Function(
    name="start_step",
    description="Mark a specific step as started/active.",
    parameters={
        "type": "object",
        "properties": {
            "step_name": {
                "type": "string",
                "description": "Name or description of the step being started"
            }
        },
        "required": ["step_name"],
        "additionalProperties": False
    },
    entrypoint=lambda step_name: f"Started step: {step_name}"
)

# Tool for completing a step (frontend-only tool)
complete_step_tool = Function(
    name="complete_step",
    description="Mark a specific step as completed.",
    parameters={
        "type": "object",
        "properties": {
            "step_name": {
                "type": "string",
                "description": "Name or description of the step being completed"
            }
        },
        "required": ["step_name"],
        "additionalProperties": False
    },
    entrypoint=lambda step_name: f"Completed step: {step_name}"
)

# Create the agent with frontend tools
agentive_generative_ui_agent = Agent(
    name="agentiveGenerativeUIAgent",
    model=OpenAIChat(id="gpt-4o-mini"),
    tools=[update_steps_tool, start_step_tool, complete_step_tool],
    instructions="""You are an AI assistant that helps users by breaking down tasks into clear steps and tracking progress visually.

IMPORTANT: You MUST use the tools provided to update the UI. Do NOT write tool calls as text.

When given any task:
1. Immediately call the update_steps tool with all planned steps (status="pending")
2. For each step:
   - Call start_step with the exact step_name
   - Provide helpful information or perform the step
   - Call complete_step with the exact step_name

Always use the exact description text from update_steps as the step_name in start_step and complete_step.

Remember: Use the actual tool functions, don't just describe what you would do.""",
    markdown=True,
    stream=True,
) 