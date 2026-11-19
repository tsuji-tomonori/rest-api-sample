# 修理依頼 API のデプロイ

第10章で組み立てた API Gateway、Lambda、Aurora を AWS に配置します。手元から構築するときは「スタックを作成する」から、GitHub から自動配信するときは「GitHub Actions から継続的にデプロイする」から読みます。どちらも、スタックを適用し、DB を移行してから、公開 URL で一覧を取得する流れです。[構成と接続設定](../../docs/10-aws.md)

## スタックを作成する

次のコマンドは Bash 用です。認証済みの AWS CLI、uv、CDK CLI、Docker を使い、リポジトリのルートから実行します。`cdk synth` はテンプレートを生成し、`cdk diff` はデプロイ済みのスタックとの差分を示します。表示されたアカウント、ロール、差分を確認してから `cdk deploy` で適用してください。対象アカウント・リージョンへの初回デプロイにはブートストラップが必要です。[CDK のデプロイ](https://docs.aws.amazon.com/cdk/v2/guide/deploy.html)・[ブートストラップ](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html)

```bash
export AWS_REGION=ap-northeast-1
export BUILDX_NO_DEFAULT_ATTESTATIONS=1
aws sts get-caller-identity
uv sync --locked --group infra
cd package/infra
cdk synth RepairApi --no-lookups --quiet
cdk diff RepairApi
cdk deploy RepairApi --outputs-file cdk.out/repair-outputs.json
```

Aurora のバージョンは [cdk.json](cdk.json) の `auroraVersion` で指定します。デプロイ先で作成できる PostgreSQL 17 系のバージョンを選んでください。[Aurora Serverless v2 の対応状況](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.requirements.html)

## テーブルを用意し、API を呼ぶ

出力ファイル `cdk.out/repair-outputs.json` の `RepairApi` に、次の操作で使う値が入ります。`MigrateFunction` は移行用 Lambda の名前、`ApiUrl` は公開 URL、`InvokeArn` は API の呼び出しを許可する対象です。まず移行用 Lambda を実行します。初回は修理依頼のテーブルが作られ、更新時は未適用の変更が反映されます。

```bash
MIGRATE='MigrateFunction の値'
aws lambda invoke --function-name "$MIGRATE" --cli-read-timeout 150 \
  --payload '{}' --cli-binary-format raw-in-base64-out cdk.out/migration.json
cat cdk.out/migration.json
```

`FunctionError` がなく、ファイルに `{"migration":"up-to-date"}` が返ればテーブルの準備は完了です。API を利用するロールには、出力された `InvokeArn` に対する `execute-api:Invoke` を許可します。次は一時認証情報を設定した AWS CLI プロファイルで、最初の一覧を読む例です。[API Gateway の IAM 認可](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-access-control-iam.html)

```bash
API='ApiUrl の値'
(
  source <(aws configure export-credentials --format env)
  curl --silent --show-error --include --config - "$API/repair-requests" <<SIGN
aws-sigv4 = "aws:amz:$AWS_REGION:execute-api"
user = "$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY"
header = "x-amz-security-token: $AWS_SESSION_TOKEN"
SIGN
)
```

新しい台帳では `200` と `{"items":[],"next_after":null}` が返ります。公開 URL から権限を確認し、API 用 Lambda を経て Aurora の一覧を読み取れた状態です。

## GitHub Actions から継続的にデプロイする

[Deploy to AWS](../../.github/workflows/deploy.yml) は、`main` への push に対する `Verify sample` が成功したときに動きます。検証が通ったコミットをチェックアウトし、CDK のデプロイ、DB マイグレーション、公開 URL からの疎通確認を順番に実行します。疎通確認には GET を使うので、既存の修理依頼をそのまま使えます。

### 初回に用意するもの

1. **デプロイ先を準備する。** AWS の対象アカウント・リージョンで CDK をブートストラップします。`aws sts get-caller-identity` でアカウントを確認したうえで、管理者が `cdk bootstrap aws://ACCOUNT_ID/REGION` を実行します。[AWS CDK のブートストラップ](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping-env.html)
2. **GitHub のデプロイ環境を作る。** リポジトリの Settings → Environments で環境 `aws` を作り、Deployment branches and tags を `main` ブランチに限定します。運用で承認が必要なときは、この環境の保護ルールで設定できます。[GitHub のデプロイ環境](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
3. **AWS に OIDC プロバイダーと IAM ロールを用意する。** プロバイダーの URL は `https://token.actions.githubusercontent.com`、対象者（audience）は `sts.amazonaws.com` です。ロールの信頼ポリシーでは、このプロバイダーからの `sts:AssumeRoleWithWebIdentity` を許可し、`aud` と `sub` を下記の値に完全一致させます。GitHub が一時認証情報を受け取るため、アクセスキーの登録は不要です。[GitHub と AWS の OIDC 設定](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws)
4. **権限を付けて自動配信を有効にする。** デプロイ用ロールには、対象アカウント・リージョンの CDK ブートストラップ用ロール（デプロイ・ファイル発行・イメージ発行）への `sts:AssumeRole` を許可します。CloudFormation の実行ロールには、スタックのリソースを管理し、デプロイ用ロールにこのスタックの実行確認用インラインポリシーを設定・更新・削除できる権限が必要です。GitHub の Settings → Secrets and variables → Actions → **Variables** に `AWS_REGION` を設定し、最後に `AWS_ROLE_ARN` にデプロイ用ロールの ARN を設定します。`AWS_ROLE_ARN` が未設定の間は CD をスキップします。[ブートストラップ用ロールの役割](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping-env.html)

| OIDC 信頼条件（`StringEquals`） | 値 |
| --- | --- |
| `token.actions.githubusercontent.com:aud` | `sts.amazonaws.com` |
| `token.actions.githubusercontent.com:sub` | ID 入りの形式は `repo:OWNER@OWNER_ID/REPO@REPO_ID:environment:aws`。従来形式を使うリポジトリは `repo:OWNER/REPO:environment:aws`。対象リポジトリが実際に発行する形式を1つ指定 |

所有者とリポジトリの ID は `gh api repos/OWNER/REPO --jq '[.owner.id,.id]'` で確認できます。環境名が `sub` に入るため、ブランチの制限は手順2の環境設定で行います。[GitHub の subject 形式](https://docs.github.com/en/actions/reference/security/oidc#immutable-subject-claims)

### 実行結果を読む

CI が成功したときと、デプロイの順番が来たときに、検証した SHA が `main` の先頭と一致するか確かめます。新しいコミットが先頭にあれば、古いコミットの配信をスキップします。稼働中のデプロイは中断せず、後続の配信と重ならないようにしています。[GitHub の workflow_run](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run) ・ [同時実行制御](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)

CDK は `DeploymentRoleName` を受け取り、今回のマイグレーション関数と API への呼び出し権限をデプロイ用ロールに付与します。マイグレーションの例外、完了を示す応答の欠落、一覧取得の失敗は、いずれもジョブの失敗として記録します。CloudFormation の適用後にマイグレーションや疎通確認で失敗した場合、スタックそのものは更新済みです。AWS 側の設定を直したら、現在の `main` の成功した push に対応する `Verify sample` を再実行できます。コードを直す場合は `main` への反映で検証からやり直します。[配信後の確認コード](post_deploy.py)

### AWS の疎通結果を確認する

Actions の **Deploy to AWS** を開き、ジョブ概要「AWS 実環境の疎通確認」を読みます。実行ページの **Artifacts → aws-smoke-report** に入った `aws-smoke.json` には、検査ごとの期待・実測 HTTP コード、試行回数、所要時間（ミリ秒）、失敗理由が記録されます。記録には認証情報や修理依頼の内容を含めません。[GitHub Actions の実行概要](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#adding-a-job-summary)・[実行結果の保存](https://docs.github.com/en/actions/tutorials/store-and-share-data)

| 検査 ID | 呼び出しと期待する結果 | 確認する範囲 |
| --- | --- | --- |
| `migration` | 移行用 Lambda を同期実行して HTTP 200。関数内の例外がなく、完了応答が返る | Aurora 上のテーブルと API 用 DB ユーザーの準備 |
| `iam` | 署名を付けずに一覧を取得して 403 | 公開 URL が未署名の要求を拒否する |
| `list` | SigV4 署名付き `GET /repair-requests?limit=1` が 200。JSON が一覧モデルに合い、0件または1件返る | API Gateway から API 用 Lambda を経て Aurora を読む経路。空の DB でも確認できる |
| `invalid_limit` | 署名付きで `limit=0` を送って 422。応答は `application/problem+json` で、本文の `status` も 422 | FastAPI の入力検証結果が Gateway を経て利用者に届く経路 |

検査が途中で失敗すると CD は失敗し、実行済みの結果と後続の `not_run` を保存します。デプロイ先が未設定の場合は、全体が `not_run`、理由が `aws_target_not_configured` です。スタック更新に失敗した場合は `deployment_failed` と記録します。

すでに構築した環境では、リポジトリのルートから次のコマンドで3つの HTTP 検査だけを再実行できます。上の `cdk deploy --outputs-file` が生成したファイルと、対象 API を呼べる AWS プロファイルを使います。テストが1つでも失敗すると終了コードは 1 です。

```bash
export AWS_DEFAULT_REGION=ap-northeast-1
uv run --locked python -m package.infra.post_deploy package/infra/cdk.out/repair-outputs.json \
  --smoke-only --report package/infra/cdk.out/aws-smoke.json
```

## 運用担当に引き継ぐ

対象の AWS アカウント・リージョン、スタック名 `RepairApi`、公開 URL、配信したコミット、直近の疎通結果を共有します。疎通結果にあるのはデプロイ時点の記録です。業務フローや OpenAPI 契約の判定基準は第11章で確認できます。[第11章　API のテストを組み立てる](../../docs/11-testing.md)

障害調査には CloudFormation のスタックの「リソース」から、API 用・移行用 Lambda をたどれます。各関数の「モニタリング」から実行ログを開きます。CDK は関数ごとにロググループを作り、7日間保存します。稼働中に追うメトリクスと通知の設計、次のバージョンへ切り替えるときの判断は、運用の章で説明します。[第12章　API の運用と監視を始める](../../docs/12-operations.md)・[第13章　API のバージョンを上げる](../../docs/13-versioning.md)

## 検証環境の利用を終える

Aurora の自動停止中もストレージ、VPC エンドポイント、シークレットなどに料金が発生します。サンプルはスタックと一緒に DB を削除する設定です。**修理依頼のデータを含めて廃棄する環境**であることを確認してから、`package/infra` で `cdk destroy RepairApi` を実行してください。ブートストラップ用のスタックとイメージは別に管理されます。[Aurora の自動停止](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2-auto-pause.html)・[PrivateLink の料金](https://aws.amazon.com/privatelink/pricing/)・[Secrets Manager の料金](https://aws.amazon.com/secrets-manager/pricing/)
