from agno.agent import Agent
from agno.tools.whatsapp import WhatsAppTools

agent = Agent(
    name="whatsapp",
    tools=[WhatsAppTools()],
)

agent.print_response("Send message to whatsapp chat a paragraph about the moon")
