import fastapi

from app.api.routes.v1.router import router as v1_router


api_router = fastapi.APIRouter()
api_router.include_router(v1_router)
