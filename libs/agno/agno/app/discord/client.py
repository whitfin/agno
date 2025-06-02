from os import getenv
from typing import Optional
from agno.agent.agent import Agent
from agno.media import Audio, File, Image, Video
from agno.team.team import Team
from agno.utils.log import log_info
import requests
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
            log_info(f"sent {message.content}")
        else:
            message_image = None
            message_video = None
            message_audio = None
            media_url=None
            message_text=message.content
            if message.attachments:
                media=message.attachments[0]
                media_type=media.content_type
                media_url=media.url
                if (media_type.startswith("image/")):
                    message_image=media_url
                elif(media_type.startswith("video/")):
                    req = requests.get(media_url)
                    video=req.content
                    message_video=video                
                elif(media_type.startswith("audio/")):
                    message_audio=media_url                
            log_info(f"processing message:{message_text} \n with media: {media_url}")
            if agent:
                response = await agent.arun(message_text, user_id=message.author.name,
                    images=[Image(url=message_image)] if message_image else None,
                    videos=[Video(content=message_video)] if message_video else None,
                    audio=[Audio(url=message_audio)] if message_audio else None,)
            elif team:
                response = await team.arun(message_text, user_id=message.author.name,
                    images=[Image(url=message_image)] if message_image else None,
                    videos=[Video(url=message_video)] if message_video else None,
                    audio=[Audio(url=message_audio)] if message_audio else None,)
            await message.channel.send(response.content)
    return client.run(DISCORD_TOKEN)
    