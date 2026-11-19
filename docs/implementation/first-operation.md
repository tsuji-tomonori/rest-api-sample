# 一つの変更を通して作る　場所で修理依頼を探す

総務が第2会議室の修理依頼だけを見たいとします。公開中の一覧には、状態・件数・続きの番号を指定できます。ここでは手元の作業コピーに、場所で絞る任意の条件 `location` を一つ加えます。既存の `GET /repair-requests` を拡張するので、新しいパスや DB の列を作る必要はありません。

## 1. 変更後の約束を一行で決める

**場所を指定したら、前後の空白を除いた場所名と完全に一致する依頼を受付番号順に返す。省略したら従来どおり。** 一致する依頼がない場合は `200` と空の一覧です。空白だけの指定は入力の誤りとして `422` にします。[入力の設計](../textbook/03-inputs.md)・[設計シート B3](../templates/contract-sheet.md#b3)

## 2. FastAPI に検索条件を渡す

[ルート定義](../../package/app/main.py)の `from .schemas import (...)` に `ShortText` を追加します。これは登録時の場所に使っている型で、前後の空白を除き、1〜100文字に制限します。[入力モデル](../../package/app/schemas.py)

同じファイルの `list_repairs` の引数に、`after` の次の行として次を加えます。

```python
    location: Annotated[ShortText | None, Query(description="場所名の完全一致")] = None,
```

`= None` が条件を省略できることを表します。今度は関数内で、既存の `if after is not None:` の**直前**に次の2行を足します。

```python
    if location is not None:
        query = query.where(RepairRequest.location == location)
```

状態と場所の両方が指定されたら、両方を満たす行だけを選びます。DB が絞り込んでから `limit + 1` 件を読むので、別の場所の依頼が途中にあっても、そのページに載せる件数と次のページの番号が合います。

## 3. 以前の呼び方と新しい呼び方を試す

[API テスト](../../tests/test_api.py)の末尾に次の関数を追加します。このファイルの `client` はテストのたびに空の SQLite を用意します。A、B、A の順に登録すると、場所を絞る前に件数を区切ってしまう誤りにも気付けます。

```python
def test_location_filter(client):
    repairs = []
    for room in ("A", "B", "A"):
        response = client.post(COLLECTION, json={"title": "椅子の修理", "location": room})
        assert response.status_code == 201
        repairs.append(response.json())

    assert client.get(COLLECTION).json()["items"] == repairs
    first = client.get(COLLECTION, params={"location": " A ", "limit": 1})
    assert first.status_code == 200
    assert first.json() == {"items": [repairs[0]], "next_after": repairs[0]["id"]}

    second = client.get(COLLECTION, params={"location": "A", "after": first.json()["next_after"], "limit": 1})
    assert second.json() == {"items": [repairs[2]], "next_after": None}
    assert client.get(COLLECTION, params={"location": "C"}).json() == {"items": [], "next_after": None}
    assert client.get(COLLECTION, params={"location": " "}).status_code == 422
```

リポジトリのルートで実行します。API サーバーを別途起動する必要はありません。

```console
uv run --locked python -m pytest -q tests/test_api.py::test_location_filter
```

## 4. 公開する YAML に反映する

FastAPI の宣言から仕様書を作り直し、差分と既存テストを確認します。

```console
uv run --locked python -m package.app.export_openapi docs/openapi.yaml
git diff -- docs/openapi.yaml
uv run --locked python -m pytest -q tests/test_api.py
```

差分では `listRepairs` の `parameters` に `name: location`、`in: query`、`required: false` が追加されます。画面から試す場合は、[第1章の手順](01-http.md)で変更後のアプリを起動します。すでに起動中なら、その端末で Ctrl+C を押してから起動し直します。ブラウザーで `http://127.0.0.1:8000/docs` を開くと、一覧取得に `location` 欄が現れます。場所 A と B にそれぞれ依頼を登録し、A を指定すると、テストと同じ絞り込みを確かめられます。

[FastAPI のクエリ検証](https://fastapi.tiangolo.com/tutorial/query-params-str-validations/)・[SQLAlchemy の検索条件](https://docs.sqlalchemy.org/en/20/tutorial/data_select.html#the-where-clause)

[実装編の入口](README.md) ｜ [実装編 08　この変更を公開するには](08-compatibility.md)
