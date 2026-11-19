FROM public.ecr.aws/lambda/python:3.12 AS runtime
# ベースの公開後に修正された Amazon Linux 2023 のパッケージも取り込む。
ARG AL2023_RELEASE=2023.12.20261112
RUN dnf --releasever=${AL2023_RELEASE} upgrade -y && dnf clean all

# uv.lock に記録した依存パッケージをここで準備し、実行用イメージにコピーする。
FROM runtime AS dependencies
COPY --from=ghcr.io/astral-sh/uv:0.10.0 /uv /usr/local/bin/uv
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project --no-cache --python /var/lang/bin/python3.12

FROM dependencies AS local
# Compose 用の段階には、実 HTTP を受ける uvicorn とテスト用の pytest も入れる。
RUN uv sync --locked --no-install-project --no-cache --python /var/lang/bin/python3.12
ENV PATH="/build/.venv/bin:${PATH}"
COPY package/app /build/package/app
COPY package/db /build/package/db
ENTRYPOINT []

FROM runtime
# エミュレーターはローカル用ステージに残す。AWS では Lambda の実行環境がイベントを渡す。
RUN rm -f /usr/local/bin/aws-lambda-rie
# DB に接続するとき、この認証局の証明書を使って Aurora のサーバー証明書を検証する。
ADD https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem /opt/rds-global-bundle.pem
RUN chmod 0444 /opt/rds-global-bundle.pem

COPY --from=dependencies /build/.venv/lib/python3.12/site-packages/ ${LAMBDA_TASK_ROOT}/
COPY package/app ${LAMBDA_TASK_ROOT}/package/app
COPY package/db ${LAMBDA_TASK_ROOT}/package/db
CMD ["package.app.main.handler"]
