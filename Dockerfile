FROM python:3.9.6-slim-buster
RUN python -m pip install --upgrade pip \
 && pip --no-cache-dir install pipenv
ENV PIPENV_VENV_IN_PROJECT=1
WORKDIR /workspace
# COPY ./Pipfile ./Pipfile.lock /workspace/
# RUN pipenv install --deploy --dev
COPY . /workspace
ENTRYPOINT [ "pipenv", "run" ]
CMD ["pytest"]
