from cookbook.apps.agui.agentic_generative_ui_minimal import AgenticGenerativeUIAgent

messages = [{"role": "user", "content": "Plan a vacation to Japan"}]

for chunk in AgenticGenerativeUIAgent.run(messages, stream=True):
    if chunk.content:
        print(chunk.content, end="", flush=True)
    if hasattr(chunk, 'tools') and chunk.tools:
        for tool in chunk.tools:
            print("\nTool call:", tool) 