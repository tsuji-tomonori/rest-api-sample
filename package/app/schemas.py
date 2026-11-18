from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


Status = Literal["open", "completed"]
ShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100, pattern=r"^[^\x00]+$"),
]
RepairId = Annotated[int, Field(ge=1, le=2_147_483_647)]


class NewRepair(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: ShortText
    location: ShortText


class StatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Status


class Repair(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: RepairId
    title: str
    location: str
    status: Status


class RepairPage(BaseModel):
    items: list[Repair]
    next_after: RepairId | None
