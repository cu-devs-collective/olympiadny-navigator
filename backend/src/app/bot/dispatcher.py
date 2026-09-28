import maxapi

from app.bot.handlers.route import create_route_router
from app.core.config import Settings, get_settings
from app.db.connector import Database


def create_dispatcher(
    database: Database | None = None, settings: Settings | None = None
) -> maxapi.Dispatcher:
    dispatcher = maxapi.Dispatcher(router_id="root")
    dispatcher.include_routers(create_route_router(database, settings or get_settings()))
    return dispatcher
