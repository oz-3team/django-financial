# 1. 베이스 이미지 설정 (Python 3.13)
# pyproject.toml에 명시된 파이썬 버전에 맞춰 이미지를 선택합니다.
FROM python:3.13-slim

# 2. 환경 변수 설정
# 파이썬이 .pyc 파일을 만들지 않도록 하고, 로그 출력이 버퍼링 없이 바로 표시되도록 합니다.
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. uv 설치
# 경량화된 패키지 설치 도구인 uv를 설치합니다.
RUN pip install uv

# 4. 작업 디렉토리 설정
# 컨테이너 내에서 애플리케이션이 실행될 기본 디렉토리를 설정합니다.
WORKDIR /app

# 5. 의존성 파일 복사
# 먼저 의존성 관련 파일만 복사하여 Docker 빌드 캐시를 효율적으로 활용합니다.
COPY pyproject.toml uv.lock ./

# 6. 의존성 설치
# uv sync 명령어를 사용하여 uv.lock 파일 기준으로 의존성을 설치합니다.
# --no-dev 플래그로 개발용 패키지는 제외합니다.
RUN uv pip sync --no-dev

# 7. 프로젝트 소스 코드 복사
# 나머지 모든 소스 코드를 작업 디렉토리로 복사합니다.
COPY . .

# 8. 포트 노출
# Django 애플리케이션이 실행될 8000번 포트를 외부에 노출합니다.
EXPOSE 8000

# 9. Gunicorn과 Uvicorn 워커를 사용하여 애플리케이션 실행
# Gunicorn이 Uvicorn 워커를 사용하여 ASGI 모드로 애플리케이션을 실행합니다.
# config.asgi:application는 프로젝트의 ASGI 애플리케이션 위치를 나타냅니다.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-k", "uvicorn.workers.UvicornWorker", "config.asgi:application"]
