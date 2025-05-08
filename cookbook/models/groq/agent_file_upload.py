from agno.agent import Agent
from agno.media import File
from agno.models.groq import Groq

agent = Agent(
    model=Groq(id="meta-llama/llama-4-maverick-17b-128e-instruct"),
    description="You are a helpful assistant that can read PDF files.",
    debug_mode=True,
)

# file_local = File(filepath="tmp/LSTM.pdf")
file_local = File(
    url="https://www.jsu.edu/business/fea/docs/financial_stament_review.pdf"
)
agent.print_response(
    "What is the Cost of Goods Sold based on the document?", files=[file_local]
)
