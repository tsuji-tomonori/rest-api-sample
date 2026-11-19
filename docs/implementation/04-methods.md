# 実装編 04　メソッドとパスを Python 関数に結び付ける

FastAPI では、関数の上に付ける `@app.get(...)` や `@app.post(...)` で、どのメソッド・パスをその関数に渡すかを指定します。これを**ルートの登録**といいます。AWS では API Gateway がリクエストを Lambda に渡し、関数を選ぶこの部分は手元と同じ FastAPI が担当します。

## どの関数に渡すか

| メソッドとパス | FastAPI の指定と呼び出す関数 | DB で行うこと |
| --- | --- | --- |
| `GET /repair-requests` | `@app.get` → `list_repairs` | 絞り込みと順序を付けて複数件を読む |
| `GET /repair-requests/{request_id}` | `@app.get` → `get_repair` | 受付番号で1件を読む |
| `POST /repair-requests` | `@app.post` → `create_repair` | 初期状態が `open` の行を追加する |
| `PATCH /repair-requests/{request_id}` | `@app.patch` → `update_status` | 指定した行の状態だけを更新する |
| `DELETE /repair-requests/{request_id}` | `@app.delete` → `delete_repair` | 指定した行を削除する |

実例編で検討した「呼び出し元が指定した宛先の内容を丸ごと置き換える」操作を追加するなら、`@app.put("/repair-requests/{request_id}")` に、全体の入力モデルとそれを保存する関数を結び付けます。現在のサンプルが提供するのは表の5操作です。[ルート定義](../../package/app/main.py)・[実例編 04 の PUT を選ぶ条件](../examples/04-methods.md)

## 詳細取得の関数にメソッドとパスを付ける

詳細取得の関数 `get_repair` のすぐ上に、次の指定を書きます。先頭の `@app.get` がメソッドを、最初の引数がパスを決めます。たとえば `GET /repair-requests/42` が届くと、FastAPI はこの関数を選び、引数 `request_id` に整数の `42` を渡します。

```python
@app.get(
    "/repair-requests/{request_id}",
    operation_id="getRepair",
    summary="修理依頼を1件取得する",
    response_model=Repair,
    response_description="指定した受付番号の依頼を返します。",
    responses=problems(404, 422),
)
```

同じ `/repair-requests/42` に `PATCH` を送ると、`@app.patch` を付けた `update_status` が呼ばれます。どちらも受付番号はパスから受け取り、更新ではさらに本文から新しい状態を読みます。[取得関数の本体](02-resources.md)・[更新関数の本体](06-contract.md)

`operation_id="getRepair"` は公開仕様書に載る操作名、`summary` はその見出しです。`response_model` で返す項目の型を、`responses` で仕様書に載せるエラーを指定します。[応答の作り方](05-responses.md)・[生成した仕様書との対応](07-openapi.md)

## 5操作をまとめて確かめる

リポジトリのルートで実行します。次のテストは一時的な SQLite と FastAPI を使うので、別の端末にサーバーを起動する必要はありません。

```console
uv run --locked python -m pytest -q tests/test_api.py::test_lifecycle
```

このテストは1件を登録し、返った `Location` で詳細を取得します。完了にすると、未完了の一覧からその依頼が消えます。削除時に `204`、同じ番号を再照会すると `404` が返るところまで通れば成功です。起動した API に自分で送る場合は[実例編 04 の curl 手順](../examples/04-methods.md)を使えます。[テストコード](../../tests/test_api.py)

[FastAPI 公式　ルートごとの設定](https://fastapi.tiangolo.com/tutorial/path-operation-configuration/)・[更新処理](https://fastapi.tiangolo.com/tutorial/body-updates/)

[前へ　実装 03](03-inputs.md) ｜ [教科書 04](../textbook/04-methods.md) ｜ [実例 04](../examples/04-methods.md) ｜ [シート B2](../templates/contract-sheet.md#b2) ｜ [次へ　実装 05](05-responses.md) ｜ [実装編の目次](README.md)
