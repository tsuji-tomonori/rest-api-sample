from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from mangum import Mangum
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from .database import RepairRequest, session
from .http import configure_http, problems
from .schemas import NewRepair, Repair, RepairId, RepairPage, Status, StatusChange

app = FastAPI(title="修理依頼 API", version="1.0.0")
configure_http(app)
DB = Annotated[Session, Depends(session)]
NOT_FOUND = "修理依頼が見つかりません。"


@app.post(
    "/repair-requests",
    status_code=201,
    response_model=Repair,
    responses={
        201: {"headers": {"Location": {"description": "登録した依頼のパス", "schema": {"type": "string"}}}},
        **problems(400, 415, 422),
    },
)
def create_repair(data: NewRepair, response: Response, db: DB):
    repair = RepairRequest(**data.model_dump(), status="open")
    db.add(repair)
    db.commit()
    response.headers["Location"] = f"/repair-requests/{repair.id}"
    return repair


@app.get("/repair-requests", response_model=RepairPage, responses=problems(422))
def list_repairs(
    db: DB,
    status: Status | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    after: RepairId | None = None,
):
    query = select(RepairRequest).order_by(RepairRequest.id)
    if status is not None:
        query = query.where(RepairRequest.status == status)
    if after is not None:
        query = query.where(RepairRequest.id > after)
    rows = db.scalars(query.limit(limit + 1)).all()
    return {"items": rows[:limit], "next_after": rows[limit - 1].id if len(rows) > limit else None}


@app.get("/repair-requests/{request_id}", response_model=Repair, responses=problems(404, 422))
def get_repair(request_id: RepairId, db: DB):
    repair = db.get(RepairRequest, request_id)
    if repair is None:
        raise HTTPException(404, NOT_FOUND)
    return repair


@app.patch("/repair-requests/{request_id}", response_model=Repair, responses=problems(400, 404, 415, 422))
def update_status(request_id: RepairId, data: StatusChange, db: DB):
    statement = update(RepairRequest).where(RepairRequest.id == request_id).values(status=data.status)
    repair = db.scalar(statement.returning(RepairRequest))
    if repair is None:
        raise HTTPException(404, NOT_FOUND)
    db.commit()
    return repair


@app.delete("/repair-requests/{request_id}", status_code=204, response_class=Response, responses=problems(404, 422))
def delete_repair(request_id: RepairId, db: DB):
    statement = delete(RepairRequest).where(RepairRequest.id == request_id)
    if db.scalar(statement.returning(RepairRequest.id)) is None:
        raise HTTPException(404, NOT_FOUND)
    db.commit()
    return Response(status_code=204)


handler = Mangum(app, lifespan="off")
