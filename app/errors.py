from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message


def _body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def install_handlers(app: FastAPI) -> None:
    from legalshield_ai.llm import LlmUnavailable

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status, content=_body(exc.code, exc.message))

    @app.exception_handler(LlmUnavailable)
    async def _llm_unavailable(_: Request, exc: LlmUnavailable):
        return JSONResponse(
            status_code=503,
            content=_body("LLM_UNAVAILABLE", "The legal assistant is temporarily unavailable. Please try again."),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        parts = []
        for e in exc.errors():
            loc = ".".join(str(x) for x in e.get("loc", [])[1:]) or "body"
            parts.append(f"{loc}: {e.get('msg')}")
        return JSONResponse(status_code=422, content=_body("VALIDATION_ERROR", "; ".join(parts)))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(status_code=exc.status_code, content=_body(code, str(exc.detail)))
