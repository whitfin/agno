from agno.agent import Agent

agent = Agent(
    name="Debug Agent",
    instructions="You are a debug agent. You are given a task and you need to debug it.",
)

agent.run("What is the capital of France?" , debug_mode=True)

print("Debug mode: True")
run_response = agent.run("What is the capital of France?" , debug_mode=False)
print(run_response)