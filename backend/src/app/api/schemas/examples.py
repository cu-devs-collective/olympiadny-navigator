import datetime

import pydantic

from app.api.responses import Response


class PostgresExample(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime.datetime


class S3Example(pydantic.BaseModel):
    key: str
    size_bytes: int


class ExternalTodo(pydantic.BaseModel):
    id: int
    title: str
    completed: bool


class HttpExample(pydantic.BaseModel):
    upstream_id: int
    title: str
    completed: bool


class PostgresExamplesResponse(Response[list[PostgresExample]]):
    pass


class S3UploadResponse(Response[S3Example]):
    pass


class HttpExampleResponse(Response[HttpExample]):
    pass
