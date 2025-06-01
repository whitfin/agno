from agno.agent import Agent
from agno.models.anthropic import Claude

agent = Agent(model=Claude(id="claude-4-sonnet-20250514"), markdown=True)
agent.print_response("What is the stock price of Apple?", stream=True)
