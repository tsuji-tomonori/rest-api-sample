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


# value は実際に送る JSON。x- で始まる項目は、契約テストで応答を確かめるための教材独自の印。
def request_example(summary: str, value: dict, status: int, expected_fields: dict | None = None) -> dict:
    example = {"summary": summary, "value": value, "x-expected-status": status}
    if expected_fields is not None:
        example["x-expected-fields"] = expected_fields
    return example


NEW_REPAIR_EXAMPLES = {
    "office-chair": request_example(
        "会議室の椅子を修理する",
        {"title": "椅子がぐらつく", "location": "第2会議室"}, 201,
        {"title": "椅子がぐらつく", "location": "第2会議室", "status": "open"},
    ),
    "trim-spaces": request_example(
        "件名と場所の前後に空白がある",
        {"title": "  照明が消える  ", "location": "  受付  "}, 201,
        {"title": "照明が消える", "location": "受付", "status": "open"},
    ),
}
NEW_REPAIR_NEGATIVE_EXAMPLES = {
    "blank-title": request_example("件名が空白だけ", {"title": "   ", "location": "受付"}, 422),
    "client-id": request_example(
        "登録時に受付番号を指定した", {"id": 42, "title": "椅子がぐらつく", "location": "第2会議室"}, 422,
    ),
}
STATUS_CHANGE_EXAMPLES = {
    "complete": request_example("依頼を完了する", {"status": "completed"}, 200, {"status": "completed"}),
    "reopen": request_example("依頼を再開する", {"status": "open"}, 200, {"status": "open"}),
}
STATUS_CHANGE_NEGATIVE_EXAMPLES = {
    "unknown-status": request_example("定義されていない状態を指定した", {"status": "done"}, 422),
    "missing-status": request_example("変更する状態を省略した", {}, 422),
}
