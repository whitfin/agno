from pathlib import Path
from agno.agent import Agent
from agno.media import Image
from agno.models.openai import OpenAIChat
from agno.tools.dalle import DalleTools

image_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[DalleTools()],
    description="You are an AI agent that can generate images using DALL-E.",
    markdown=True,
    show_tool_calls=True,
)

# Has to be a square image
image_path = Path("tmp/test_photo.png")

image_agent.print_response(
    f"Take the photo of me at file path {str(image_path)} and make it look like a ghibli character",
)

images = image_agent.get_images()
if images and isinstance(images, list):
    for image_response in images:
        image_url = image_response.url
        print(image_url)
