"""Minimal example for AgentOS."""

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.models.openai import OpenAIChat
from agno.os import AgentOS
from pydantic import BaseModel, Field
from typing import List


class InvoiceItem(BaseModel):
    item_number: int = Field(..., description="The item number No")
    item_code: str = Field(..., description="The Item Code")
    item_description: str = Field(..., description="The item description")
    item_country_of_origin: str = Field(..., description="The item country of origin")
    item_quantity: int = Field(..., description="The item quantity")
    item_unit_of_measure: str = Field(..., description="The item unit of measure UOM")
   

class Invoice(BaseModel):
    header_invoice_number: str = Field(..., description="The invoice number is a 12 digit number with INV# close to it")
    header_invoice_date: str = Field(..., description="The invoice date is a date in the format of MM/DD/YYYY")
    header_invoice_delivery_from: str = Field(..., description="The invoice Delivery From address")
    items: List[InvoiceItem] = Field(..., description="The invoice items")

    
# Setup the database
db = PostgresDb(db_url="postgresql+psycopg://ai:ai@localhost:5532/ai")

# Setup basic agents, teams and workflows
basic_agent = Agent(
    name="Invoice analyst Agent",
    db=db,
    enable_session_summaries=True,
    enable_user_memories=True,
    add_history_to_context=True,
    num_history_runs=3,
    add_datetime_to_context=True,
    markdown=True,
    instructions=[
        "You are an invoice analyst. You are given an invoice and you need to analyze it and provide a summary of the invoice.",
        "When you can not find the information requested, you should cleary state that you can not find the information.",
    ],
    output_schema=Invoice,
    debug_mode=True,
)

# Setup our AgentOS app
agent_os = AgentOS(
    description="Demo app for klearnow",
    os_id="klearnow-app",
    agents=[basic_agent],
)
app = agent_os.get_app()


if __name__ == "__main__":
    """Run our AgentOS.

    You can see the configuration and available apps at:
    http://localhost:7777/config

    """
    agent_os.serve(app="klearnow:app", reload=True)
