import base64
from os import getenv
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import PlainTextResponse

from agno.agent.agent import Agent
from agno.media import Audio, File, Image, Video
from agno.team.team import Team
import discord

intents = discord.Intents.all()
client = discord.Client(intents=intents)
try:
    DISCORD_TOKEN= getenv("DISCORD_BOT_TOKEN")
except Exception:
    raise ValueError("DISCORD_BOT_TOKEN NOT SET")

def DiscordClient(agent: Optional[Agent] = None, team: Optional[Team] = None):
    @client.event
    async def on_message(message):
        if message.author == client.user:
            print("author==client")
        else:
            if agent:
                response = await agent.arun(message.content, user_id=message.author.name)
            elif team:
                response = await team.arun(message.content, user_id=message.author.name)
            await message.channel.send(response.content)
    return client.run(DISCORD_TOKEN)
    