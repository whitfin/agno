from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.models.openai.chat import OpenAIChat

agent = Agent(
    model=Claude(id="claude-3-7-sonnet-latest"),
    instructions="You are an agent focused on responding in one line. All your responses must be super concise and focused.",
    markdown=True,
)
agent.print_response("What is the stock price of Apple?", stream=True)

agent.instructions = "You are an agent focused on responding in depth. All your responses must be super detailed and focused."
agent.print_response("What is the stock price of Apple?", stream=True)


model = OpenAIChat(id="gpt-4o", temperature=0.2)
agent = Agent(model=model)
