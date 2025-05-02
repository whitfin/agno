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
            api_client.post(
                ApiRoutes.APP_CREATE,
                json={"app": app.model_dump()},
            )

        except Exception as e:
            log_debug(f"Could not create App: {e}")


async def acreate_app(app: AppCreate) -> None:
    if not agno_cli_settings.api_enabled:
        return

    async with api.AuthenticatedAsyncClient() as api_client:
        try:
            payload = {"app": app.model_dump(exclude_none=True)}
            await api_client.post(
                ApiRoutes.APP_CREATE,
                json=payload,
            )

        except Exception as e:
            log_debug(f"Could not create App: {e}")
