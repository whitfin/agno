"""AgentOS Demo"""

from agents.agno_agent import agno_agent
from agents.finance_agent import finance_agent
from agents.research_agent import research_agent
from agno.os import AgentOS
from agno.os.interfaces.whatsapp import Whatsapp
from teams.multi_language_team import multi_language_team
from workflows.article_creation import article_workflow

# ************* AgentOS *************
agent_os = AgentOS(
    os_id="agentos-demo",
    agents=[agno_agent, finance_agent, research_agent],
    teams=[multi_language_team],
    workflows=[article_workflow],
    interfaces=[Whatsapp(agent=agno_agent)],
)
app = agent_os.get_app()
# *******************************

if __name__ == "__main__":
    agent_os.serve(app="agent_os:app", reload=True)
