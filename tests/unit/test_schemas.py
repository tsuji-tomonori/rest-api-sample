"""入力モデルを直接呼び出し、値の整形と境界値を確かめる。"""

import pytest
from pydantic import ValidationError

from package.app.schemas import NewRepair, StatusChange


@pytest.mark.parametrize("length", [1, 100])
def test_new_repair_counts_characters_after_trimming(length):
    title = "椅" * length
    repair = NewRepair(title=f" {title} ", location=" 第2会議室 ")
    assert repair.model_dump() == {"title": title, "location": "第2会議室"}


@pytest.mark.parametrize("title", ["  ", "椅" * 101])
def test_new_repair_rejects_lengths_outside_the_range(title):
    with pytest.raises(ValidationError) as error:
        NewRepair(title=title, location="第2会議室")
    assert error.value.errors()[0]["loc"] == ("title",)


@pytest.mark.parametrize("extra", [{"id": 42}, {"status": "completed"}])
def test_client_cannot_set_server_fields_on_creation(extra):
    with pytest.raises(ValidationError) as error:
        NewRepair.model_validate({"title": "椅子がぐらつく", "location": "第2会議室", **extra})
    assert error.value.errors()[0]["type"] == "extra_forbidden"


def test_status_change_rejects_an_attempt_to_rename_the_repair():
    with pytest.raises(ValidationError) as error:
        StatusChange.model_validate({"status": "completed", "title": "別の依頼"})
    assert error.value.errors()[0]["loc"] == ("title",)
