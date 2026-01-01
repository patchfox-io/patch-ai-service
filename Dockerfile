# syntax=docker/dockerfile:1.7

FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg

# System deps: fonts for matplotlib (headless)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only pyproject first for better layer caching
COPY pyproject.toml ./pyproject.toml

# Generate requirements from [project.dependencies] to keep pyproject as the source of truth
RUN python - <<'PY' > requirements.txt
import tomllib
with open("pyproject.toml", "rb") as f:
    data = tomllib.load(f)
deps = data.get("project", {}).get("dependencies", [])
if not deps:
    raise SystemExit("No dependencies found in [project.dependencies].")
print("\n".join(deps))
PY

# Install runtime deps
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

# Copy the rest of the project (includes slackbot.py)
COPY . .

RUN chmod +x /app/entrypoint.sh

# Create and use a non-root user
RUN useradd --create-home appuser \
    && chown -R appuser:appuser /app
USER appuser

ENTRYPOINT ["/app/entrypoint.sh"]
