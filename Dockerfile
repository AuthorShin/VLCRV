# ---- Build stage: install dependencies with Python 3.13 to match the
#      interpreter shipped in the distroless runtime image (ABI-compatible
#      wheels, e.g. pydantic-core). ------------------------------------------
FROM python:3.13-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /src

COPY requirements.txt .
RUN pip install --no-cache-dir --target=/install/packages -r requirements.txt

# Runtime config dir, pre-owned by the nonroot UID (65532) used below.
RUN mkdir -p /install/data && chown -R 65532:65532 /install/data

# ---- Runtime stage: no shell, no package manager, no source build tools. ---
FROM gcr.io/distroless/python3-debian13:nonroot

ENV PYTHONPATH=/app/packages \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=build --chown=65532:65532 /install/packages /app/packages
COPY --from=build --chown=65532:65532 /install/data /app/data
COPY --chown=65532:65532 . .

EXPOSE 8004

# Distroless entrypoint is /usr/bin/python3.13, so this runs `python run.py`.
CMD ["run.py"]
