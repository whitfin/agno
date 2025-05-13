"""Image understanding with a vLLM-served Vision model.

Prerequisites
-------------
1. Start a vision-capable model.  Phi-3.5-vision is fully open and works on CPU:

   ```bash
   vllm serve microsoft/Phi-3.5-vision-instruct \
     --task generate \
     --trust-remote-code \
     --dtype float32 \
     --enable-auto-tool-choice \
     --tool-call-parser pythonic \
     --limit-mm-per-prompt '{"image":2}'
   ```

2. Run this script.  It sends an image URL in OpenAI Vision format and streams
   back the answer.
"""

from agno.agent import Agent
from agno.media import Image
from agno.models.vllm import Vllm

vision_agent = Agent(
    model=Vllm(id="microsoft/Phi-3.5-vision-instruct"),
    markdown=True,
)

vision_agent.print_response(
    "Tell me about this image and give me a fun fact related to it.",
    images=[
        Image(url="https://upload.wikimedia.org/wikipedia/commons/0/0c/GoldenGateBridge-001.jpg")
    ],
    stream=True,
) 