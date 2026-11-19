# 実装編 03　パス・クエリ・本文を FastAPI で受け取る

設計シートの B3 に書いた「どこから受け取るか」はルート関数の引数に、B4 の「どんな値なら受け付けるか」は引数の型に写します。一覧の件数を指定する入力と、新しい修理依頼を登録する入力を見比べます。

## 入力の置き場所をコードに写す

| 呼び出し元が送るもの | サンプルで読む場所 |
| --- | --- |
| パスの受付番号 | `/repair-requests/{request_id}` の波かっこと、関数の引数 `request_id: RepairId` を同じ名前にする |
| 一覧のクエリ | `list_repairs` の引数 `status`・`limit`・`after` で受ける。`limit` の条件と既定値は下の1行で指定する |
| 登録の JSON 本文 | `create_repair` の引数 `data` に `NewRepair` と `Body(...)` を指定する。関数の中では件名を `data.title` で読める |
| 本文の形式を伝えるヘッダー | 本文を取るルートでは共通処理 `JsonBodyRoute` が `request.headers.get("content-type", "")` を読む。登録・更新には `application/json` を指定する |

たとえば呼び出し元のシステム名を伝えるヘッダーを追加するなら、`from fastapi import Header` としてルート関数の引数に `source_system: Annotated[str, Header()]` を書くと、`Source-System` ヘッダーを必須の文字列として受け取れます。[FastAPI 公式　ヘッダーの引数](https://fastapi.tiangolo.com/tutorial/header-params/)

次は `list_repairs` の引数から抜き出した1行です。

```python
limit: Annotated[int, Query(ge=1, le=100, openapi_examples={"first-page": {"value": 1}})] = 20,
```

`int` は整数、`ge=1` と `le=100` は両端を含む範囲です。何も指定しないと右端の既定値 `20` が使われます。`openapi_examples` にある `1` は仕様書に載せる入力例です。利用者が `?limit=1` を送ると、一覧に含まれる依頼は最大1件になります。[ルートの引数](../../package/app/main.py)・[ヘッダーの共通処理](../../package/app/http.py)

## 登録できる JSON を型にする

登録する情報は件名と場所です。次は入力モデルの本体です。Pydantic の `BaseModel` を継承すると、FastAPI が受信した JSON をこの型に照らして検証します。

```python
class NewRepair(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: ShortText
    location: ShortText
```

`ShortText` は前後の空白を除いて1〜100文字とする共通の型です。どちらの項目も既定値を持たないため必須です。`extra="forbid"` を付けたので、本文にサーバーが採番する `id` を混ぜると、保存処理に進む前に入力エラーになります。[入力モデルと文字列の条件](../../package/app/schemas.py)

## 入力を一つ変えて確かめる

[実装編 01](01-http.md)で API を起動し、別の端末で順に送ります。Windows PowerShell では先頭を `curl.exe` に替えます。

```console
curl -i "http://127.0.0.1:8000/repair-requests?limit=1"
curl -i "http://127.0.0.1:8000/repair-requests?limit=0"
```

1回目は `200` と一覧が返ります。台帳が空でも正常です。2回目は `422` と、`detail` に `query.limit` を含むエラーが返ります。登録本文については次のテストが使えます。テスト専用の台帳で不正な入力を送り、依頼が増えていないことまで確認します。[テストの入力と期待結果](../../tests/test_api.py)

```console
uv run --locked python -m pytest -q tests/test_api.py::test_invalid_create_does_not_insert
```

[FastAPI 公式　本文・パス・クエリの読み分け](https://fastapi.tiangolo.com/tutorial/body/)

[前へ　実装 02](02-resources.md) ｜ [教科書 03](../textbook/03-inputs.md) ｜ [実例 03](../examples/03-inputs.md) ｜ [シート B3](../templates/contract-sheet.md#b3) ｜ [次へ　実装 04](04-methods.md) ｜ [実装編の目次](README.md)
