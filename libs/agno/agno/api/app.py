from agno.api.api import api
from agno.api.routes import ApiRoutes
from agno.api.schemas.app import AppCreate
from agno.cli.settings import agno_cli_settings
from agno.utils.log import log_debug


def create_app(app: AppCreate) -> None:
    if not agno_cli_settings.api_enabled:
        return

    with api.AuthenticatedClient() as api_client:
        try:
            print("HERE")
            api_client.post(
                ApiRoutes.APP_CREATE,
                json={"app": app.model_dump()},
            )
            print("HERE2")
        except Exception as e:
            log_debug(f"Could not create App: {e}")


async def acreate_app(app: AppCreate) -> None:
    if not agno_cli_settings.api_enabled:
        return

    async with api.AuthenticatedAsyncClient() as api_client:
        try:
            print("HERE")
            payload = {"app": app.model_dump(exclude_none=True)}
            await api_client.post(
                ApiRoutes.APP_CREATE,
                json=payload,
            )
            print("HERE2")
        except Exception as e:
            log_debug(f"Could not create App: {e}")
