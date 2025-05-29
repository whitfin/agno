from __future__ import annotations

from agno.agent import Agent
from agno.tools.function import Function
from agno.models.openai import OpenAIChat

# Calculator tools
add_tool = Function(
    name="add",
    description="Add two numbers together",
    parameters={
        "type": "object",
        "properties": {
            "a": {"type": "number", "description": "First number"},
            "b": {"type": "number", "description": "Second number"}
        },
        "required": ["a", "b"]
    },
    entrypoint=lambda a, b: f"The sum of {a} and {b} is {a + b}"
)

subtract_tool = Function(
    name="subtract",
    description="Subtract one number from another",
    parameters={
        "type": "object",
        "properties": {
            "a": {"type": "number", "description": "Number to subtract from"},
            "b": {"type": "number", "description": "Number to subtract"}
        },
        "required": ["a", "b"]
    },
    entrypoint=lambda a, b: f"The difference of {a} minus {b} is {a - b}"
)

multiply_tool = Function(
    name="multiply",
    description="Multiply two numbers",
    parameters={
        "type": "object",
        "properties": {
            "a": {"type": "number", "description": "First number"},
            "b": {"type": "number", "description": "Second number"}
        },
        "required": ["a", "b"]
    },
    entrypoint=lambda a, b: f"The product of {a} and {b} is {a * b}"
)

divide_tool = Function(
    name="divide",
    description="Divide one number by another",
    parameters={
        "type": "object",
        "properties": {
            "a": {"type": "number", "description": "Dividend"},
            "b": {"type": "number", "description": "Divisor (cannot be zero)"}
        },
        "required": ["a", "b"]
    },
    entrypoint=lambda a, b: f"The quotient of {a} divided by {b} is {a / b}" if b != 0 else "Error: Division by zero"
)

# Create calculator agent
CalculatorAgent = Agent(
    name="CalculatorAgent",
    model=OpenAIChat(id="gpt-4o-mini"),
    description="A calculator assistant that can perform basic math operations",
    instructions="""You are a helpful calculator assistant. You can perform basic math operations using the provided tools.

When users ask you to calculate something:
1. Use the appropriate tool (add, subtract, multiply, or divide)
2. Show the calculation clearly
3. Provide the result

Be friendly and helpful. If asked to do complex calculations, break them down into steps using the basic operations available.""",
    tools=[add_tool, subtract_tool, multiply_tool, divide_tool],
    markdown=True,
    stream=True,
) 