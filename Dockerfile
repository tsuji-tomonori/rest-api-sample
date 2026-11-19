FROM public.ecr.aws/lambda/python:3.12 AS runtime

FROM runtime AS dependencies
COPY --from=ghcr.io/astral-sh/uv:0.10.0 /uv /usr/local/bin/uv
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project --no-cache --python /var/lang/bin/python3.12

FROM runtime
ADD https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem /opt/rds-global-bundle.pem
RUN chmod 0444 /opt/rds-global-bundle.pem

COPY --from=dependencies /build/.venv/lib/python3.12/site-packages/ ${LAMBDA_TASK_ROOT}/
COPY package/app ${LAMBDA_TASK_ROOT}/package/app
COPY package/db ${LAMBDA_TASK_ROOT}/package/db
CMD ["package.app.main.handler"]
