import logging
from collections.abc import Callable
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

PROBLEM_MEDIA_TYPE = "application/problem+json"
VALIDATION_PROBLEM_TYPE = "urn:job-analyzer:problem:validation-error"


class ProblemValidationError(BaseModel):
    detail: str
    pointer: str


class ProblemDetails(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str = "about:blank"
    title: str
    status: int = Field(ge=100, le=599)
    detail: str
    instance: str
    code: str | None = None
    errors: list[ProblemValidationError] | None = None


def _title_for_status(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "HTTP Error"


def _problem_response(
    request: Request,
    *,
    status_code: int,
    detail: str,
    problem_type: str = "about:blank",
    title: str | None = None,
    headers: dict[str, str] | None = None,
    extensions: dict[str, Any] | None = None,
) -> JSONResponse:
    content: dict[str, Any] = {
        "type": problem_type,
        "title": title or _title_for_status(status_code),
        "status": status_code,
        "detail": detail,
        "instance": request.url.path,
    }
    if extensions:
        content.update(extensions)
    return JSONResponse(
        status_code=status_code,
        content=content,
        headers=headers,
        media_type=PROBLEM_MEDIA_TYPE,
    )


async def http_exception_handler(
    request: Request,
    exception: StarletteHTTPException,
) -> JSONResponse:
    extensions: dict[str, Any] = {}
    if isinstance(exception.detail, dict):
        detail = str(exception.detail.get("message") or _title_for_status(exception.status_code))
        extensions = {
            key: value for key, value in exception.detail.items() if key != "message"
        }
    else:
        detail = str(exception.detail)
    return _problem_response(
        request,
        status_code=exception.status_code,
        detail=detail,
        headers=exception.headers,
        extensions=extensions,
    )


def _json_pointer(location: tuple[Any, ...]) -> str:
    escaped = [str(part).replace("~", "~0").replace("/", "~1") for part in location]
    return "#/" + "/".join(escaped)


async def request_validation_exception_handler(
    request: Request,
    exception: RequestValidationError,
) -> JSONResponse:
    errors = [
        {
            "detail": error["msg"],
            "pointer": _json_pointer(error["loc"]),
        }
        for error in exception.errors()
    ]
    return _problem_response(
        request,
        status_code=422,
        problem_type=VALIDATION_PROBLEM_TYPE,
        title="Validation Error",
        detail="Request validation failed",
        extensions={"errors": errors},
    )


async def unhandled_exception_handler(request: Request, exception: Exception) -> JSONResponse:
    logger.exception("Unhandled API exception", exc_info=exception)
    return _problem_response(
        request,
        status_code=500,
        detail="An unexpected error occurred",
    )


def install_problem_handlers(application: FastAPI) -> None:
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    application.add_exception_handler(Exception, unhandled_exception_handler)


def install_problem_openapi(application: FastAPI) -> None:
    default_openapi: Callable[[], dict[str, Any]] = application.openapi

    def problem_openapi() -> dict[str, Any]:
        schema = default_openapi()
        for path_item in schema.get("paths", {}).values():
            for operation in path_item.values():
                if not isinstance(operation, dict):
                    continue
                for status_code in ("422", "500"):
                    response = operation.get("responses", {}).get(status_code)
                    if response is not None:
                        response["content"] = {
                            PROBLEM_MEDIA_TYPE: {
                                "schema": {"$ref": "#/components/schemas/ProblemDetails"}
                            }
                        }
        return schema

    application.openapi = problem_openapi


STANDARD_PROBLEM_RESPONSES = {
    422: {
        "model": ProblemDetails,
        "description": "Request validation failed",
        "content": {PROBLEM_MEDIA_TYPE: {}},
    },
    500: {
        "model": ProblemDetails,
        "description": "Unexpected server error",
        "content": {PROBLEM_MEDIA_TYPE: {}},
    },
}
