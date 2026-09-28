import fastapi

from app.api.routes.v1.healthz import router as healthz_router
from app.api.routes.v1.route import router as route_router


router = fastapi.APIRouter(prefix="/v1")
router.include_router(healthz_router)  # Healthcheck route, do not remove!
router.include_router(route_router)
