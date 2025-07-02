ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim as base
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser
RUN pip install --no-cache-dir -r requirements.txt
USER appuser
COPY . .
EXPOSE 8000
CMD uvicorn 'main:app' --host=0.0.0.0 --port=8000