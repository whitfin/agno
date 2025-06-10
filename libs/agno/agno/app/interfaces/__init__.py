from typing import Union
from agno.app.interfaces.playground.playground import Playground
from agno.app.interfaces.whatsapp.whatsapp import WhatsappAPI
from agno.app.interfaces.slack.slack import SlackAPI

Interface = Union[Playground, WhatsappAPI, SlackAPI]

__all__ = ["Interface", "Playground", "WhatsappAPI", "SlackAPI"]