from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.models_labs import ModelsLabTools, FileType
from agno.storage.agent.sqlite import SqliteAgentStorage
from agno.agent import Agent, RunResponse
from agno.utils.audio import write_audio_to_file

agent = Agent(
    name="ModelsLab Music Agent",
    agent_id="ml_music_agent",
    model=OpenAIChat(id="gpt-4o"),
    show_tool_calls=True,
    tools=[ModelsLabTools(wait_for_completion=True, file_type=FileType.MP3)],
    description="You are an AI agent that can generate music using the ModelsLabs API.",
    instructions=[
        "When generating music, use the `generate_media` tool with detailed prompts that specify:",
        "- The genre and style of music (e.g., classical, jazz, electronic)",
        "- The instruments and sounds to include",
        "- The tempo, mood and emotional qualities",
        "- The structure (intro, verses, chorus, bridge, etc.)",
        "Create rich, descriptive prompts that capture the desired musical elements.",
        "Focus on generating high-quality, complete instrumental pieces.",
        "Keep responses simple and only confirm when music is generated successfully.",
        "Give the music link in the response",
    ],
    markdown=True,
    debug_mode=True,
)

music: RunResponse = agent.run(
    "Generate a 30 second classical music piece"
)
if music.response_audio is not None:
    write_audio_to_file(
        audio=music.response_audio.content, filename="tmp/sample_music.wav"
    )

# agent.print_response(
#     "Generate a 30 second classical music piece"
# )