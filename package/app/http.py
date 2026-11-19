from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


NOT_FOUND = "修理依頼が見つかりません。"


class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str


class RepairAPI(FastAPI):
    def openapi(self) -> dict[str, Any]:
        if self.openapi_schema is not None:
            return self.openapi_schema
        # 標準の仕様書に、例外ハンドラーが返す共通の本文を加える。次回はこの仕様書を再利用する。
        document = super().openapi()
        components = document.setdefault("components", {})
        components.setdefault("schemas", {})["Problem"] = Problem.model_json_schema()
        return document


ERROR_DESCRIPTIONS = {
    400: "本文を JSON として読み取れません。",
    404: "指定した受付番号の依頼が見つかりません。",
    415: "本文の Content-Type に application/json を指定してください。",
    422: "入力値が条件に合いません。エラーの詳細で該当する項目を確認してください。",
}


def status_title(code: int) -> str:
    # 422 の見出しは RFC 9110 の表記に合わせる。Python 3.12 では旧称の Unprocessable Entity が返る。
    return "Unprocessable Content" if code == 422 else HTTPStatus(code).phrase


def problems(*codes: int) -> dict:
    # 各ルートの responses に渡す定義。利用者が OpenAPI を読むと、起こりうるエラーと本文の形が分かる。
    responses: dict[int, dict[str, Any]] = {
        code: {
            "description": ERROR_DESCRIPTIONS[code],
            "content": {"application/problem+json": {"schema": {"$ref": "#/components/schemas/Problem"}}},
        }
        for code in codes
    }
    if 404 in responses:
        missing = Problem(title=status_title(404), status=404, detail=NOT_FOUND)
        responses[404]["content"]["application/problem+json"]["examples"] = {
            "not-found": {"summary": "指定した依頼がない", "value": missing.model_dump()},
        }
    return responses


def problem(code: int, detail: str, headers=None) -> JSONResponse:
    # エラーが起きたときは、OpenAPI と共通の Problem モデルから実際の応答を作る。
    body = Problem(title=status_title(code), status=code, detail=detail)
    return JSONResponse(
        body.model_dump(), status_code=code, headers=headers, media_type="application/problem+json"
    )


class JsonBodyRoute(APIRoute):
    def get_route_handler(self):
        handle = super().get_route_handler()

        async def checked(request: Request):
            # 本文を受け取るルートでは、FastAPI が内容を読む前に Content-Type を確かめる。
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
        # JSON を読めないときは 400、読み取った値が入力条件に合わないときは 422 を返す。
        if any(error["type"] == "json_invalid" for error in errors):
            return problem(400, "本文を JSON として読み取れません。")
        fields = ", ".join(".".join(map(str, error["loc"])) for error in errors)
        return problem(422, f"入力の形式や範囲を確認してください（{fields}）。")
