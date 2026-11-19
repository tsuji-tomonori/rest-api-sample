# 教材とサンプルの保守

このページは、このリポジトリのコード、公開仕様書、教材を変更する人向けです。API の設計を始めるときは[設計シート](../templates/contract-sheet.md)、稼働中の API に障害が起きたときは[監視と復旧の手順](../build/operations.md)を開きます。

## 1. 変更の内容に合わせて CI の結果を読む

GitHub Actions の `Verify sample` は push とプルリクエスト、週次の定期実行で動きます。ローカルで再現するときは、リポジトリのルートでコマンドを実行します。テストの失敗は、最初に期待と違った箇所から調べます。

| 変更箇所 | 確かめること | 最初に見る結果 |
| --- | --- | --- |
| Python コード | Ruff がコード上の誤りやセキュリティ上の問題を、mypy が型の不整合を検出する | `uv run --locked --group infra ruff check package scripts tests`、`uv run --locked --group infra ruff check --select S package scripts`、`uv run --locked --group infra mypy` |
| GitHub Actions | actionlint がワークフローの構文や式を検査する | CI の `Validate CI and CD workflows` |
| メソッド・入力・レスポンス | YAML に書いた契約と実装が一致するか、登録や更新が DB に反映されるかを調べる | 公開仕様書の照合、単体テスト、SQLite と PostgreSQL を使った検査、Compose の結合・契約テスト |
| 配信手順 | 検証済みのコミットから配信し、DB 移行後に署名付き・署名なしのリクエストを送れるかを確かめる | CI の配信処理テストと CD の `aws-smoke-report`。実際の AWS 疎通は、対象の検査が `passed` なら成功 |

操作の契約を変えたら、ルート・入出力モデルと一緒に公開仕様書を更新します。下の1行目で生成し、差分を確認します。3行目の `--check` はファイルを書き換えず、現行コードの生成結果と一致するかを検査します。互換性の判定には、変更前の利用者が送っていた入力と期待結果も使います。[API のテスト設計](../build/testing.md)・[CI の定義](../../.github/workflows/verify.yml)・[CD の定義](../../.github/workflows/deploy.yml)

```console
uv run --locked python -m package.app.export_openapi docs/openapi.yaml
git diff -- docs/openapi.yaml
uv run --locked python -m package.app.export_openapi --check docs/openapi.yaml
```

## 2. 依存関係を更新し、脆弱性に対応する

Dependabot は uv、GitHub Actions、Docker の更新候補を毎週確認します。CI の pip-audit は、ロックした Python の実行・開発・テスト・構築用パッケージを既知の脆弱性と照合します。更新提案と脆弱性の通知のどちらでも、最初に利用箇所を特定します。たとえば FastAPI は社員からのリクエストを処理し、pytest はテストを実行するときに動きます。[Dependabot の設定](../../.github/dependabot.yml)・[依存関係の定義](../../pyproject.toml)・[pip-audit](https://github.com/pypa/pip-audit)

1. アドバイザリで、対象パッケージ、影響する版・使い方、修正版を確認します。使い方をコードと照合し、対応する担当者と期限を決めます。
2. 直接指定した版なら `pyproject.toml` を修正し、`uv lock` を実行します。間接依存なら `uv lock --upgrade-package パッケージ名` で更新します。
3. ロックファイルの差分をレビューし、監査と契約テストを再実行します。実行環境に含まれる依存を変えたら、イメージを配信し、対象環境の疎通結果を確認します。
4. 修正版がまだない場合は、影響する操作、暫定対策、再確認の期限を記録します。

## 3. 配布イメージと AWS 構成の差分を確かめる

CI は CDK が選んだビルド対象から Lambda イメージを作り、2つの関数のハンドラーを読み込みます。Trivy はそのイメージ内の OS とライブラリを調べ、修正版がある HIGH・CRITICAL の指摘で検査を失敗させます。Amazon Linux の更新が必要なら公式リリースノートで修正を確認し、Dockerfile の `AL2023_RELEASE` を更新して、作り直したイメージを再検査します。[Dockerfile](../../Dockerfile)・[Trivy のイメージ検査](https://trivy.dev/docs/latest/target/container_image/)・[Amazon Linux のリリースノート](https://docs.aws.amazon.com/linux/al2023/release-notes/)

インフラは `uv run --locked --group infra python -m pytest -q tests/infra` で検査します。新しい NAT Gateway、必須タグの欠落、Aurora の容量変更などは、合成したテンプレートのアサーションで確認します。cdk-nag の指摘は AWS Solutions ルールとリソースの組で調べ、教材に残す場合は理由も記録します。テンプレート全体のスナップショットには、IAM 権限やネットワークの差分も現れます。更新前に、意図した変更と差分が一致するかをレビューしてください。[構築手順と費用の前提](../../package/infra/README.md)・[アサーションとスナップショット](../../tests/infra)・[例外の理由](../../tests/infra/nag-exceptions.yaml)

## 4. 教材を更新したときの確認

| 伝えたいこと | 記載する場所と書き方 |
| --- | --- |
| 業務が変わっても使える知識 | 教科書に、定義、選択肢、選ぶ基準、よくある誤り、根拠を書く。具体例は原則の違いが分かる短いものに絞る |
| ある要望に対する判断 | 実例編に、要望、候補、採用した理由、条件が変わる場合、設計シートの記入結果を書く。確認用の操作は末尾に置く |
| 読者が自分の業務で決めること | シートに、空欄、選択肢、記入後に判断できる確認項目を置く。対応する教科書・実例の章番号をそろえる |
| 実際に動かす手順と保守 | 起動・配信・運用は実装ガイドへ、教材の検査・依存更新はこのページへ案内する |

パス・メソッド・HTTP ステータスを書くときは、公開 YAML と実装の表記を使います。用語の意味は[用語集](../glossary.md)にそろえます。知識の根拠は RFC や公式仕様の該当箇所へ、サンプルの挙動はコードまたはテストへリンクします。

次の検査では、教材内の相対リンクと仕様書の YAML 抜粋を確かめます。章を移したときは、README の入口から同じ番号の教科書・実例・シートの欄へ行き来できるかも確認します。図やコードブロックの表示は GitHub のプレビューで見直します。

```console
uv run --locked python -m pytest -q tests/unit/test_book_links.py tests/unit/test_book_openapi.py
```

[教材の目次](../../README.md)
