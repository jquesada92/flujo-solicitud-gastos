FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY scripts ./scripts
COPY app ./app

# Windows checkouts can materialize shell scripts with CRLF even when the Git
# blob is LF. Normalize inside the Linux image as a second line of defense so
# the shebang remains /bin/sh instead of /bin/sh\r.
RUN find /app/scripts -type f -name '*.sh' -exec sed -i 's/\r$//' {} + \
    && chmod +x /app/scripts/*.sh

EXPOSE 8000

CMD ["/app/scripts/start.sh"]
