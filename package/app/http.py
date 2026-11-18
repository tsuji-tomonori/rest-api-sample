from http import HTTPStatus

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str


def status_title(code: int) -> str:
    # Python 3.12 uses the older name "Unprocessable Entity" for 422.
    return "Unprocessable Content" if code == 422 else HTTPStatus(code).phrase


def problems(*codes: int) -> dict:
    return {
        code: {
            "description": status_title(code),
            "content": {"application/problem+json": {"schema": Problem.model_json_schema()}},
        }
        for code in codes
    }


def problem(code: int, detail: str, headers=None) -> JSONResponse:
    body = Problem(title=status_title(code), status=code, detail=detail)
    return JSONResponse(
        body.model_dump(), status_code=code, headers=headers, media_type="application/problem+json"
    )


class JsonBodyRoute(APIRoute):
    def get_route_handler(self):
        handle = super().get_route_handler()

        async def checked(request: Request):
            media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            if self.body_field and media_type != "application/json":
                raise HTTPException(415, "本文は application/json で送ってください。")
            return await handle(request)

        return checked


def configure_http(app: FastAPI) -> None:
    app.router.route_class = JsonBodyRoute

    @app.middleware("http")
    async def no_store(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        return problem(exc.status_code, str(exc.detail), exc.headers)

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        if any(error["type"] == "json_invalid" for error in errors):
            return problem(400, "本文を JSON として読み取れません。")
        fields = ", ".join(".".join(map(str, error["loc"])) for error in errors)
        return problem(422, f"入力の形式や範囲を確認してください（{fields}）。")
