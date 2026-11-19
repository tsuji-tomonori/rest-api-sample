# 第7章　OpenAPI 仕様書

設計シートの対応欄　[C2 OpenAPI に転記する](../templates/contract-sheet.md#review)

## 定義

**OpenAPI** は、HTTP API の呼び方と返る結果を、人とツールが同じ定義から読めるようにする規格です。設計シートで操作を一つ決めたら、「何を送るか」「何が返るか」の順に仕様書へ写します。

この教材の仕様書には **YAML** を使います。YAML は項目名と値を `項目名: 値` の形で書き、字下げで親子関係を、行頭の `-` で一覧の各要素を表す形式です。API の通信には、仕様書で指定したメディアタイプを使います。

## 選択肢

| 設計シートで決めたこと | OpenAPI 3.1 で書く場所 | 記入の手掛かり |
| --- | --- | --- |
| 何の仕様書か | `openapi`、`info.title`、`info.version` | 書式の版、API の名前、この仕様書の版を書く |
| 何ができるか | `paths` → パス → メソッド | 操作ごとに短い `summary` を書く。`operationId` を付ける場合は仕様書内で一意にする |
| パス・クエリ・ヘッダーに入れる値 | `parameters` | `name` に名前、`in` に置き場所、`schema` に型や範囲を書く。パスの変数名は波かっこの中と合わせ、`required: true` にする |
| 送る本文 | `requestBody` → `content` → メディアタイプ | `schema` にデータの形、`examples` に実際に送れる値を置く |
| 成功時と失敗時の結果 | `responses` → ステータスコード | `description` に結果の意味を書く。返すヘッダーは `headers`、本文の形式と型は `content` に置く |
| 複数の操作で共用する型 | `components.schemas` | 名前を付けて定義し、使う場所から `$ref` で参照する |
| 共通の認証方式 | `components.securitySchemes` と `security` | 利用できる方式を定義して必要な操作に適用する。本人だけが変更できるなどの業務条件は操作の説明にも残す |

## 選ぶ基準

初めて書くときは、[設計シート C2 と一操作の YAML ひな形](../templates/contract-sheet.md#c2)を開き、下の順に読み直します。

1. **一つの呼び出しを組み立てられるか。** パスとメソッドを選び、必須の入力を順に埋めます。本文そのものが必須なら `requestBody.required`、本文内のどの項目が必須かはオブジェクトの `required` 一覧に書きます。
2. **同じ呼び出しで起こり得る結果を読めるか。** ステータスコードは YAML で `'201'` のように引用符で囲みます。新しい対象の取得先を返すなら `Location` を記し、本文のない `204` には `content` を書きません。
3. **型が合っていても間違える条件が残っていないか。** `schema` は型や長さなどの規則です。例には入力と期待する結果を対応させ、初期状態や失敗後の変化も説明します。機械的に表しにくい条件は `description` と完成確認の例に残せます。

## よくある誤り

入力と出力に同じ型を使うと、自動採番する番号まで登録時に必須と読めることがあります。利用者が送る項目と、登録後に読める項目を照合し、異なる形には別の型を用意します。入力例が一つ書いてあっても、必須項目や長さの条件は自動で決まりません。許容範囲は型の定義に書きます。

<details>
<summary>発展　コードから生成する場合</summary>

ルート、入力・出力の型、レスポンスをコードに宣言し、同じ定義から仕様書を生成する方法があります。生成後は、ステータス、ヘッダー、業務上の意味がシートの通りに伝わるかを読み返します。実例編の第7章で、生成した YAML と設計シートを見比べられます。

</details>

## 根拠と参考

- [OpenAPI 3.1.1　操作](https://spec.openapis.org/oas/v3.1.1.html#operation-object)・[パラメータ](https://spec.openapis.org/oas/v3.1.1.html#parameter-object)・[レスポンス](https://spec.openapis.org/oas/v3.1.1.html#response-object)
- [OpenAPI 3.1.1　型](https://spec.openapis.org/oas/v3.1.1.html#schema-object)・[認証方式](https://spec.openapis.org/oas/v3.1.1.html#security-scheme-object)・[YAML 1.2.2](https://yaml.org/spec/1.2.2/)

[前へ　第6章](06-contract.md) ｜ [実例 07](../examples/07-openapi.md) ｜ [シート C2](../templates/contract-sheet.md#c2) ｜ [次へ　第8章](08-compatibility.md) ｜ [目次](../../README.md)
