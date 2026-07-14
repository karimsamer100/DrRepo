FROM python:3.12.8-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_INPUT=1

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin drrepo \
    && python -m pip install --no-cache-dir "pytest>=8" "coverage>=7"

WORKDIR /workspace
COPY runner.py /opt/drrepo/runner.py
RUN chmod 0555 /opt/drrepo/runner.py

USER 10001:10001
ENTRYPOINT ["python", "/opt/drrepo/runner.py"]
