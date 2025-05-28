from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response

from agno.agent.agent import Agent
from agno.app.discord.security import verify_discord_signature
from agno.team.team import Team
from agno.tools.slack import SlackTools
from agno.utils.log import log_info


def get_async_router(agent: Optional[Agent] = None, team: Optional[Team] = None) -> APIRouter:
    router = APIRouter()

    @router.post("/discord/events")
    async def discord_events(request: Request, background_tasks: BackgroundTasks):
        signature = request.headers.get("X-Signature-Ed25519")
        timestamp = request.headers.get("X-Signature-Timestamp")
        body_bytes = await request.body()

        if not signature or not timestamp:
            raise HTTPException(status_code=401, detail="Missing Discord signature headers")

        if not verify_discord_signature(body_bytes, signature, timestamp):
            raise HTTPException(status_code=401, detail="Invalid request signature")

        payload = await request.json()
        event_type = payload.get("type")
        data = payload.get("d")
        log_info(f"Received Discord event: {event_type}")
        # Dispatch event processing based on event_type
        if event_type==0:
            return Response(status_code=204)
        elif event_type == "MESSAGE_CREATE":
            background_tasks.add_task(process_message_create, data)
        elif event_type == "INTERACTION_CREATE":
            background_tasks.add_task(process_interaction_create, data)
        else:
            # Handle unsupported or unimplemented events
            log_info(f"Event type {event_type} is not supported.")
            raise HTTPException(status_code=400, detail=f"Unsupported event type {event_type}")

        return {"status": "ok"}

    return router


async def process_message_create(data: dict):
    # Process a MESSAGE_CREATE event
    log_info("Processing MESSAGE_CREATE event...")
    # ... Add logic to handle the message creation ...


async def process_interaction_create(data: dict):
    # Process an INTERACTION_CREATE event
    log_info("Processing INTERACTION_CREATE event...")
    # ... Add logic to handle the interaction creation ...