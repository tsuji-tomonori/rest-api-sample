# 第3章　パスとパラメータ

総務の担当者は、朝一番に未完了の依頼を見渡し、それから1件を開きます。この二つの操作を区別できるように、一覧と個別の依頼に宛先を付けましょう。

## 一覧と1件に宛先を付ける

HTTP では、対象を識別するために **URI** を使います。たとえば `https://example.com/repair-requests/42` では、`https` が通信方式、`example.com` がホスト名、その後の `/repair-requests/42` が **パス** です。以下の例ではホストまでを省き、パスから書きます。[RFC 3986 §3 URI の構成](https://www.rfc-editor.org/rfc/rfc3986.html#section-3)

| 読みたいもの | メソッドと宛先 |
| --- | --- |
| 修理依頼の一覧 | `GET /repair-requests` |
| 42番の修理依頼 | `GET /repair-requests/42` |
| 未完了の修理依頼を最大10件 | `GET /repair-requests?status=open&limit=10` |

この教材では、一覧に複数形の名詞を使い、1件を指すときは末尾に番号を加えます。番号は依頼を一意に指すため、件名が同じ依頼も区別できます。複数形は、対象の集まりを読み手に伝えるための命名規約です。RFC 3986 が定めるのは、パスを `/` で区切るといった URI の構文です。[RFC 3986 §3.3 Path](https://www.rfc-editor.org/rfc/rfc3986.html#section-3.3)・[Google AIP-122 の集合名に関する規約](https://google.aip.dev/122#collection-identifiers)

## 値を渡す場所を決める

仕様書の `/repair-requests/{request_id}` は宛先のひな型です。波かっこの部分を `42` など実際の番号に置き換えます。ここで渡す値が **パスパラメータ** です。`?` に続く部分は **クエリ** と呼びます。この API では `status=open` と `limit=10` を `&` でつなぎ、一覧の条件を渡します。[RFC 3986 §3.4 Query](https://www.rfc-editor.org/rfc/rfc3986.html#section-3.4)・[OpenAPI 3.1.1 Path Templating](https://spec.openapis.org/oas/v3.1.1.html#path-templating)

修理を依頼する社員は、件名と場所も渡します。そこで、宛先のほかに **本文** と **ヘッダー** を使います。本文は相手に届けるデータ、ヘッダーはその形式などを伝える付加情報です。たとえば `Content-Type: application/json` は「この本文を JSON として読んでください」という指定です。[RFC 9110 §6.3、§6.4、§8.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.3)

| 値の役割 | この API で置く場所 | 例 |
| --- | --- | --- |
| どの依頼か | パス | `/repair-requests/42` の `42` |
| どの範囲を読むか | クエリ | `status=open`、`limit=10`、続きの位置 `after=42` |
| 何を登録・変更するか | 本文 | 登録する件名と場所、または更新する状態 |
| 本文をどう解釈するか | ヘッダー | `Content-Type: application/json` |

一つの項目がいつも同じ場所に入るとは限りません。未完了の依頼を**探す**とき、`status=open` はクエリに入ります。完了に**変える**とき、`{"status":"completed"}` は変更内容なので本文に入ります。まず、その値を何のために使うかを文章にすると、置き場所を決めやすくなります。

仕様書を書くときにも、この区別が役立ちます。OpenAPI では、パスやクエリで受け取る値を `parameters` に記述します。本文とその形式は `requestBody` にまとめます。たとえば、この登録 API が受け付ける `application/json` は `requestBody` の `content` に書きます。パスパラメータは必須です。一覧の件数のように省略できる値には、省略したときの振る舞いも書きます。この API の `limit` は既定で20件です。[OpenAPI 3.1.1 Parameter Object](https://spec.openapis.org/oas/v3.1.1.html#parameter-object)・[Request Body Object](https://spec.openapis.org/oas/v3.1.1.html#request-body-object)

もう一つ、宛先はログや履歴にも残り得ます。たとえば認証用の秘密を受け取る API なら、URL への埋め込みは避け、採用する認証方式が定めるヘッダーなどで渡します。[RFC 9110 §17.9 URI に含まれる機密情報](https://www.rfc-editor.org/rfc/rfc9110.html#section-17.9)

[前へ　REST とリソース](02-rest.md) ・ [目次](../README.md) ・ [次へ　メソッドと再送](04-methods.md)
