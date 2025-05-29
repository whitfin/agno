from __future__ import annotations

from agno.agent import Agent
from agno.tools.function import Function
from agno.models.openai import OpenAIChat

# Tool for updating step state (frontend-only tool)
update_steps_tool = Function(
    name="update_steps",
    description="Update the current state of task execution steps",
    parameters={
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "status": {"type": "string", "enum": ["pending", "completed"]}
                    },
                    "required": ["description", "status"]
                }
            }
        },
        "required": ["steps"]
    },
    entrypoint=lambda steps: "Steps updated successfully"
)

# Tool for marking a step as started
start_step_tool = Function(
    name="start_step",
    description="Mark a step as currently being executed",
    parameters={
        "type": "object",
        "properties": {
            "step_name": {"type": "string"}
        },
        "required": ["step_name"]
    },
    entrypoint=lambda step_name: f"Started step: {step_name}"
)

# Tool for marking a step as completed
complete_step_tool = Function(
    name="complete_step",
    description="Mark a step as completed",
    parameters={
        "type": "object",
        "properties": {
            "step_name": {"type": "string"}
        },
        "required": ["step_name"]
    },
    entrypoint=lambda step_name: f"Completed step: {step_name}"
)

# Minimal agent with clear instructions
AgenticGenerativeUIAgent = Agent(
    name="AgenticGenerativeUIAgent",
    model=OpenAIChat(id="gpt-4o"),
    instructions="""When the user asks you to plan something:

1. FIRST: Call update_steps with an array of 3-5 steps (all with status 'pending')
2. THEN: Write a brief message saying you'll work through the steps
3. For each step:
   - Call start_step with the step description
   - Write 1-2 sentences about that step
   - Call complete_step with the step description
4. End with a brief summary

IMPORTANT: You MUST call the tools. Do not output JSON as text.""",
    tools=[update_steps_tool, start_step_tool, complete_step_tool],
    stream=True,
    markdown=True,
    show_tool_calls=True,
    tool_choice="required"
)