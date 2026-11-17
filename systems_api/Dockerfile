# SystemsAPI: one image for the web app (pserve) and the EDDN ingester.
# Build context: this directory (systems_api/). Config comes from /data at run time;
# deploy/compose.yml runs it with host networking and an init process (see deploy/README.md).
# python:3.12-slim (3.12.16-slim-trixie, pip 25.0.1), multi-arch index digest read 2026-11-12 (same as JIRAAnnouncer and FIDO).
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_ROOT_USER_ACTION=ignore
WORKDIR /app
COPY requirements.txt .
# The sdist-only pyramid_settings_wrapper needs setuptools<81 in its isolated build, and pyramid 2.1
# and deform need pkg_resources at run time. PIP_CONSTRAINT reaches build environments up to pip 26.1,
# PIP_BUILD_CONSTRAINT from pip 26.2 on; both are set so a base-image bump keeps working.
RUN PIP_CONSTRAINT=/app/requirements.txt PIP_BUILD_CONSTRAINT=/app/requirements.txt pip install --no-cache-dir -r requirements.txt
COPY . .
RUN PIP_CONSTRAINT=/app/requirements.txt PIP_BUILD_CONSTRAINT=/app/requirements.txt pip install --no-cache-dir --no-deps . \
 && pip check \
 && python -c "import systems_api, systems_api.eddn_client, waitress, zmq, psycopg2" \
 && rm -rf /app
WORKDIR /data
USER 1000:1000
EXPOSE 6543
CMD ["pserve", "/data/run.ini"]
