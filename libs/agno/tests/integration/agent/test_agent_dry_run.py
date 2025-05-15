import pytest

from agno.agent.agent import Agent

# A minimal stub model to satisfy Agent.get_system_message and avoid API calls
class DummyModel:
    id = "dummy"
    assistant_message_role = "assistant"
    supports_native_structured_outputs = False
    supports_json_schema_outputs = False

    def get_instructions_for_model(self, tools):
        return []

    def get_system_message_for_model(self, tools):
        return None

    def response(self, *args, **kwargs):
        pytest.skip("Model.response should not be called during dry run")

    async def aresponse(self, *args, **kwargs):
        pytest.skip("Model.aresponse should not be called during dry run")


def test_print_response_dry_run_sync(capsys):
    agent = Agent(model=DummyModel())
    # Synchronous dry run
    agent.print_response("hello world", dry_run=True)
    out = capsys.readouterr().out
    assert "==== Dry Run ====" in out
    assert "System Message:" in out
    assert "None" in out
    assert "User Message:" in out
    assert "hello world" in out
    assert "Metrics:" in out
    assert "SessionMetrics" in out


@pytest.mark.asyncio
async def test_print_response_dry_run_async(capsys):
    agent = Agent(model=DummyModel())
    # Asynchronous dry run
    await agent.aprint_response("async hello", dry_run=True)
    out = capsys.readouterr().out
    assert "==== Dry Run (async) ====" in out
    assert "System Message:" in out
    assert "None" in out
    assert "User Message:" in out
    assert "async hello" in out
    assert "Metrics:" in out
    assert "SessionMetrics" in out
