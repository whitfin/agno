# import json
# from datetime import datetime

# from agno.agent import Agent
# from agno.models.google import Gemini
# from agno.tools.thinking import ThinkingTools
# from agno.tools.yfinance import YFinanceTools
# from agno.run.response import RunEvent
# from agno.models.openai import OpenAIChat
# from agno.tools.reasoning import ReasoningTools
# from textwrap import dedent
# import asyncio

# # Create a timestamp for the filename
# timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
# output_file = f"reasoning_data_{timestamp}.txt"

# # Create the agent
# agent1 = Agent(
#     # model=Gemini(id="gemini-2.0-flash"),
#     tools=[
#         # ThinkingTools(add_instructions=True),
#         YFinanceTools(
#             stock_price=True,
#             analyst_recommendations=True,
#             company_info=True,
#             company_news=True,
#         ),
#     ],
#     instructions="Use tables where possible",
#     show_tool_calls=True,
#     reasoning=True,
#     markdown=True,
#     stream_intermediate_steps=True
# )

# agent2 = Agent(
#     model=OpenAIChat(id="gpt-4o"),
#     tools=[ReasoningTools(add_instructions=True)],
#     instructions=dedent("""\
#         You are an expert problem-solving assistant with strong analytical skills! 🧠
        
#         Your approach to problems:
#         1. First, break down complex questions into component parts
#         2. Clearly state your assumptions
#         3. Develop a structured reasoning path
#         4. Consider multiple perspectives
#         5. Evaluate evidence and counter-arguments
#         6. Draw well-justified conclusions
        
#         When solving problems:
#         - Use explicit step-by-step reasoning
#         - Identify key variables and constraints
#         - Explore alternative scenarios
#         - Highlight areas of uncertainty
#         - Explain your thought process clearly
#         - Consider both short and long-term implications
#         - Evaluate trade-offs explicitly
        
#         For quantitative problems:
#         - Show your calculations
#         - Explain the significance of numbers
#         - Consider confidence intervals when appropriate
#         - Identify source data reliability
        
#         For qualitative reasoning:
#         - Assess how different factors interact
#         - Consider psychological and social dynamics
#         - Evaluate practical constraints
#         - Address value considerations
#         \
#     """),
#     add_datetime_to_instructions=True,
#     stream_intermediate_steps=True,
#     show_tool_calls=True,
#     markdown=True,
# )

# # Open file for writing and KEEP IT OPEN through the loop
# with open(output_file, "w") as f:
#     f.write("Query: Write a report comparing NVDA to TSLA in detail\n\n")

#     # Track reasoning events - inside the with block
#     for chunk in agent2.run("Write a report comparing NVDA to TSLA in detail", stream=True):
#         # Only process reasoning-related events
#         if chunk.event in ["ReasoningStarted", "ReasoningStep", "ReasoningCompleted"]:
#             # Write the event type
#             event_info = f"\n=== EVENT: {chunk.event} ===\n"
#             f.write(event_info)
#             print(event_info, end="")

#             # Write content information
#             try:
#                 # Different handling based on content type
#                 if hasattr(chunk.content, "dict"):
#                     # For Pydantic models
#                     content_json = json.dumps(chunk.content.dict(), indent=2)
#                 elif hasattr(chunk.content, "__dict__") and not isinstance(chunk.content, str):
#                     # For regular objects
#                     content_json = json.dumps(chunk.content.__dict__, indent=2)
#                 else:
#                     # For primitive types
#                     content_json = json.dumps(chunk.content, indent=2)

#                 f.write(f"Content (JSON):\n{content_json}\n")
#                 print(f"Content (JSON):\n{content_json}\n")
#             except Exception as e:
#                 # Fallback to string representation
#                 f.write(f"Content (as string):\n{str(chunk.content)}\n")
#                 print(f"Content (as string):\n{str(chunk.content)}\n")
#                 f.write(f"JSON conversion error: {str(e)}\n")
#                 print(f"JSON conversion error: {str(e)}\n")

#             # Add extra_data if it exists
#             if hasattr(chunk, "extra_data") and chunk.extra_data is not None:
#                 try:
#                     # Process extra_data to specifically capture reasoning_messages
#                     extra_data_dict = {}

