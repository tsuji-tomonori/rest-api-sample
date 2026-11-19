# 実装編 07　FastAPI から公開用の OpenAPI を生成する

修理依頼を登録する画面とテストは、同じ入力例を使えます。ここでは [設計シート C2](../templates/contract-sheet.md#c2) に書いた「件名と場所を送ると、新しい受付番号が返る」をコードに置き、その結果を YAML で確かめます。

## 入力例を登録ルートに渡す

[入出力モデル](../../package/app/schemas.py)では、`request_example` に入力値と期待する結果を渡し、名前を付けてまとめます。登録用の辞書から、会議室の椅子を修理する例を抜き出すと次のようになります。

```python
NEW_REPAIR_EXAMPLES = {
    "office-chair": request_example(
        "会議室の椅子を修理する",
        {"title": "椅子がぐらつく", "location": "第2会議室"}, 201,
        {"title": "椅子がぐらつく", "location": "第2会議室", "status": "open"},
    ),
}
```

[登録ルート](../../package/app/main.py)の引数とデコレーターで、FastAPI に次の情報を渡します。

| コードに書くもの | 生成された仕様書で読む場所 |
| --- | --- |
| 引数 `data: Annotated[NewRepair, Body(openapi_examples=NEW_REPAIR_EXAMPLES)]` | `requestBody.content` の `application/json`。入力モデルへの参照と、実際に送る `office-chair` の例 |
| デコレーターの `operation_id="createRepair"`、`summary="修理依頼を登録する"` | `paths` → `/repair-requests` → `post` の操作名と説明 |
| `status_code=201`、`response_model=Repair`、`responses` の `Location` | 同じ操作の `responses` → `'201'`。登録結果の型と、その依頼を開くためのヘッダー |

`examples` は OpenAPI 標準の項目です。期待値を表す `x-expected-status`、`x-expected-fields` は教材の契約テストが読む追加項目です。空白だけの件名など、拒む入力は `x-negative-examples` に分けています。[生成された例](../examples/07-openapi.md)

## YAML を生成し、実装と照合する

Python 3.12 と uv を用意し、リポジトリのルートで実行します。仕様書の生成にサーバーや DB を起動する必要はありません。

```console
uv run --locked python -m package.app.export_openapi docs/openapi.yaml
uv run --locked python -m package.app.export_openapi --check docs/openapi.yaml
```

1行目が `Wrote` と出力したら、[公開 YAML](../openapi.yaml)で `createRepair` を探します。`office-chair.value.location` に「第2会議室」、`responses` の `'201'` に `headers.Location` があれば、設計した入力例と取得先が仕様書に表れています。2行目の `Up to date` は、保存した YAML と現在のコードから生成した YAML が一致したことを示します。[生成コード](../../package/app/export_openapi.py)

実際の HTTP 応答まで確かめるには、テスト用の API と PostgreSQL を Docker Compose で起動し、公開 YAML の例を送ります。[実装編01](01-http.md)のサーバーが動いていれば、その端末で Ctrl+C を押して終了します。Compose も同じポート 8000 を使います。

```console
docker compose up --build --wait api
uv run --locked --group contract python tests/contract/check.py
```

この検査は登録時の `201`、`Location` から読み直した依頼の内容、拒否した入力のエラーなどを確かめます。最後に `All 5 documented operations passed the live lifecycle check.` と出れば、公開した5操作すべてで成功応答を確認できました。Swagger UI は稼働中の API の `/openapi.json` を読みます。画面に表示される例と、公開 YAML から送った例は、どちらも冒頭の Python の定義から作られます。[契約テスト](../../tests/contract/check.py)・[テスト用データの片付け方](../../package/app/README.md)

確認が済んだら `docker compose down` で API と PostgreSQL を停止します。

根拠　[FastAPI の名前付き入力例](https://fastapi.tiangolo.com/tutorial/schema-extra-example/#using-the-openapi_examples-parameter)・[FastAPI の操作 ID と OpenAPI 拡張](https://fastapi.tiangolo.com/advanced/path-operation-advanced-configuration/)

[前へ　実装 06](06-contract.md) ｜ [教科書 07](../textbook/07-openapi.md) ｜ [実例 07](../examples/07-openapi.md) ｜ [シート C2](../templates/contract-sheet.md#c2) ｜ [次へ　実装 08](08-compatibility.md) ｜ [実装編の目次](README.md)
