# 実装編 05　ステータス、ヘッダー、本文を返す

修理依頼の登録では、画面が「保存できた」と判断するための `201` と、保存した依頼を開くための `Location` の両方を返します。まず正常に完了したときの応答を書き、次にデータが見つからないときの応答をそろえます。

## 登録の結果を組み立てる

[登録ルートの `create_repair`](../../package/app/main.py) で、成功時の約束を三つに分けて書きます。

| 返したいもの | FastAPI に書く場所 | この実装で返るもの |
| --- | --- | --- |
| ステータス | `@app.post(...)` の `status_code=201` | 正常に登録が終わると `201 Created` |
| ヘッダー | 関数の引数 `response: Response` で受け取り、`response.headers` に値を入れる | 作成した1件のパス |
| 本文 | `response_model=Repair` を指定し、関数の最後で保存した行を返す | `id`、`title`、`location`、`status` の JSON |

登録関数の末尾は次の3行です。`db.commit()` で保存し、採番された番号をヘッダーに入れます。`return repair` で返した行から、FastAPI が `Repair` に定義した項目を取り出します。

```python
db.commit()
response.headers["Location"] = f"/repair-requests/{repair.id}"
return repair
```

ルートの `responses` にも `Location` が登場します。こちらは「どんなヘッダーが返るか」を仕様書に載せるための宣言です。実際の番号を入れるのは上の代入です。本文を返さない削除では `response_class=Response` を指定し、処理の最後で `return Response(status_code=204)` と書きます。

## 見つからないときは共通のエラー本文を返す

詳細取得で指定した依頼が見つからないと、`get_repair` は `HTTPException(404, NOT_FOUND)` を送出します。`configure_http(app)` で登録した例外ハンドラーが、番号と理由を共通の `problem()` 関数に渡します。[詳細取得の実装](../../package/app/main.py)・[例外ハンドラーと応答の実装](../../package/app/http.py)

```python
body = Problem(title=status_title(code), status=code, detail=detail)
return JSONResponse(
    body.model_dump(), status_code=code, headers=headers, media_type="application/problem+json"
)
```

`status_code` は HTTP のステータス、`Problem` の `status` は本文の値です。どちらにも同じ `code` を渡します。`media_type` で指定した形式は `Content-Type` ヘッダーに入ります。

## 受付番号が間違っているときの応答を確かめる

空の台帳で `GET /repair-requests/42` を呼ぶと、42 は受付番号として有効でも、該当する依頼がないため `404` が返ります。`GET /repair-requests/0` なら、受付番号は1以上という入力条件に合わず `422` が返ります。次のテストは専用の空の台帳でどちらも呼び、HTTP のステータスと本文の `status` の両方が期待どおりかを調べます。[確認する値とテストコード](../../tests/test_api.py)

```console
uv run --locked python -m pytest -q tests/test_api.py::test_read_errors
```

**公式資料**　[FastAPI のレスポンスヘッダー](https://fastapi.tiangolo.com/advanced/response-headers/)・[FastAPI の例外ハンドラー](https://fastapi.tiangolo.com/tutorial/handling-errors/)・[RFC 9457 のエラー形式](https://www.rfc-editor.org/rfc/rfc9457.html#section-3)

[前へ　実装 04](04-methods.md) ｜ [教科書 05](../textbook/05-responses.md) ｜ [実例 05](../examples/05-responses.md) ｜ [シート B6](../templates/contract-sheet.md#b6) ｜ [次へ　実装 06](06-contract.md) ｜ [実装編の目次](README.md)
