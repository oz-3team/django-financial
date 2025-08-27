#!/bin/bash

# 에러 발생 시 스크립트 종료
set -e

# DB ready 대기
until pg_isready -h $POSTGRES_HOST -p $POSTGRES_PORT; do
  echo "Waiting for postgres..."
  sleep 1
done

echo "==== Django Migration Start ===="
uv run python manage.py migrate
echo "==== Django Migration Done ===="

echo "==== Starting Gunicorn with Uvicorn Worker ===="
uv run gunicorn \
    --bind 0.0.0.0:8000 \
    -k uvicorn.workers.UvicornWorker \
    config.asgi:application