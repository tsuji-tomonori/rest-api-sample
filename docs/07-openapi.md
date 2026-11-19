# 第7章　修理依頼の設計を OpenAPI で書く

「修理を依頼すると、受付番号が返る」。第6章で決めたこの約束を、画面の担当者に渡してみましょう。担当者が知りたいのは、何をどこに送ればよいか、返ってきた番号でどうやって依頼を開くかです。**OpenAPI** を使うと、その一連の操作を、人もツールも読める設計書にできます。JSON と YAML のどちらでも書けます。[OpenAPI 3.1.1 §3.2](https://spec.openapis.org/oas/v3.1.1.html#openapi-document)

## 一つの操作を、送るものと返るものに分ける

まず登録を考えます。送信先は `/repair-requests`、操作は `POST` です。設計書では `paths` の中にパスを書き、その下の `post` にこの操作の約束をまとめます。`operationId` はツールから操作を識別する名前です。付けるときは設計書の中で一意にします。[OpenAPI の Operation Object](https://spec.openapis.org/oas/v3.1.1.html#operation-object)

件名と場所は JSON の本文で送ります。`requestBody` に本文、`content` にメディアタイプ、`schema` に値の形を書きます。応答は `responses` の下でステータスコードごとに分けます。登録が成功すれば `201`。画面は本文から受付番号を読み、`Location` ヘッダーのパスを使って詳細を開けます。[OpenAPI の Request Body](https://spec.openapis.org/oas/v3.1.1.html#request-body-object)・[Response](https://spec.openapis.org/oas/v3.1.1.html#response-object)・[RFC 9110 §15.3.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.3.2)

次は詳細を開く操作です。`/repair-requests/{request_id}` の波かっこは、実際の番号が入る場所です。`parameters` に同じ名前の `request_id` を書き、場所を `in: path`、必須を `required: true` と指定します。URL が `/repair-requests/42` なら、値は `42` です。[OpenAPI の Parameter Object](https://spec.openapis.org/oas/v3.1.1.html#parameter-object)

## 登録と照会の設計書を書いてみる

次は、そのまま一つの YAML ファイルとして読める記述例です。最初は `paths` の下で「登録した」「見つかった」「見つからなかった」の3か所をたどってみてください。本文の型は末尾の `components.schemas` に置き、各操作から `$ref` で参照しています。この手書き例では登録と照会に絞ります。[全5操作の設計書（YAML）](openapi.yaml)

```yaml
openapi: 3.1.0
info:
  title: 修理依頼 API の記述例
  version: 1.0.0
paths:
  /repair-requests:
    post:
      operationId: createRepair
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/NewRepair' }
      responses:
        '201':
          description: 修理依頼を登録した
          headers:
            Location:
              description: 登録した依頼を開くためのパス
              schema: { type: string, format: uri-reference }
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Repair' }
  /repair-requests/{request_id}:
    get:
      operationId: getRepair
      parameters:
        - name: request_id
          in: path
          required: true
          schema: { type: integer, minimum: 1, maximum: 2147483647 }
      responses:
        '200':
          description: 指定した依頼が見つかった
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Repair' }
        '404':
          description: 指定した依頼が見つからなかった
          content:
            application/problem+json:
              schema: { $ref: '#/components/schemas/Problem' }
components:
  schemas:
    NewRepair:
      type: object
      required: [title, location]
      additionalProperties: false
      properties:
        title: { type: string, minLength: 1, maxLength: 100 }
        location: { type: string, minLength: 1, maxLength: 100 }
    Repair:
      type: object
      required: [id, title, location, status]
      properties:
        id: { type: integer, minimum: 1, maximum: 2147483647 }
        title: { type: string }
        location: { type: string }
        status: { type: string, enum: [open, completed] }
    Problem:
      type: object
      required: [title, status, detail]
      properties:
        type: { type: string, default: 'about:blank' }
        title: { type: string }
        status: { type: integer }
        detail: { type: string }
```

登録時の入力は `NewRepair`、登録後の表現は `Repair` です。社員が送るのは件名と場所だけで、受付番号と初期状態はサーバーが決めます。登録成功時と照会成功時の両方が同じ `Repair` を参照するので、画面はどちらの応答も同じ形で読めます。失敗時の本文は第5章の形式に合わせて `application/problem+json` と書きます。[OpenAPI の Components Object](https://spec.openapis.org/oas/v3.1.1.html#components-object)・[RFC 9457 §3](https://www.rfc-editor.org/rfc/rfc9457.html#section-3)

## 一覧の条件と「値がない」を表す

実際の一覧には「未完了を最大10件」という指定もあります。`GET /repair-requests?status=open&limit=10` の操作を定義するとき、`paths` に書くキーは `/repair-requests` です。その `get.parameters` に `status` と `limit` を `in: query` で定義します。`limit` の定義を取り出すと次のようになります。[OpenAPI の Paths Object](https://spec.openapis.org/oas/v3.1.1.html#paths-object)・[Parameter Object](https://spec.openapis.org/oas/v3.1.1.html#parameter-object)

```yaml
- name: limit
  in: query
  required: false
  schema: { type: integer, minimum: 1, maximum: 100, default: 20 }
```

利用者は `limit` を省略でき、そのときサンプルは20件を上限にします。一方、一覧の**応答**には毎回 `next_after` があります。値は次のページを読むための番号か、最後のページを表す `null` です。「項目があるか」はオブジェクトの `required`、「どんな値を入れられるか」はその項目のスキーマで決めます。OpenAPI 3.1 では整数と `null` を `type: [integer, 'null']` と書けます。生成した JSON では `anyOf` に整数と `null` の二つの型が並びます。[OpenAPI の Schema Object](https://spec.openapis.org/oas/v3.1.1.html#schema-object)・[JSON Schema の null](https://json-schema.org/understanding-json-schema/reference/null)

## 実装から同じ設計書を取り出す

サンプルでは Python の型と FastAPI のルート定義から、同じ設計書を [YAML](openapi.yaml) と [JSON](openapi.json) で生成しています。`openapi: 3.1.0` は設計書を読むための規格の版です。`info.version: 1.0.0` はこの設計書に付けた版で、FastAPI の `version` に設定しています。どちらの値もリクエストのパスを変えません。[OpenAPI の OpenAPI Object](https://spec.openapis.org/oas/v3.1.1.html#openapi-object)・[Info Object](https://spec.openapis.org/oas/v3.1.1.html#info-object)・[FastAPI のメタデータ](https://fastapi.tiangolo.com/tutorial/metadata/)

公開後に設計書を更新するときは、変更前の定義と比べます。たとえば登録の必須項目が一つ増えると、これまで件名と場所だけを送っていた画面からは登録できなくなります。このような変更をどう公開するかは、第11章で判断します。[第11章　API のバージョンを上げる](11-versioning.md)

uv を使い、リポジトリのルートで次のコマンドを実行します。上の行は仕様書を更新し、下の行は保存済みの内容と実装が一致するかを確認します。どちらも `app.openapi()` を呼ぶので、Web サーバーの起動や DB 接続は不要です。[生成コマンドの実装](../package/app/export_openapi.py)・[FastAPI の OpenAPI 生成](https://fastapi.tiangolo.com/how-to/extending-openapi/)

```console
uv run --locked python -m package.app.export_openapi docs/openapi.yaml docs/openapi.json
uv run --locked python -m package.app.export_openapi --check docs/openapi.yaml docs/openapi.json
```

## 入力例を送り、期待した応答と比べる

登録の入力例は、FastAPI の `Body(openapi_examples=...)` に名前を付けて書きます。[全5操作の YAML](openapi.yaml) で `office-chair` を探してみてください。`value` が送る本文です。この教材では、同じ例の `x-expected-status` に期待する `201`、`x-expected-fields` に照合したい応答の項目を記録します。空白だけの件名など、エラーを試す入力は操作の `x-negative-examples` にまとめています。`examples` は OpenAPI の標準項目で、`x-` で始まるこれらの名前と意味は教材で決めたものです。[FastAPI の入力例](https://fastapi.tiangolo.com/tutorial/schema-extra-example/#using-the-openapi_examples-parameter)・[OpenAPI の Example Object](https://spec.openapis.org/oas/v3.1.1.html#example-object)・[Specification Extensions](https://spec.openapis.org/oas/v3.1.1.html#specification-extensions)

契約テストは、保存した YAML から各例を読み、起動中の API に本文を送ります。たとえば空白だけの件名なら `422`、通常の登録なら `201` を期待します。成功時は応答の項目を照合し、`Location` が示す先で同じ依頼を読み出せることも確かめます。AWS の署名と権限は API Gateway が確認するため、デプロイ後に別途検証します。[契約テスト](../tests/contract/check.py)・[AWS での構成例](09-aws.md)

手元の API を起動すると、`/openapi.json` でその実行中の契約を取得できます。`/docs` を開くと、ブラウザーで各操作の入力欄と応答例を見ながらリクエストを送れます。次の章では、実際に依頼を登録して `201` と `Location` が返るところを確かめます。[FastAPI の Docs URLs](https://fastapi.tiangolo.com/tutorial/metadata/#docs-urls)

[前へ：第6章　業務を API の契約にする](06-contract.md) ｜ [目次](../README.md) ｜ [次へ：第8章　FastAPI で実装する](08-fastapi.md)
