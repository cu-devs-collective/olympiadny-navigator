import collections.abc

import maxapi

from app.bot.handlers.repeater import create_repeater_router


type RouterFactory = collections.abc.Callable[[], maxapi.Router]

_ROUTER_FACTORIES: tuple[RouterFactory, ...] = (create_repeater_router,)


def create_handlers_router() -> maxapi.Router:
    router = maxapi.Router(router_id="handlers")
    router.include_routers(*(factory() for factory in _ROUTER_FACTORIES))
    return router


__all__ = ["create_handlers_router"]
