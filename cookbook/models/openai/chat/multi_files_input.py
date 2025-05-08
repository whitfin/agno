from agno.agent import Agent
from agno.media import File
from agno.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="gpt-4.1"),
    markdown=True,
    add_history_to_messages=True,
    debug_mode=True,
)

agent.print_response(
    "Analyze all the files and give me a summary of the content",
    files=[
        File(filepath="tmp/plan.md"),
        File(filepath="tmp/car.json"),
        File(filepath="tmp/boston_housing.csv"),
        File(filepath="tmp/LSTM.pdf"),
        File(url="https://agno-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"),
    ],
)
