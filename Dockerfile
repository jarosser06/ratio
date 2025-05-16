# Image is passed as a build arg by the framework
ARG IMAGE
FROM $IMAGE

RUN poetry config virtualenvs.create false

ADD . ${LAMBDA_TASK_ROOT}/ratio
RUN rm -rf /var/task/ratio/.venv

RUN cd ${LAMBDA_TASK_ROOT}/ratio && poetry install --without dev
