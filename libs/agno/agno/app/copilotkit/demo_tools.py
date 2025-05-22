from agno.agent.agent import Agent
from agno.models.openai.chat import OpenAIChat
from agno.tools.function import Function
from agno.app.copilotkit.app import CopilotKitApp


def multiply_numbers(a: int, b: int) -> int:  # noqa: D401
    """Multiply two integers and return the result.

    Args:
        a (int): First number.
        b (int): Second number.

    Returns:
        int: The product of the two numbers.
    """
    return a * b


# Wrap the Python function in an AGNO Function so the LLM can call it
calculator_tool = Function.from_callable(multiply_numbers)


class ToolAgent(Agent):
    """An example agent that can execute a calculator tool via function-calling."""

    def __init__(self):
        super().__init__(
            model=OpenAIChat(id="gpt-4o"),  # Use any model that supports tool calls
            description="You are a helpful assistant that can perform basic arithmetic using the provided tool.",
            instructions="When the user asks you to perform a calculation, call the appropriate tool with the correct arguments.  Only use the tool when necessary.",
            tools=[calculator_tool],
            show_tool_calls=True,
            stream=True,
        )


# Create the FastAPI application that CopilotKit frontend will connect to
app = CopilotKitApp(agent=ToolAgent()).get_app(use_async=False) 