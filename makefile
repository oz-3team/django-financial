.PHONY: run migrate lint test docker uv docker-up docker-down docker-logs

# Django 마이그레이션
migrate:
	python manage.py migrate

# Django 개발 서버 실행 (ASGI)
uv:
	uvicorn config.asgi:application --reload

# 코드 스타일/문법 검사 (ruff)
ruff:
	ruff check .

# 테스트 실행
test:
	pytest

# Docker 이미지 빌드 후 컨테이너 실행
docker-up:
	docker-compose up --build -d

# Docker 컨테이너 정지
docker-down:
	docker-compose down

# Docker 컨테이너 로그 확인
docker-logs:
	docker-compose logs -f
