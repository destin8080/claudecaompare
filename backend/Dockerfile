# ---------------------------------------------------------------------------
# Compare Your Website — backend Dockerfile
#
# Uses the official Playwright Python image, which ships with Chromium and
# every system library it depends on already installed at the standard path
# (/ms-playwright/...). This avoids the apt vs Nix issues we hit on Railway
# with playwright install-deps.
#
# The image tag MUST match the playwright version in requirements.txt.
# ---------------------------------------------------------------------------
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

# Layer caching: install Python deps first, then copy code.
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Application code
COPY app ./app

# Railway / Render / Fly all inject $PORT; default to 8000 for local docker run.
ENV PORT=8000
EXPOSE 8000

# Shell form so ${PORT} is expanded at container start.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
