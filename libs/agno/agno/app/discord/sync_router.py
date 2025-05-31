from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from agno.agent.agent import Agent
from agno.app.slack.security import verify_slack_signature
from agno.team.team import Team
from agno.tools.slack import SlackTools
from agno.utils.log import log_info


def get_sync_router(agent: Optional[Agent] = None, team: Optional[Team] = None) -> APIRouter:
    router = APIRouter()

    @router.post("/discord/events")
    def discord_events(request: Request, background_tasks: BackgroundTasks):
        payload = request.json()
        event_type = payload.get("t")
        data = payload.get("d")

        log_info(f"Received Discord event: {event_type}")
        
        if not event_type or not data:
            raise HTTPException(status_code=400, detail="Invalid payload format")

        # Dispatch event processing based on event_type
        if event_type == "MESSAGE_CREATE":
            background_tasks.add_task(process_message_create, data)
        elif event_type == "INTERACTION_CREATE":
            background_tasks.add_task(process_interaction_create, data)
        else:
            # Handle unsupported or unimplemented events
            log_info(f"Event type {event_type} is not supported.")
            raise HTTPException(status_code=400, detail=f"Unsupported event type {event_type}")

        return {"status": "ok"}

    return router


def process_message_create(data: dict):
    # Process a MESSAGE_CREATE event
    log_info("Processing MESSAGE_CREATE event...")
    # ... Add logic to handle the message creation ...

def process_interaction_create(data: dict):
    # Process an INTERACTION_CREATE event
    log_info("Processing INTERACTION_CREATE event...")
    # ... Add logic to handle the interaction creation ...