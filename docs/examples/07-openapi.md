# 実例編 07　登録の設計を OpenAPI に写す

[教科書 07　OpenAPI](../textbook/07-openapi.md) ｜ [設計シート C2　OpenAPI に転記する](../templates/contract-sheet.md#review)

## 要望と決めること

画面の担当者には「何を送ればよいか」、テストの担当者には「何が返れば合格か」を伝えたいところです。二つの資料に別々の例を書くと、変更のたびに両方を直す必要があります。そこで同じ登録例を仕様書に載せ、画面とテストで共有します。

## 選択肢と選んだ理由

修理依頼は、社員が決める値と、保存した後に初めて決まる値が違います。入力には `NewRepair`、登録結果には `Repair` を使います。受付番号を入力の必須項目にしてしまうと、自分で番号を選べない社員が送信できなくなるからです。

**C2 OpenAPI に転記する**では、シートの左から順に次の欄へ写します。

| シートの決定 | 公開 YAML での置き場所 |
| --- | --- |
| B2　登録する | `paths` の `/repair-requests` → `post` |
| B3・B4　件名と場所を受け付ける | `requestBody` から `components.schemas.NewRepair` を参照 |
| B6　新しい番号で詳細を開ける | `responses` の `'201'` に本文と `headers.Location` を書く |
| B7　入力を直せる | `'400'`・`'415'`・`'422'` の本文に共通の `Problem` を使う |
| B9　登録結果を確かめる | 本文の `examples` に入力例を載せ、期待結果も記録する |

次の二つは、[実際の公開仕様書](../openapi.yaml)から、登録の判断に関わる項目を抜き出したものです。最初の抜粋で送る値と返る値をたどり、二つ目の抜粋で入力の条件を読みます。

```yaml
openapi: 3.1.0
info:
  title: 修理依頼 API
  version: 1.0.0
paths:
  /repair-requests:
    post:
      operationId: createRepair
      summary: 修理依頼を登録する
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/NewRepair' }
            examples:
              office-chair:
                value: { title: 椅子がぐらつく, location: 第2会議室 }
                x-expected-status: 201
                x-expected-fields: { status: open }
      responses:
        '201':
          description: 修理依頼を登録しました。本文に登録内容、Location に取得先のパスを返します。
          headers:
            Location:
              description: 登録した依頼のパス
              schema: { type: string, format: uri-reference }
              example: /repair-requests/42
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Repair' }
        '422':
          description: 入力値が条件に合いません。エラーの詳細で該当する項目を確認してください。
          content:
            application/problem+json:
              schema: { $ref: '#/components/schemas/Problem' }
```

```yaml
components:
  schemas:
    NewRepair:
      type: object
      required: [title, location]
      additionalProperties: false
      properties:
        title: { type: string, minLength: 1, maxLength: 100, pattern: '^[^\x00]+$' }
        location: { type: string, minLength: 1, maxLength: 100, pattern: '^[^\x00]+$' }
```

## 条件が変わったら

現行の仕様書は、定義した二つの入力以外を `additionalProperties: false` で拒みます。`id` を送って `422` になる例は、正しい送り方と区別して操作の `x-negative-examples` に載せました。`x-expected-status`、`x-expected-fields` と合わせて、このサンプルがテストに使う拡張項目です。

別の業務で利用側があらかじめ番号を決め、その宛先に依頼全体を作成・置換するなら、`PUT /repair-requests/{request_id}` が候補になります。その場合はシートの B2 を書き換え、OpenAPI でも番号を必須のパスパラメータに移し、既存の番号を指定した場合の結果を B8 に残します。

## 設計シートの記入結果

**C2** に「`createRepair` を `office-chair` の値で呼ぶと `201`。返った `Location` の詳細は初期状態 `open`」と書きます。別の担当者はこの1行を起点に、[設計シート](../templates/contract-sheet.md#review)、[公開 YAML](../openapi.yaml)、[実際に例を送るテスト](../../tests/contract/check.py)を照合できます。

<details>
<summary>手元で確かめる（任意）　FastAPI から YAML を生成する</summary>

リポジトリのルートで1行目を実行すると仕様書が更新されます。2行目で、保存した YAML が現在のコードの生成結果と一致するかを確認できます。どちらも API や DB の起動は不要です。

```console
uv run --locked python -m package.app.export_openapi docs/openapi.yaml
uv run --locked python -m package.app.export_openapi --check docs/openapi.yaml
```

初回の準備と、API を起動して結果を確かめる手順は[FastAPI の実装ガイド](../build/fastapi.md)で扱います。

</details>

[前へ　第6章](06-contract.md) ｜ [教科書 07](../textbook/07-openapi.md) ｜ [シート C2](../templates/contract-sheet.md#c2) ｜ [次へ　第8章](08-compatibility.md) ｜ [目次](../../README.md)
