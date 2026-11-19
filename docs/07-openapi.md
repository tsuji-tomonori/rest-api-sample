# 第7章　設計シートを OpenAPI の仕様書にする

第6章の設計シートでは、件名と場所を送ると、受付番号とその依頼を開く宛先が返ると決めました。この約束を **OpenAPI**（HTTP API の仕様を記述する規格）で書けば、画面の担当者は項目名や型を調べられ、ツールも同じ定義を読み取れます。[修理依頼の公開仕様書（YAML）](openapi.yaml)

## 一つの操作を、入力からたどる

YAML（ヤムル）は、項目名と値をテキストで書く形式です。たとえば `title: 修理依頼 API` は、左が項目名、右が値です。下の例では字下げを一段深くして、`post` が `/repair-requests` に属することを表しています。

**サンプルで試せる**　次は公開仕様書から、登録と詳細取得を抜き出したものです。設計シートの「何をどこに送るか」は `requestBody` に、「成功時に何を返すか」「失敗時にどう直せるか」は `responses` に現れます。

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
      summary: 修理依頼を1件取得する
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

## 受け付ける入力と、拒む入力の例を添える

**サンプルで試せる**　設計シートの登録例を、実際に送る値と期待する結果の組にします。どの処理をするかは、同じ文字列型でも内容によって変わります。

| 登録の例 | 送る値の特徴 | 期待するレスポンス |
| --- | --- | --- |
| `office-chair` | 件名「椅子がぐらつく」、場所「第2会議室」 | `201`、状態は `open` |
| `trim-spaces` | 件名「照明が消える」と場所「受付」の前後に空白 | `201`、件名と場所の前後の空白を除く |
| `blank-title` | 件名が空白だけ | `422` |

受け付ける入力は、OpenAPI 標準の `examples` に名前を付け、送る本文を `value` に書きます。この教材では、拒む入力を `x-negative-examples` に、期待するステータスや応答項目を `x-expected-status`、`x-expected-fields` に書きます。これらの `x-` 項目は教材の拡張です。[第11章のテスト](11-testing.md)では、公開仕様書の例を実装に送り、結果を照合します。

## 公開する YAML を更新する

このサンプルでは FastAPI のルートや Python の型を変更し、そこから仕様書を生成します。リポジトリのルートで1行目を実行すると YAML が更新されます。2行目は、保存したファイルが生成結果と一致するかを調べます。どちらもサーバーの起動や DB 接続は不要です。

```console
uv run --locked python -m package.app.export_openapi docs/openapi.yaml
uv run --locked python -m package.app.export_openapi --check docs/openapi.yaml
```

ファイルの `openapi: 3.1.0` は記述に使う規格の版、`info.version: 1.0.0` はこの仕様書に付けた版です。起動中の FastAPI は同じ定義を `/openapi.json` で返し、操作画面の Swagger UI が読み込みます。

**公開後に変更するときは、以前の画面が同じ操作を続けられるかを確かめます。** たとえば登録に「担当部署」を加え、省略しても従来どおり登録できるなら、古い画面は今の入力を使い続けられます。必須にすれば、件名と場所だけを送る画面は登録に失敗します。仕様書の差分と以前の入力例を照らし、利用者の変更が必要なら、公開前に移行方法を決めます。[第13章のバージョン管理](13-versioning.md)

## この章で決めたこと

- 設計シートにある操作・入力・レスポンスを、それぞれ `paths`、パラメータや本文、`responses` に写す。
- 画面と API の担当者が同じスキーマと入力例を使えるように、期待する結果まで含めて仕様書に記録する。
- 公開済みの仕様を変える場合は、以前の入力とレスポンスを使う画面への影響を確認する。

## 根拠と参考

- [この章の YAML 抜粋を配布仕様書と照合するテスト](../tests/unit/test_book_openapi.py)
- OpenAPI の仕様書、各操作、入出力の定義と拡張項目。[OpenAPI 3.1.1](https://spec.openapis.org/oas/v3.1.1.html)・[Operation Object](https://spec.openapis.org/oas/v3.1.1.html#operation-object)・[Specification Extensions](https://spec.openapis.org/oas/v3.1.1.html#specification-extensions)
- 公開済みの操作に項目を加える際の互換性。[Google AIP-180](https://google.aip.dev/180#adding-components)
- 登録成功時の宛先、エラー本文の形式。[RFC 9110 §10.2.2 Location](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.2)・[§15.3.2 201 Created](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.3.2)・[RFC 9457 §3 Problem Details](https://www.rfc-editor.org/rfc/rfc9457.html#section-3)
- FastAPI での仕様書の生成と入力例の指定。[OpenAPI の生成](https://fastapi.tiangolo.com/how-to/extending-openapi/)・[名前付き入力例](https://fastapi.tiangolo.com/tutorial/schema-extra-example/#using-the-openapi_examples-parameter)
- このサンプルの実装と検査。[公開仕様書](openapi.yaml)・[入力例](../package/app/schemas.py)・[出力コマンド](../package/app/export_openapi.py)・[契約テスト](../tests/contract/check.py)

[前へ　第6章　業務の要望から API を設計する](06-contract.md) ｜ [目次](../README.md) ｜ [次へ　第8章　会議室の予約なら、何が変わるか](08-practice.md)
