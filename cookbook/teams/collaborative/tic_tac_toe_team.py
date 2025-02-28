from textwrap import dedent

from agno.agent import Agent
from agno.models.google.gemini import Gemini
from agno.models.openai import OpenAIChat
from agno.team.team import Team

player_1 = Agent(
    name="Player 1",
    role="Play Tic Tac Toe",
    model=OpenAIChat(id="gpt-4.5-preview"),
    add_name_to_instructions=True,
    instructions=dedent("""
    You are a Tic Tac Toe player.
    You will be given a Tic Tac Toe board and a player to play against.
    You will need to play the game and try to win.
    """),
)

player_2 = Agent(
    name="Player 2",
    role="Play Tic Tac Toe",
    model=Gemini(id="gemini-2.0-flash"),
    add_name_to_instructions=True,
    instructions=dedent("""
    You are a Tic Tac Toe player.
    You will be given a Tic Tac Toe board and a player to play against.
    You will need to play the game and try to win.
    """),
)


agent_team = Team(
    name="Tic Tac Toe Team",
    mode="collaborative",
    model=OpenAIChat("gpt-4o"),
    members=[player_1, player_2],
    instructions=[
        "You are a games master.",
        "You have to stop the game when one of the players has won.",
        "Initialize the board state as empty.",
        "Store the board state between runs.",
        "Show the updated board state in your response each time."
    ],
    send_team_context_to_members=True,
    update_team_context=True,
    show_tool_calls=True,
    markdown=True,
    verbose=True,
)

agent_team.print_response(
    message="Play Tic Tac Toe",
    stream=True,
    stream_intermediate_steps=True,
)
