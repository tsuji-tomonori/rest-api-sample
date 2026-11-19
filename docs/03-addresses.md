# 第3章　パスとパラメータ

総務の担当者は未完了の依頼を一覧で見て、気になる1件を開きます。「42番の依頼」の **42** を替えると、別の依頼が開きます。「一度に10件」の **10** を替えると、表示件数が変わります。値を替えたときに何が変わるかを考えると、その値を置く場所が決まります。

## 一覧と1件に、それぞれ宛先を付ける

**サンプルで試せる**

対象を識別するための記述を **URI**（Uniform Resource Identifier）と呼びます。アクセス方法と場所を示す URI が **URL**（Uniform Resource Locator）です。たとえば `https://example.com/repair-requests/42` は URL です。`https` は通信方式、`example.com` はホスト名、その後の `/repair-requests/42` が **パス** です。図のホスト名は説明用です。

![修理依頼42番の URL と、仕様書の /repair-requests/{request_id} に受付番号を入れて実際のパスを作る例](assets/repair-uri.svg)

1. **扱うものに名前を付ける。** 社員と総務がやり取りするのは「修理依頼」です。集合のパスを `/repair-requests` とします。複数形で集合を示し、英単語を小文字とハイフンでそろえるのは、この教材の命名規約です。HTTP で決められた綴りではありません。
2. **1件を指す番号を足す。** 仕様書に書く `/repair-requests/{request_id}` の波かっこは、実際の番号に置き換える印です。総務が修理を終えて状態を「完了」に変えても、受付番号は同じです。
3. **操作は HTTP メソッドで伝える。** 1件を見る操作に `/getRepairRequest`、完了にする操作に `/completeRepairRequest` と別々に名付けると、同じ依頼を指す宛先が操作ごとに増えます。このサンプルは同じパスを使い、読むときは `GET`、状態を変えるときは `PATCH` を選びます。

受付番号は登録時にサーバーが付けます。`POST /repair-requests` の本文に送るのは `{"title":"椅子がぐらつく","location":"第2会議室"}` です。成功すると `201` が返り、本文の `id` と、レスポンスヘッダー `Location` のパスで作成した依頼が分かります。本文に自分で `id` を足すと、このサンプルでは入力エラーの `422` が返ります。

| 総務の操作 | リクエスト | 成功時に読むもの |
| --- | --- | --- |
| 未完了の依頼を最大10件表示する | `GET /repair-requests?status=open&limit=10` | `200`。本文の `items` が依頼を並べた配列。該当なしなら空の `[]` |
| 一覧から42番を開く | `GET /repair-requests/42` | `200` と依頼1件。例は `{"id":42,"title":"椅子がぐらつく","location":"第2会議室","status":"open"}` |

42 は受付番号の例です。手元では登録時に返った番号を使います。

## 入力をどこに置くか

同じ `status` でも、**未完了を探す**なら一覧の条件、**この依頼を完了にする**なら書き換える値です。

| 入力の場所 | 適した値と、この API での例 | 避けるものと理由 |
| --- | --- | --- |
| **パスパラメータ** | 1件を特定する番号。`/repair-requests/42` の `42` | パスワードや秘密の API キー。URL ごと共有・記録されることがある |
| **クエリパラメータ** | 一覧の条件や件数。`?` の後に `status=open&limit=10` と書く | 秘密のトークンや機微な個人情報。ブラウザーで URL を開くと、条件も閲覧履歴に残り得る |
| **リクエストヘッダー** | 通信に必要な情報。送る本文の形式は `Content-Type: application/json`、受け取りたい形式は `Accept: application/json` | 件名や場所などの業務データ。本文にまとめる方が、項目の意味や制約を仕様書に書きやすい |
| **リクエストボディ（本文）** | 登録する件名と場所、更新する値。完了なら `PATCH /repair-requests/42` に `{"status":"completed"}` を送る | `GET` の一覧条件。`GET` の本文には共通に定められた意味がなく、受信側が拒むこともある |

一覧の `status` は `open` と `completed` のどちらかで、省略すると両方が対象です。`limit` は1〜100の整数で、既定は20です。依頼は受付番号の小さい順に返ります。続きがあれば、レスポンスの `next_after` を次のリクエストの `after` に渡し、同じ絞り込み条件で次のページを開きます。たとえば `?status=open&limit=10&after=42` は、42番より後の未完了の依頼を最大10件返します。`next_after` が `null` なら最後のページです。

**パスワード、秘密のトークン、秘密の API キーは URL に入れません。** HTTPS が暗号化するのは TLS の接続区間です。接続を受けるサーバーや中継機器は、パスやクエリをアクセスログに記録できます。ヘッダーや本文も記録対象になり得るので、ログに残す項目を選び、認証情報は除きます。

## 設計を広げるとき

<details>
<summary>親の番号が必要な場合と、自分で番号を付ける場合</summary>

**設計例（未実装）**

