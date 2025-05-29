from __future__ import annotations

from agno.agent import Agent
from agno.tools.function import Function
from agno.models.openai import OpenAIChat
import random

# Mock weather data for demonstration
WEATHER_DATA = {
    "new york": {"temp": 72, "condition": "Partly Cloudy", "humidity": 65},
    "london": {"temp": 59, "condition": "Rainy", "humidity": 80},
    "tokyo": {"temp": 68, "condition": "Clear", "humidity": 55},
    "paris": {"temp": 64, "condition": "Cloudy", "humidity": 70},
    "sydney": {"temp": 77, "condition": "Sunny", "humidity": 45},
    "mumbai": {"temp": 86, "condition": "Humid", "humidity": 85},
    "toronto": {"temp": 55, "condition": "Windy", "humidity": 60},
    "dubai": {"temp": 95, "condition": "Hot and Sunny", "humidity": 40},
}

def get_weather_data(city: str) -> str:
    """Get weather data for a city (mock implementation)."""
    city_lower = city.lower()
    
    # Check if we have data for this city
    if city_lower in WEATHER_DATA:
        data = WEATHER_DATA[city_lower]
    else:
        # Generate random data for unknown cities
        data = {
            "temp": random.randint(50, 90),
            "condition": random.choice(["Sunny", "Cloudy", "Partly Cloudy", "Rainy"]),
            "humidity": random.randint(30, 90)
        }
    
    return f"""Weather in {city.title()}:
🌡️ Temperature: {data['temp']}°F ({round((data['temp'] - 32) * 5/9)}°C)
☁️ Condition: {data['condition']}
💧 Humidity: {data['humidity']}%"""

# Weather tool
get_weather_tool = Function(
    name="get_weather",
    description="Get current weather information for a city",
    parameters={
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "Name of the city to get weather for"
            }
        },
        "required": ["city"]
    },
    entrypoint=get_weather_data
)

# Create weather agent
WeatherAgent = Agent(
    name="WeatherAgent",
    model=OpenAIChat(id="gpt-4o-mini"),
    description="A weather assistant that provides current weather information",
    instructions="""You are a friendly weather assistant. You can provide current weather information for any city using the get_weather tool.

When users ask about weather:
1. Use the get_weather tool with the city name
2. Present the information clearly
3. Add helpful context (e.g., whether it's good weather for outdoor activities)
4. You can suggest what to wear or bring based on the conditions

Be conversational and helpful. If users ask about multiple cities, get the weather for each one.""",
    tools=[get_weather_tool],
    markdown=True,
    stream=True,
) 