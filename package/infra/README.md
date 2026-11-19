# 修理依頼 API のデプロイ

各サービスの役割と、接続に必要な設定は[第9章](../../docs/09-aws.md)で説明しています。ここでは Python CDK の操作だけを示します。コマンドは Bash 用です。デプロイには AWS CLI の認証情報、CDK CLI、Docker を使います。

## スタックを作成する

リポジトリのルートから実行します。最初に表示された AWS アカウントとロール、`cdk diff` の変更内容を確認してください。対象リージョンへの初回デプロイには [CDK のブートストラップ](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html)が必要です。

```bash
export AWS_REGION=ap-northeast-1
export BUILDX_NO_DEFAULT_ATTESTATIONS=1
aws sts get-caller-identity
uv sync --locked --group infra
cd package/infra
cdk diff RepairApi
cdk deploy RepairApi
```

Aurora のバージョンは [cdk.json](cdk.json) の `auroraVersion` で指定します。デプロイ先で作成できる PostgreSQL 17 系のバージョンを選んでください。[Aurora Serverless v2 の対応状況](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.requirements.html)

## テーブルを用意し、API を呼ぶ

出力された `MigrateFunction` の関数名を使います。初回とテーブル定義を変更したときに実行します。

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

新しい台帳では `200` と `{"items":[],"next_after":null}` が返ります。デプロイ後は、Aurora の自動停止中もストレージ、VPC エンドポイント、シークレットなどに料金が発生します。環境が不要になったら `package/infra` で `cdk destroy RepairApi` を実行します。**スタックを削除すると修理依頼のデータも削除されます。** ブートストラップ用のスタックとイメージは別に管理されます。[Aurora の自動停止](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2-auto-pause.html)・[PrivateLink の料金](https://aws.amazon.com/privatelink/pricing/)・[Secrets Manager の料金](https://aws.amazon.com/secrets-manager/pricing/)

## GitHub Actions から継続的にデプロイする

[Deploy to AWS](../../.github/workflows/deploy.yml) は、`main` への push に対する `Verify sample` が成功したときに動きます。検証が通ったコミットをチェックアウトし、CDK のデプロイ、DB マイグレーション、署名付き `GET /repair-requests?limit=1` の順で確認します。GET は返った1ページをアプリの応答モデルと照合します。修理依頼の登録や削除は行いません。

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