#                     # Convert extra_data to a dictionary
#                     if hasattr(chunk.extra_data, "dict"):
#                         extra_data_dict = chunk.extra_data.dict()
#                     elif hasattr(chunk.extra_data, "__dict__") and not isinstance(chunk.extra_data, str):
#                         extra_data_dict = chunk.extra_data.__dict__
#                     else:
#                         extra_data_dict = chunk.extra_data if isinstance(chunk.extra_data, dict) else {
#                             "raw": str(chunk.extra_data)}

#                     # Specifically process reasoning_messages if they exist
#                     if "reasoning_messages" in extra_data_dict and extra_data_dict["reasoning_messages"]:
#                         reasoning_messages = []

#                         # Process each message in reasoning_messages
#                         for msg in extra_data_dict["reasoning_messages"]:
#                             if hasattr(msg, "dict"):
#                                 reasoning_messages.append(msg.dict())
#                             elif hasattr(msg, "__dict__") and not isinstance(msg, str):
#                                 reasoning_messages.append(msg.__dict__)
#                             else:
#                                 reasoning_messages.append(str(msg))

#                         # Replace the original messages with the processed ones
#                         extra_data_dict["reasoning_messages"] = reasoning_messages

#                     # Convert the final dictionary to JSON
#                     extra_data_json = json.dumps(
#                         extra_data_dict, indent=2, default=str)

#                     f.write(f"Extra Data (JSON):\n{extra_data_json}\n")
#                     print(f"Extra Data (JSON):\n{extra_data_json}\n")
#                 except Exception as e:
#                     f.write(
#                         f"Extra Data (as string):\n{str(chunk.extra_data)}\n")
#                     print(
#                         f"Extra Data (as string):\n{str(chunk.extra_data)}\n")
#                     f.write(f"Extra Data JSON conversion error: {str(e)}\n")
#                     print(f"Extra Data JSON conversion error: {str(e)}\n")

#             # Also include reasoning_content if available
#             if hasattr(chunk, "reasoning_content") and chunk.reasoning_content:
#                 f.write(f"Reasoning Content:\n{chunk.reasoning_content}\n")
#                 print(f"Reasoning Content:\n{chunk.reasoning_content}\n")

#             # Add a separator
#             f.write("\n" + "-"*50 + "\n")
#             print("\n" + "-"*50)

#     # This line stays inside the with block
#     print(f"\nReasoning data has been written to {output_file}")


# # # """
# # # This example demonstrates how it works when you pass a non-reasoning model as a reasoning model.
# # # It defaults to using the default OpenAI reasoning model.
# # # We recommend using the appropriate reasoning model or passing reasoning=True for the default COT.
# # # """

# # # from agno.agent import Agent
# # # from agno.models.openai import OpenAIChat

# # # # It uses the default model of the Agent
# # # reasoning_agent = Agent(
# # #     reasoning=True,
# # #     markdown=True,
# # # )
# # # reasoning_agent.print_response(
# # #     "Give me steps to write a python script for fibonacci series",
# # #     stream=True,
# # #     show_full_reasoning=True,
# # # )

# # """🧠 Problem-Solving Reasoning Agent

# # This example shows how to create an agent that uses the ReasoningTools to solve
# # complex problems through step-by-step reasoning. The agent breaks down questions,
# # analyzes intermediate results, and builds structured reasoning paths to arrive at
# # well-justified conclusions.

# # Example prompts to try:
# # - "Solve this logic puzzle: A man has to take a fox, a chicken, and a sack of grain across a river."
# # - "Is it better to rent or buy a home given current interest rates?"
# # - "Evaluate the pros and cons of remote work versus office work."
# # - "How would increasing interest rates affect the housing market?"
# # - "What's the best strategy for saving for retirement in your 30s?"
# # """

# # from textwrap import dedent

# # from agno.agent import Agent
# # from agno.models.openai import OpenAIChat
# # from agno.tools.reasoning import ReasoningTools

# # reasoning_agent = Agent(
# #     model=OpenAIChat(id="gpt-4o"),
# #     tools=[ReasoningTools(add_instructions=True)],
# #     instructions=dedent("""\
# #         You are an expert problem-solving assistant with strong analytical skills! 🧠
        
# #         Your approach to problems:
# #         1. First, break down complex questions into component parts
# #         2. Clearly state your assumptions
# #         3. Develop a structured reasoning path
# #         4. Consider multiple perspectives
# #         5. Evaluate evidence and counter-arguments
# #         6. Draw well-justified conclusions
        
# #         When solving problems:
# #         - Use explicit step-by-step reasoning
# #         - Identify key variables and constraints
# #         - Explore alternative scenarios
# #         - Highlight areas of uncertainty
# #         - Explain your thought process clearly
# #         - Consider both short and long-term implications
# #         - Evaluate trade-offs explicitly
        
