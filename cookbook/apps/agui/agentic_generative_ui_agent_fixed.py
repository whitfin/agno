from __future__ import annotations

from agno.agent import Agent
from agno.tools.function import Function
from agno.models.openai import OpenAIChat
import logging

logger = logging.getLogger(__name__)

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
    entrypoint=lambda steps: {
        "result": "Steps updated successfully",
        "steps_count": len(steps) if isinstance(steps, list) else 0
    }
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
    entrypoint=lambda step_name: {
        "result": f"Started step: {step_name}",
        "step_name": step_name
    }
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
    entrypoint=lambda step_name: {
        "result": f"Completed step: {step_name}",
        "step_name": step_name
    }
)

# Create the agent with frontend tools
agentive_generative_ui_agent_fixed = Agent(
    name="agentiveGenerativeUIAgent",
    model=OpenAIChat(
        id="gpt-4o-mini",
        temperature=0.7,  # Add some temperature for variety
    ),
    tools=[update_steps_tool, start_step_tool, complete_step_tool],
    instructions="""You are an AI assistant that helps users by breaking down tasks into clear steps and tracking progress visually.

CRITICAL RULES FOR TOOL USAGE:
1. ALWAYS use the provided tools to update the UI. Never write tool calls as text.
2. When given a task, IMMEDIATELY call update_steps with ALL planned steps (status="pending")
3. For EACH step, call the tools in this EXACT order:
   - start_step with the exact step description
   - Provide helpful information about that step
   - complete_step with the exact step description
4. NEVER repeat tool calls. Each tool should be called exactly ONCE per step.
5. Use the EXACT description text from update_steps as the step_name parameter.

EXAMPLE FLOW for "Help me make tea":
1. First call: update_steps([
     {"description": "Boil water", "status": "pending"},
     {"description": "Prepare tea cup", "status": "pending"},
     {"description": "Add tea bag", "status": "pending"},
     {"description": "Pour hot water", "status": "pending"},
     {"description": "Let it steep", "status": "pending"}
   ])
2. Then for each step:
   - start_step("Boil water") → explain → complete_step("Boil water")
   - start_step("Prepare tea cup") → explain → complete_step("Prepare tea cup")
   - And so on...

Remember: Each tool call should have a unique purpose. Do not call the same tool multiple times with the same parameters.""",
    markdown=True,
    stream=True,
    # Ensure tools are always available
    tool_choice="auto"
)

# Mark tools as frontend-only
for tool in agentive_generative_ui_agent_fixed.tools:
    tool._frontend_only = True
    logger.info(f"Marked tool '{tool.name}' as frontend-only") 