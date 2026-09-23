import fastapi

from app.api.routes.v1.example_http import router as example_http_router
from app.api.routes.v1.healthz import router as healthz_router


router = fastapi.APIRouter(prefix="/v1")
router.include_router(healthz_router)  # Healthcheck route, do not remove!
# TODO: remove the example router below and add application-specific routes.
router.include_router(example_http_router)
