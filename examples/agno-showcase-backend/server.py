"""AGno showcase backend server with multiple agents."""

from agno.agent import Agent
from agno.app.ag_ui import AGUIApp, AGUIAppSettings
from agno.models.openai import OpenAIChat
from agno.tools import Function
from fastapi import FastAPI
import uvicorn

# Create different agents for each demo
def create_agentic_generative_ui_agent():
    """Agent that can break down tasks into steps."""
    return Agent(
        name="AgenticGenerativeUIAgent",
        model=OpenAIChat(id="gpt-4"),
        instructions="""You are a helpful task planning assistant. When asked to help with a task:
        1. Break it down into clear, actionable steps
        2. Use the update_steps tool to create the step list
        3. Use start_step and complete_step to show progress
        4. Provide helpful guidance throughout the process""",
        tools=[
            Function(
                name="update_steps",
                description="Update the list of steps for the current task"
            ),
            Function(
                name="start_step", 
                description="Mark a step as in progress"
            ),
            Function(
                name="complete_step",
                description="Mark a step as completed"
            )
        ]
    )

def create_shared_state_agent():
    """Agent that manages a todo list."""
    return Agent(
        name="SharedStateAgent",
        model=OpenAIChat(id="gpt-4"),
        instructions="""You are a todo list manager. You can:
        - Add new todos
        - Toggle todo completion status
        - Delete todos
        - Change the filter view
        Be helpful and proactive in managing the user's tasks.""",
        tools=[
            Function(name="add_todo"),
            Function(name="toggle_todo"),
            Function(name="delete_todo"),
            Function(name="set_filter")
        ]
    )

def create_haiku_generator_agent():
    """Agent that generates haikus."""
    return Agent(
        name="HaikuGeneratorAgent",
        model=OpenAIChat(id="gpt-4"),
        instructions="""You are a creative haiku poet. When asked to write haikus:
        1. Follow the 5-7-5 syllable pattern strictly
        2. Match the requested theme and mood
        3. Create evocative, meaningful poetry
        4. Use the generate_haiku tool to display your creations""",
        tools=[
            Function(name="generate_haiku"),
            Function(name="clear_haikus"),
            Function(name="delete_haiku")
        ]
    )

def create_calculator_agent():
    """Agent that performs calculations with explanations."""
    return Agent(
        name="CalculatorAgent",
        model=OpenAIChat(id="gpt-4"),
        instructions="""You are a smart calculator that explains calculations step by step.
        When asked to calculate:
        1. Parse the mathematical expression
        2. Break down the calculation into clear steps
        3. Use the calculate tool to show the result with explanations
        4. Handle complex calculations like compound interest, tips, etc.""",
        tools=[
            Function(name="calculate"),
            Function(name="clear_calculations")
        ]
    )

def create_weather_agent():
    """Agent that provides weather information."""
    return Agent(
        name="WeatherAgent",
        model=OpenAIChat(id="gpt-4"),
        instructions="""You are a weather assistant. When asked about weather:
        1. Use the request_weather tool to show weather data
        2. Always provide realistic weather data
        3. Include temperature, conditions, humidity, and wind
        4. Remember that the user must confirm before the data is displayed""",
        tools=[
            Function(name="request_weather")
        ]
    )

def create_predictive_state_agent():
    """Agent that helps with form completion."""
    return Agent(
        name="PredictiveStateAgent",
        model=OpenAIChat(id="gpt-4"),
        instructions="""You are a smart form assistant that helps users complete forms.
        When asked to help:
        1. Analyze the existing form data
        2. Make intelligent predictions for empty fields
        3. Use predict_form_field to suggest values with confidence scores
        4. Provide helpful reasoning for your suggestions""",
        tools=[
            Function(name="predict_form_field"),
            Function(name="apply_prediction")
        ]
    )

# Create a registry of agents
AGENTS = {
    "agentiveGenerativeUIAgent": create_agentic_generative_ui_agent(),
    "sharedStateAgent": create_shared_state_agent(),
    "haikuGeneratorAgent": create_haiku_generator_agent(),
    "calculatorAgent": create_calculator_agent(),
    "weatherAgent": create_weather_agent(),
    "predictiveStateAgent": create_predictive_state_agent()
}

# Create the main FastAPI app
app = FastAPI()

# Configure AG-UI settings with CORS for the frontend
settings = AGUIAppSettings(
    cors_origins=["http://localhost:3000"],
    enable_cors=True
)

# Mount each agent's app at its own path
for agent_id, agent in AGENTS.items():
    # Create AG-UI app with proper settings
    agui_app = AGUIApp(
        agent=agent,
        settings=settings
    )
    # Get the FastAPI app and mount it
    agent_app = agui_app.get_app(prefix="/api/copilotkit")
    app.mount(f"/{agent_id}", agent_app)

@app.get("/")
async def root():
    """Root endpoint with information about available agents."""
    return {
        "message": "AGno Showcase Backend",
        "agents": list(AGENTS.keys()),
        "endpoints": {
            agent_id: f"/{agent_id}/api/copilotkit" 
            for agent_id in AGENTS.keys()
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7777) 