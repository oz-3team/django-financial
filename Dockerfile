# 1단계: 빌드 스테이지 (uv 바이너리 복사)
FROM python:3.13-slim AS builder

# uv 공식 이미지에서 바이너리 복사
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# 의존성 파일 복사
COPY pyproject.toml uv.lock ./

# 의존성 설치 (uv 실행 가능)
# --no-install-project 플래그는 pyproject.toml에 명시된 프로젝트 자체는 설치하지 않고, 
# 명시된 의존성만 설치하도록 합니다.
RUN uv sync --all-packages --no-install-project

# 전체 프로젝트 복사
COPY . .

# app 및 의존성 완성
RUN uv sync --all-packages


# 2단계: 실제 실행 이미지
FROM python:3.13-slim

WORKDIR /app

# 빌드 스테이지에서 완성된 /app 폴더 복사
COPY --from=builder /app /app
COPY ./scripts /scripts

# [수정] Windows의 CRLF 줄 끝을 Linux의 LF로 변환
RUN sed -i 's/$//' /scripts/run.sh
RUN chmod +x /scripts/run.sh

# PATH에 앱의 가상환경 포함 (uv가 설치한 가상환경)
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# 시작 명령
CMD ["/scripts/run.sh"]