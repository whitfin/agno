"""
1. Run: `pip install openai ddgs newspaper4k lxml_html_clean agno` to install the dependencies
2. Run: `python cookbook/storage/singlestore_storage/singlestore_storage_for_team.py` to run the team
"""

import os
from os import getenv
from typing import List

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.storage.singlestore import SingleStoreStorage
from agno.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.hackernews import HackerNewsTools
from agno.utils.certs import download_cert
from pydantic import BaseModel
from sqlalchemy.engine import create_engine

# Configure SingleStore DB connection
USERNAME = getenv("SINGLESTORE_USERNAME")
PASSWORD = getenv("SINGLESTORE_PASSWORD")
HOST = getenv("SINGLESTORE_HOST")
PORT = getenv("SINGLESTORE_PORT")
DATABASE = getenv("SINGLESTORE_DATABASE")
SSL_CERT = getenv("SINGLESTORE_SSL_CERT", None)


# Download the certificate if SSL_CERT is not provided
if not SSL_CERT:
    SSL_CERT = download_cert(
        cert_url="https://portal.singlestore.com/static/ca/singlestore_bundle.pem",
        filename="singlestore_bundle.pem",
    )
    if SSL_CERT:
        os.environ["SINGLESTORE_SSL_CERT"] = SSL_CERT


# SingleStore DB URL
db_url = (
    f"mysql+pymysql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}?charset=utf8mb4"
)
if SSL_CERT:
    db_url += f"&ssl_ca={SSL_CERT}&ssl_verify_cert=true"

# Create a DB engine
db_engine = create_engine(db_url)


class Article(BaseModel):
    title: str
    summary: str
    reference_links: List[str]


hn_researcher = Agent(
    name="HackerNews Researcher",
    model=OpenAIChat("gpt-4o"),
    role="Gets top stories from hackernews.",
    tools=[HackerNewsTools()],
)

web_searcher = Agent(
    name="Web Searcher",
    model=OpenAIChat("gpt-4o"),
    role="Searches the web for information on a topic",
    tools=[DuckDuckGoTools()],
    add_datetime_to_instructions=True,
)


hn_team = Team(
    name="HackerNews Team",
    mode="coordinate",
    model=OpenAIChat("gpt-4o"),
    members=[hn_researcher, web_searcher],
    storage=SingleStoreStorage(
        table_name="team_sessions",
        db_engine=db_engine,
        schema=DATABASE,
        auto_upgrade_schema=True,
    ),
    instructions=[
        "First, search hackernews for what the user is asking about.",
        "Then, ask the web searcher to search for each story to get more information.",
        "Finally, provide a thoughtful and engaging summary.",
    ],
    response_model=Article,
    show_tool_calls=True,
    markdown=True,
    show_members_responses=True,
)

hn_team.print_response("Write an article about the top 2 stories on hackernews")
