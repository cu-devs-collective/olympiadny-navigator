import pydantic


class Response[DataT](pydantic.BaseModel):
    data: DataT


class Error(pydantic.BaseModel):
    code: str
    message: str
    details: list[dict[str, object]] = pydantic.Field(default_factory=list)


class ErrorResponse(pydantic.BaseModel):
    error: Error
