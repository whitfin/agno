from agno.agent import Agent
from agno.media import File
from agno.models.groq import Groq

agent = Agent(
    model=Groq(id="meta-llama/llama-4-maverick-17b-128e-instruct"),
    description="You are a helpful assistant that can read PDF files.",
    debug_mode=True,
)

file_local = File(filepath="tmp/sample.pdf")
agent.print_response(
    "explain to me the DC microgrid structure and control figure", files=[file_local]
)