修理依頼に作業記録を加えるとします。作業記録の番号が依頼ごとに1から始まるなら、`/repair-requests/42/work-logs/3` で「42番の依頼の3番目の記録」を区別できます。記録を作る宛先は `POST /repair-requests/42/work-logs` です。親の受付番号はパスにあるので、本文には新しい記録の `{"note":"椅子の脚を固定した"}` だけを送ります。どの依頼の記録かを問わず一意な作業番号があるなら、`/work-logs/3` でも特定できます。

利用者側が新しい受付番号を決める契約なら、`PUT /repair-requests/57` のように番号をパスに置き、そこに保存する完成形を本文で渡せます。作成だけを許す場合は `If-None-Match: *` を指定し、すでに対象があれば `412` で知らせます。パスと本文の両方で同じ ID を受ける契約では、不一致をどう扱うかも決めます。たとえばパスは42、本文は57なら、両方とも変更せず `400` を返す設計です。

何階層まで、という HTTP の決まりはありません。長さも一律ではなく、サーバーや中継機器にはそれぞれ上限があります。RFC 9110 が示す8,000オクテット（バイト）は、少なくともその長さの URI を扱えるようにする推奨値です。受け付けられる長さを超えた URI へのレスポンスは `414` です。

</details>

<details>
<summary>手続き、検索、ログインに応用する</summary>

**設計例（未実装）**

- **手続きを表したいとき。** 完了した事実だけでよければ、依頼の状態を変えます。誰がいつ完了を申請し、誰が承認したかまでたどりたいなら、`POST /repair-requests/42/completion-requests` のように申請を独立した対象にできます。標準的な操作で意図を表せないとき用に、独自の操作を許す設計指針もあります。
- **検索を広げるとき。** 一つの条件で複数の値を受けるなら、たとえば `?tag=chair&tag=desk` のように名前を繰り返す書式を選べます。OpenAPI でこの配列を表す指定は `style: form` と `explode: true` です。書式に加えて「どちらかに一致」「両方に一致」のどちらかも約束します。検索語に区切り文字が含まれるときは、たとえば `R&D` を `?q=R%26D` と符号化します。HTTP ライブラリに任せる場合は元の文字列を渡します。
- **ログインを作るとき。** 自社の認証サービスを使う例なら、HTTPS で `POST /sessions` の JSON 本文に `{"login_id":"<ログインID>","password":"<入力値>"}` を送ります。以降のリクエストで Bearer 方式のアクセストークンを使うなら、`Authorization: Bearer <アクセストークン>` ヘッダーに入れます。この教材の AWS 構成では IAM の署名で呼び出し元を確認します。
- **版の異なる契約を公開するとき。** パスで版を選ぶなら、`/v2/repair-requests/42` の `v2` が契約の版、`42` が受付番号です。現在の公開パスを保ったまま新版を加える方法は[バージョン管理の章](11-versioning.md)で扱います。

</details>

## この章で決めたこと

- 1件を特定する番号はパスに、一覧を絞る条件はクエリに置く。
- 登録する件名と場所は本文に、本文の形式はヘッダーに書く。
- パスワードやトークンを URL に入れず、本文やヘッダーを記録する場合も値を伏せる。

## 根拠と参考

- URI と URL、パスとクエリ、符号化の規則。[RFC 3986 §1.1.3](https://www.rfc-editor.org/rfc/rfc3986.html#section-1.1.3)・[§2.4](https://www.rfc-editor.org/rfc/rfc3986.html#section-2.4)・[§3](https://www.rfc-editor.org/rfc/rfc3986.html#section-3)
- HTTP の URI 長、GET・POST・PUT、条件付き作成と応答。[RFC 9110 §4.1](https://www.rfc-editor.org/rfc/rfc9110.html#section-4.1)・[§9.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3)・[§13.1.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-13.1.2)・[§15.5.15](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.5.15)
- 集合の命名と親子関係、独自操作は設計指針。パラメータの場所や必須条件は仕様書に記述する。[Microsoft のリソース設計指針](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design#define-restful-web-api-resource-uris)・[Zalando のパス命名規約](https://opensource.zalando.com/restful-api-guidelines/#129)・[Google AIP-136](https://google.aip.dev/136#guidance)・[OpenAPI の Parameter Object](https://spec.openapis.org/oas/v3.1.1.html#parameter-object)
- 機密情報の通信と記録、Bearer トークンの渡し方。[RFC 9110 §17.9](https://www.rfc-editor.org/rfc/rfc9110.html#section-17.9)・[RFC 8446 §1](https://www.rfc-editor.org/rfc/rfc8446.html#section-1)・[RFC 6750 §2.1](https://www.rfc-editor.org/rfc/rfc6750.html#section-2.1)・[RFC 9700 §4.3.2](https://www.rfc-editor.org/rfc/rfc9700.html#section-4.3.2)・[OWASP のログ記録指針](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html#data-to-exclude)
- 修理依頼のパス・入力・応答。[実行できる API の仕様書](openapi.yaml)・[FastAPI の実装](../package/app/main.py)・[入力モデル](../package/app/schemas.py)

[前へ　第2章　REST とリソース](02-rest.md) ｜ [目次](../README.md) ｜ [次へ　第4章　操作に合うメソッドを選ぶ](04-methods.md)