# #         For quantitative problems:
# #         - Show your calculations
# #         - Explain the significance of numbers
# #         - Consider confidence intervals when appropriate
# #         - Identify source data reliability
        
# #         For qualitative reasoning:
# #         - Assess how different factors interact
# #         - Consider psychological and social dynamics
# #         - Evaluate practical constraints
# #         - Address value considerations
# #         \
# #     """),
# #     add_datetime_to_instructions=True,
# #     stream_intermediate_steps=True,
# #     show_tool_calls=True,
# #     markdown=True,
# # )

# # # Example usage with a complex reasoning problem
# # reasoning_agent.print_response(
# #     "Solve this logic puzzle: A man has to take a fox, a chicken, and a sack of grain across a river. "
# #     "The boat is only big enough for the man and one item. If left unattended together, the fox will "
# #     "eat the chicken, and the chicken will eat the grain. How can the man get everything across safely?",
# #     stream=True,
# # )

# # # # Economic analysis example
# # # reasoning_agent.print_response(
# # #     "Is it better to rent or buy a home given current interest rates, inflation, and market trends? "
# # #     "Consider both financial and lifestyle factors in your analysis.",
# # #     stream=True
# # # )

# # # # Strategic decision-making example
# # # reasoning_agent.print_response(
# # #     "A startup has $500,000 in funding and needs to decide between spending it on marketing or "
# # #     "product development. They want to maximize growth and user acquisition within 12 months. "
# # #     "What factors should they consider and how should they analyze this decision?",
# # #     stream=True
# # # )

"""🧠 Problem-Solving Reasoning Agent

This example shows how to create an agent that uses the ReasoningTools to solve
complex problems through step-by-step reasoning. The agent breaks down questions,
analyzes intermediate results, and builds structured reasoning paths to arrive at
well-justified conclusions.

Example prompts to try:
- "Solve this logic puzzle: A man has to take a fox, a chicken, and a sack of grain across a river."
- "Is it better to rent or buy a home given current interest rates?"
- "Evaluate the pros and cons of remote work versus office work."
- "How would increasing interest rates affect the housing market?"
- "What's the best strategy for saving for retirement in your 30s?"
"""

from textwrap import dedent

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.reasoning import ReasoningTools
import asyncio

reasoning_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[ReasoningTools(add_instructions=True)],
    instructions=dedent("""\
        You are an expert problem-solving assistant with strong analytical skills! 🧠
        
        Your approach to problems:
        1. First, break down complex questions into component parts
        2. Clearly state your assumptions
        3. Develop a structured reasoning path
        4. Consider multiple perspectives
        5. Evaluate evidence and counter-arguments
        6. Draw well-justified conclusions
        
        When solving problems:
        - Use explicit step-by-step reasoning
        - Identify key variables and constraints
        - Explore alternative scenarios
        - Highlight areas of uncertainty
        - Explain your thought process clearly
        - Consider both short and long-term implications
        - Evaluate trade-offs explicitly
        
        For quantitative problems:
        - Show your calculations
        - Explain the significance of numbers
        - Consider confidence intervals when appropriate
        - Identify source data reliability
        
        For qualitative reasoning:
        - Assess how different factors interact
        - Consider psychological and social dynamics
        - Evaluate practical constraints
        - Address value considerations
        \
    """),
    add_datetime_to_instructions=True,
    stream_intermediate_steps=True,
    show_tool_calls=True,
    markdown=True,
)

# Example usage with a complex reasoning problem
asyncio.run(reasoning_agent.aprint_response(
    "Solve this logic puzzle: A man has to take a fox, a chicken, and a sack of grain across a river. "
    "The boat is only big enough for the man and one item. If left unattended together, the fox will "
    "eat the chicken, and the chicken will eat the grain. How can the man get everything across safely?",
    stream=True,
))

# # Economic analysis example
# reasoning_agent.print_response(
#     "Is it better to rent or buy a home given current interest rates, inflation, and market trends? "
#     "Consider both financial and lifestyle factors in your analysis.",
#     stream=True
# )

# # Strategic decision-making example
# reasoning_agent.print_response(
#     "A startup has $500,000 in funding and needs to decide between spending it on marketing or "
#     "product development. They want to maximize growth and user acquisition within 12 months. "
#     "What factors should they consider and how should they analyze this decision?",
#     stream=True
# )
