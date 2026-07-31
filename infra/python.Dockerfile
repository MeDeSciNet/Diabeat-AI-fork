# One image for every Python service: SIM, ING (api/consumer/worker) and PAM.
# They share the analysis code, so separate images would mean separate builds of
# the same dependency tree for no isolation benefit.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY packages/shared-schemas /app/packages/shared-schemas
COPY packages/sim /app/packages/sim
COPY packages/ing /app/packages/ing
COPY packages/pam /app/packages/pam

RUN pip install --no-cache-dir \
      -e packages/shared-schemas \
      -e packages/sim \
      -e packages/ing \
      -e packages/pam

RUN useradd --create-home --uid 10001 somno && chown -R somno /app
USER somno

CMD ["somno-ing", "serve"]
