FROM python:3.8-slim-buster

WORKDIR /brightsky

ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=1

COPY requirements.txt setup.py ./

RUN pip install -r requirements.txt

COPY brightsky brightsky
COPY migrations migrations

RUN pip install .

ENTRYPOINT ["python", "-m", "brightsky"]
