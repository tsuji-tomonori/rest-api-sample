FROM public.ecr.aws/lambda/python:3.12

ADD https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem /opt/rds-global-bundle.pem
RUN chmod 0444 /opt/rds-global-bundle.pem

COPY package/app/requirements.txt /tmp/requirements-app.txt
COPY package/db/requirements.txt /tmp/requirements-db.txt
RUN python -m pip install --no-cache-dir --target "${LAMBDA_TASK_ROOT}" \
    -r /tmp/requirements-app.txt -r /tmp/requirements-db.txt

COPY package/app ${LAMBDA_TASK_ROOT}/package/app
COPY package/db ${LAMBDA_TASK_ROOT}/package/db
CMD ["package.app.main.handler"]
