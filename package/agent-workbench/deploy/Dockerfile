# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm
WORKDIR /app
COPY requirements.lock /app/requirements.lock
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    python -m pip install --no-cache-dir --require-hashes -r /app/requirements.lock
RUN useradd --create-home --uid 1000 workbench && \
    mkdir -p /data/artifacts /data/config && chown -R 1000:1000 /data
USER workbench
ENV OMNIGENT_CONFIG_HOME=/data/config \
    OMNIGENT_ADMIN_CREDENTIALS_PATH=/data/admin-credentials \
    OMNIGENT_AUTH_ENABLED=1 \
    OMNIGENT_AUTH_PROVIDER=accounts \
    OMNIGENT_ACCOUNTS_INIT_ADMIN_USERNAME=admin \
    OMNIGENT_ACCOUNTS_AUTO_OPEN=0
EXPOSE 6767
CMD ["omnigent", "server", "--host", "0.0.0.0", "--port", "6767", "--database-uri", "sqlite:////data/chat.db", "--artifact-location", "/data/artifacts", "--no-open"]
