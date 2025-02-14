import os
import requests
from uuid import uuid4
from agno.agent import Agent, RunResponse
from agno.models.openai import OpenAIChat
from agno.tools.models_labs import FileType, ModelsLabTools
from agno.utils.log import logger

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
    ],
    markdown=True,
    debug_mode=True,
)

music: RunResponse = agent.run("Generate a 30 second classical music piece")

save_dir = "audio_generations"

if music.audio is not None and len(music.audio) > 0:
    url = music.audio[0].url
    response = requests.get(url)
    # Create tmp directory if it doesn't exist
    os.makedirs(save_dir, exist_ok=True)
    filename = f"{save_dir}/sample_music{uuid4()}.wav"
    with open(filename, "wb") as f:
        f.write(response.content)
    logger.info(f"Music saved to {filename}")
