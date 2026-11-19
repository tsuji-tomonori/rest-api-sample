# 第7章　設計シートを OpenAPI の仕様書にする

画面の担当者が修理依頼の登録機能を作るとします。「件名と場所を送る」という設計シートを見ても、件名の項目名や、登録した依頼を開く宛先までは分かりません。**OpenAPI** は、HTTP リクエストの送り方と、サーバーから返る HTTP レスポンスを、人とツールが同じ仕様書から読めるようにする規格です。この教材の公開仕様書は [openapi.yaml](openapi.yaml) です。

## 一つの操作を、入力からたどる

**サンプルで試せる**　修理依頼の登録と詳細取得を、YAML で手書きすると次のようになります。これは公開仕様書の抜粋です。ここでは登録の成功と、受付番号が見つからない場合を取り上げます。全5操作のスキーマや入力例は公開仕様書で読めます。

```yaml
openapi: 3.1.0
info:
  title: 修理依頼 API
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
          description: 修理依頼を登録しました。本文に登録内容、Location に取得先のパスを返します。
          headers:
            Location:
              description: 登録した依頼のパス
              schema: { type: string, format: uri-reference }
              example: /repair-requests/42
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
          description: 指定した受付番号の依頼を返します。
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Repair' }
        '404':
          description: 指定した受付番号の依頼が見つかりません。
          content:
            application/problem+json:
              schema: { $ref: '#/components/schemas/Problem' }
```

まず `paths` から `/repair-requests`、`post` の順に読みます。これが HTTP の `POST /repair-requests` に対応します。`operationId` は、ツールが一つの操作を識別するための名前です。指定する場合は、仕様書全体で重複しない名前を選びます。

送る値は `requestBody` にあります。`application/json` は本文の形式、`schema` は本文に使える項目や型の定義です。`$ref` は仕様書内の別の定義を指します。たとえば `#/components/schemas/NewRepair` の参照先を開くと、必須項目は `title` と `location` だと分かります。送る本文は `{"title":"椅子がぐらつく","location":"第2会議室"}` です。

受け取る値は `responses` で、ステータスコードごとに読みます。登録が成功すると `201` で、本文には受付番号と状態を含む `Repair` が入ります。`Location` の値は登録した依頼を指す URI 参照です。たとえば `/repair-requests/42` が返ったら、同じサーバーのそのパスに `GET` を送れます。`200` の本文は登録時と同じ `Repair`、該当する依頼がなければ `404` の本文はエラー用の `Problem` です。

## スキーマに必須項目と値の条件を書く

登録用の `NewRepair` を抜き出したのが次の定義です。`properties` に入力項目を並べ、`required` で必須項目を選びます。`additionalProperties: false` と書くと、サーバーが発行する `id` など、ここで定義していない項目は入力できません。

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

どちらも1〜100文字の文字列です。`pattern` はヌル文字（U+0000）を除く条件です。アプリは件名と場所の前後の空白も取り除きます。この振る舞いは後の入力例で確かめます。

## パスに埋める値、条件に使う値、省略できる値

`/repair-requests/{request_id}` の波かっこには、開きたい依頼の番号が入ります。個別の依頼を指定するには番号が必要なので、`request_id` は `in: path` と `required: true` です。一覧の表示件数は、利用者が選べます。`GET /repair-requests?limit=10` の `limit` は `in: query`、`required: false` です。省略すると既定の20件まで返ります。

「省略できる」と「`null` が入る」には別々の意味があります。一覧のレスポンスには、続きの有無を示す `next_after` が毎回入ります。最後のページでは `{"items":[],"next_after":null}` のように、項目があって値が `null` になります。公開仕様書では、`RepairPage.required` に項目名を載せ、`next_after` の `anyOf` で整数と `null` の両方を許しています。

## 具体例を使って、仕様書と実装を照らし合わせる

