from typing import List

from agno.agent import Agent
from agno.models.vllm import Vllm
from pydantic import BaseModel, Field

class MovieScript(BaseModel):
    setting: str = Field(
        ..., description="Provide a nice setting for a blockbuster movie."
    )
    ending: str = Field(
        ...,
        description="Ending of the movie. If not available, provide a happy ending.",
    )
    genre: str = Field(
        ...,
        description="Genre of the movie. If not available, select action, thriller or romantic comedy.",
    )
    name: str = Field(..., description="Give a name to this movie")
    characters: List[str] = Field(..., description="Name of characters for this movie.")
    storyline: str = Field(
        ..., description="3 sentence storyline for the movie. Make it exciting!"
    )


# Agent that uses JSON mode (model instructed to emit JSON explicitly)
json_mode_agent = Agent(
    model=Vllm(id="microsoft/Phi-3-mini-4k-instruct"),
    description="You write movie scripts.",
    response_model=MovieScript,
    use_json_mode=True,
)

# Agent that lets Agno parse the assistant's answer as a Pydantic model
structured_output_agent = Agent(
    model=Vllm(id="microsoft/Phi-3-mini-4k-instruct"),
    description="You write movie scripts.",
    response_model=MovieScript,
)

json_mode_agent.print_response("New York")
structured_output_agent.print_response("New York") 

