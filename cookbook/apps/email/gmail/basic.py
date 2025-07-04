from agno.agent import Agent
from agno.app.email.gmail.app import GmailAPI
from agno.app.email.gmail.setup import runsetup
from agno.models.openai import OpenAIChat

basic_agent = Agent(
    name="Basic Agent",
    model=OpenAIChat(id="gpt-4o"),
    add_history_to_messages=True,
    num_history_responses=3,
    add_datetime_to_instructions=True,
    markdown=True,
)

gmail_app = GmailAPI(
    agent=basic_agent,
    name="Basic Agent",
    app_id="basic_agent",
    description="A basic agent that can answer questions and help with tasks.",
)
#runsetup(topic_name='projects/agnotest-464115/topics/mail',cred_path="D:\\Work\\agnoagi\\agno\\libs\\agno\\agno\\app\\email\\gmail\\credentials.json")
app = gmail_app.get_app()

if __name__ == "__main__":
    gmail_app.serve(app="basic:app", port=8000, reload=True)
