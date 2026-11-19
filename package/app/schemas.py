from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


Status = Literal["open", "completed"]
ShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100, pattern=r"^[^\x00]+$"),
]
RepairId = Annotated[int, Field(ge=1, le=2_147_483_647)]


# 登録時に利用者が決めるのは件名と場所。余分な項目をエラーにすれば、入力欄の書き間違いも伝わる。
class NewRepair(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: ShortText
    location: ShortText


# 更新時に受け取るのは状態だけなので、登録とは別の入力モデルを使う。
class StatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Status


# 応答にはサーバーが決めた ID も載せる。from_attributes で保存した行の属性から値を読み取る。
class Repair(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: RepairId
    title: str
    location: str
    status: Status


class RepairPage(BaseModel):
    items: list[Repair]
    next_after: RepairId | None