**サンプルで試せる**　公開仕様書には、登録と状態変更のリクエスト本文が計8例あります。たとえば `trim-spaces` では前後に空白がある件名を送り、返ってきた件名から空白が除かれていることを確かめます。

| 操作 | 仕様書の例 | 送る値の特徴 | 期待するレスポンス |
| --- | --- | --- | --- |
| 登録 | `office-chair` | 件名「椅子がぐらつく」、場所「第2会議室」 | `201`、状態は `open` |
| 登録 | `trim-spaces` | 件名「照明が消える」と場所「受付」の前後に空白 | `201`、件名と場所の前後の空白を除く |
| 登録 | `blank-title` | 件名が空白だけ | `422` |
| 登録 | `client-id` | 本文に `"id":42` を加える | `422` |
| 状態変更 | `complete` | `{"status":"completed"}` | `200`、状態は `completed` |
| 状態変更 | `reopen` | `{"status":"open"}` | `200`、状態は `open` |
| 状態変更 | `unknown-status` | `{"status":"done"}` | `422` |
| 状態変更 | `missing-status` | `{}` | `422` |

受理する入力例は、OpenAPI 標準の `examples` に置きます。教材ではそれぞれの `value` に送る値、`x-expected-status` に期待するステータスを書き、一部の例には `x-expected-fields` で返ってくる項目の値も指定しています。拒否する例は操作の `x-negative-examples` に置きます。これらの `x-` 項目は教材独自の拡張で、契約テストが読み取り、実際に HTTP リクエストを送って結果を照合します。

## 公開する YAML を更新する

このサンプルでは FastAPI のルートや Python の型を変更し、そこから仕様書を生成します。リポジトリのルートで1行目を実行すると YAML が更新されます。2行目は、保存したファイルが生成結果と一致するかを調べます。どちらもサーバーの起動や DB 接続は不要です。

```console
uv run --locked python -m package.app.export_openapi docs/openapi.yaml
uv run --locked python -m package.app.export_openapi --check docs/openapi.yaml
```

ファイルの `openapi: 3.1.0` は記述に使う規格の版です。`info.version: 1.0.0` はこの仕様書に付けた版です。どちらも HTTP リクエストのパスとは別に決めます。起動中の FastAPI は同じ定義を `/openapi.json` でも返し、操作画面の Swagger UI が読み込みます。API に送る修理依頼の本文は、仕様書の `requestBody` で指定した JSON です。


## この章で決めたこと

- 設計シートのメソッドとパスを、仕様書の paths に対応付ける。
- 入力とレスポンスのスキーマを定義し、共通の型は $ref で参照する。
- YAML の具体例を実際に送り、返るステータスと本文を照合する。

## 根拠と参考

- OpenAPI の仕様書、各操作、入出力の定義と拡張項目。[OpenAPI 3.1.1](https://spec.openapis.org/oas/v3.1.1.html)・[Operation Object](https://spec.openapis.org/oas/v3.1.1.html#operation-object)・[Specification Extensions](https://spec.openapis.org/oas/v3.1.1.html#specification-extensions)
- 登録成功時の宛先、エラー本文の形式。[RFC 9110 §10.2.2 Location](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.2)・[§15.3.2 201 Created](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.3.2)・[RFC 9457 §3 Problem Details](https://www.rfc-editor.org/rfc/rfc9457.html#section-3)
- FastAPI での仕様書の生成と入力例の指定。[OpenAPI の生成](https://fastapi.tiangolo.com/how-to/extending-openapi/)・[名前付き入力例](https://fastapi.tiangolo.com/tutorial/schema-extra-example/#using-the-openapi_examples-parameter)
- このサンプルの実装と検査。[公開仕様書](openapi.yaml)・[入力例](../package/app/schemas.py)・[出力コマンド](../package/app/export_openapi.py)・[契約テスト](../tests/contract/check.py)

[前へ　第6章　業務の要望から API を設計する](06-contract.md) ｜ [目次](../README.md) ｜ [次へ　第8章　会議室の予約なら、何が変わるか](08-practice.md)
