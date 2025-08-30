# 1단계: 빌드 스테이지 (uv 바이너리 복사)
FROM python:3.13-slim AS builder

# uv 공식 이미지에서 바이너리 복사
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# 의존성 파일 복사
COPY pyproject.toml uv.lock ./

# 의존성 설치 (uv 실행 가능)
RUN uv sync --all-packages --no-install-project

# 전체 프로젝트 복사
COPY . .

# 프로젝트 및 의존성 완성
RUN uv sync --all-packages

# 2단계: 실제 실행 이미지
FROM python:3.13-slim

# PostgreSQL client 설치 (pg_isready 포함)
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 빌드 스테이지에서 완성된 /app 폴더 복사
COPY --from=builder /app /app
COPY --from=builder /bin/uv /bin/uv
COPY ./scripts /scripts

# 실행 스크립트 권한 설정
RUN chmod +x /scripts/run.sh

# uv 환경 PATH
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["/scripts/run.sh"]

# 도커이미지 만들기
# docker build -t django-financial .


# 멈추고 지운 다음 다시 생성 + 시작하기
# docker stop django-financial
# docker rm django-financial
# docker run -d -p 8000:8000 --name django-financial django-financial
