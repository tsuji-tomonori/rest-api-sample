from typing import Annotated

from fastapi import Body, Depends, HTTPException, Query, Response
from mangum import Mangum
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from .database import RepairRequest, session
from .http import NOT_FOUND, RepairAPI, configure_http, problems
from .schemas import (
    NEW_REPAIR_EXAMPLES, NEW_REPAIR_NEGATIVE_EXAMPLES,
    STATUS_CHANGE_EXAMPLES, STATUS_CHANGE_NEGATIVE_EXAMPLES,
    NewRepair, Repair, RepairId, RepairPage, Status, StatusChange,
)

app = RepairAPI(title="修理依頼 API", version="1.0.0")
configure_http(app)
# 引数を db: DB と書いた関数には、FastAPI が session() から受け取ったセッションを渡す。
DB = Annotated[Session, Depends(session)]


# POST /repair-requests をこの関数に結び付ける。FastAPI は本文を NewRepair で検証し、結果を Repair の形で返す。
@app.post(
    "/repair-requests",
    operation_id="createRepair",
    summary="修理依頼を登録する",
    status_code=201,
    response_model=Repair,
    response_description="修理依頼を登録しました。本文に登録内容、Location に取得先のパスを返します。",
    openapi_extra={"x-negative-examples": NEW_REPAIR_NEGATIVE_EXAMPLES},
    responses={
        201: {"headers": {"Location": {
            "description": "登録した依頼のパス",
            "schema": {"type": "string", "format": "uri-reference"},
            "example": "/repair-requests/42",
        }}},
        **problems(400, 415, 422),
    },
)
def create_repair(data: Annotated[NewRepair, Body(openapi_examples=NEW_REPAIR_EXAMPLES)], response: Response, db: DB):
    repair = RepairRequest(**data.model_dump(), status="open")
    db.add(repair)
    # 登録が確定したら、採番された ID から取得先のパスを作る。
    db.commit()
    response.headers["Location"] = f"/repair-requests/{repair.id}"
    return repair


@app.get(
    "/repair-requests",
    operation_id="listRepairs",
    summary="修理依頼の一覧を取得する",
    response_model=RepairPage,
    response_description="条件に合う依頼を受付番号順に返します。",
    responses=problems(422),
)
def list_repairs(
    db: DB,
    status: Annotated[Status | None, Query(openapi_examples={"first-page": {"value": "open"}})] = None,
    limit: Annotated[int, Query(ge=1, le=100, openapi_examples={"first-page": {"value": 1}})] = 20,
    after: RepairId | None = None,
):
    query = select(RepairRequest).order_by(RepairRequest.id)
    if status is not None:
        query = query.where(RepairRequest.status == status)
    if after is not None:
        query = query.where(RepairRequest.id > after)
    # 1件多く読み、続きがあるかを調べる。次のページの起点は、今回返す最後の依頼の ID。
    rows = db.scalars(query.limit(limit + 1)).all()
    return {"items": rows[:limit], "next_after": rows[limit - 1].id if len(rows) > limit else None}


@app.get(
    "/repair-requests/{request_id}",
    operation_id="getRepair",
    summary="修理依頼を1件取得する",
    response_model=Repair,
    response_description="指定した受付番号の依頼を返します。",
    responses=problems(404, 422),
)
def get_repair(request_id: RepairId, db: DB):
    repair = db.get(RepairRequest, request_id)
    if repair is None:
        raise HTTPException(404, NOT_FOUND)
    return repair


@app.patch(
    "/repair-requests/{request_id}",
    operation_id="updateRepairStatus",
    summary="修理依頼の状態を変更する",
    response_model=Repair,
    response_description="状態を変更し、変更後の依頼を返します。",
    responses=problems(400, 404, 415, 422),
    openapi_extra={"x-negative-examples": STATUS_CHANGE_NEGATIVE_EXAMPLES},
)
def update_status(
    request_id: RepairId, data: Annotated[StatusChange, Body(openapi_examples=STATUS_CHANGE_EXAMPLES)], db: DB,
):
    statement = update(RepairRequest).where(RepairRequest.id == request_id).values(status=data.status)
    # RETURNING は同じ更新命令で変更後の行を返す。対象があれば変更を確定してから応答する。
    repair = db.scalar(statement.returning(RepairRequest))
    if repair is None:
        raise HTTPException(404, NOT_FOUND)
    db.commit()
    return repair


@app.delete(
    "/repair-requests/{request_id}",
    operation_id="deleteRepair",
    summary="修理依頼を削除する",
    status_code=204,
    response_class=Response,
    response_description="依頼を削除しました。応答本文はありません。",
    responses=problems(404, 422),
)
def delete_repair(request_id: RepairId, db: DB):
    statement = delete(RepairRequest).where(RepairRequest.id == request_id)
    if db.scalar(statement.returning(RepairRequest.id)) is None:
        raise HTTPException(404, NOT_FOUND)
    db.commit()
    return Response(status_code=204)


# Lambda の入口。Mangum が API Gateway のイベントを FastAPI に渡し、応答を Gateway 用の形式に戻す。
handler = Mangum(app, lifespan="off")
