# 実装編　設計した操作を Python で動かす

会議室の椅子が壊れたとき、社員は修理を依頼し、総務は別の端末でその依頼を開きます。両方の端末から同じ台帳を使うには、共通の受付と保存先が必要です。

## コードを書く前に、アプリをどこで動かすかを知る

アプリを動かすコンピューターやデータの保存先を、必要なときにネットワーク越しに使う仕組みを**クラウド**と呼びます。このサンプルの公開先は、Amazon のクラウドサービス **AWS** です。利用者からの呼び出しを受ける入口を **API Gateway**、コードを動かす役を **Lambda**、台帳を保管する役をデータベースの **Aurora** が受け持ちます。[受付から保存までを図で見る](architecture.md)

手元では、まず自分の端末だけで「受付番号から1件を開く」処理を動かせます。

## 1ファイルで詳細取得を作る

Python 3.12 と uv を使います。リポジトリをダウンロードまたはクローンし、`pyproject.toml` があるフォルダーを端末で開きます。初めて uv を使う場合は[公式のインストール手順](https://docs.astral.sh/uv/getting-started/installation/)を参照してください。

次のコードをそのフォルダーに `first_route.py` として保存します。この小さな例で扱うデータは、42番の依頼1件です。

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


class Repair(BaseModel):
    id: int
    title: str


app = FastAPI()


@app.get("/repair-requests/{request_id}")
def get_repair(request_id: int) -> Repair:
    if request_id != 42:
        raise HTTPException(status_code=404, detail="修理依頼が見つかりません。")
    return Repair(id=42, title="椅子がぐらつく")
```

`@app.get(...)` が HTTP のメソッドとパスを関数に結び付けます。パスの `{request_id}` と引数の名前を合わせると、FastAPI は URL の番号を整数として渡します。`-> Repair` は成功時に返す項目と型を示します。

```console
uv run --locked uvicorn first_route:app --port 8001
```

起動した端末を開いたまま、別の端末で次の2行を実行します。Windows PowerShell では `curl.exe` を使います。

```console
curl -i http://127.0.0.1:8001/repair-requests/42
curl -i http://127.0.0.1:8001/repair-requests/43
```

42番には `200` と `{"id":42,"title":"椅子がぐらつく"}`、43番には `404` が返ります。確認したら、起動した端末で Ctrl+C を押して終了できます。完成版では番号を DB で検索し、見つからなければ共通のエラー形式で返します。その実装は下の02と05で読めます。

## 設計した内容から実装箇所を引く

| 章 | 設計をコードにする作業 |
| --- | --- |
| [01　API と HTTP](01-http.md) | 同じリクエストが、手元では Uvicorn、AWS では API Gateway と Lambda を通って FastAPI に届く経路を確かめる |
| [02　リソース](02-resources.md) | 依頼1件をテーブルの1行にし、受付番号を主キーとして読み直す |
| [03　入力](03-inputs.md) | パスの番号とクエリの件数を関数の引数に、登録する件名と場所を本文のモデルに書く |
| [04　メソッド](04-methods.md) | 同じ宛先でも、照会・更新・削除で呼ばれる関数を分ける |
| [05　レスポンス](05-responses.md) | 成功のステータス、作成先のヘッダー、共通のエラー本文を返す |
| [06　操作の契約](06-contract.md) | 保存を確定する場所と、許可された操作・失敗時の状態を検証する場所を特定する |
| [07　OpenAPI](07-openapi.md) | ルートと型の宣言から YAML を生成し、公開仕様書と実装を照合する |
| [08　互換性](08-compatibility.md) | 以前の呼び出しをテストに残し、変更後も同じ使い方ができるか調べる |

**一つの変更を最後まで書く場合**は、[一覧に場所の絞り込みを加える](first-operation.md)に進んでください。自分の作業コピーで、引数の追加、DB の検索条件、期待結果のテスト、公開 YAML の更新を順に行えます。

[教材の目次](../../README.md) ｜ [設計シート](../templates/contract-sheet.md) ｜ [AWS の構築手順](../build/aws.md)
