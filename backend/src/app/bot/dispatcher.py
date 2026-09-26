import maxapi

from app.bot.handlers import create_handlers_router


def create_dispatcher() -> maxapi.Dispatcher:
    dispatcher = maxapi.Dispatcher(router_id="root")
    dispatcher.include_routers(create_handlers_router())
    return dispatcher
