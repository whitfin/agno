from agno.agent import Agent
from agno.models.runpod import RunPod

# Create an agent with RunPod model
agent = Agent(
    model=RunPod(
        endpoint_id="https://api.runpod.ai/v2/9efv0w6dg0rwaj/openai/v1",
    ),
    markdown=True,
)

# Use the agent
agent.print_response("What is serverless computing?")

# You can also access the raw response
# run = agent.run("Explain machine learning in simple terms")
# print(f"Response: {run.content}")

print("✅ RunPod integration is working!")

# Note: Your RunPod endpoint should expect input in one of these formats:
# 1. {"input": "your prompt here"} - for simple text generation
# 2. {"input": {"messages": [{"role": "user", "content": "your prompt"}]}} - for chat models 