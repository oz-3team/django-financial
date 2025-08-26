FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# uv 설치
RUN pip install uv

# 작업 디렉토리
WORKDIR /app

# 의존성 파일 복사
COPY pyproject.toml uv.lock ./

# 패키지 설치
RUN uv sync --all-packages

# 프로젝트 소스 복사
COPY . .

# 스크립트 복사 + 권한
COPY ./scripts /scripts
RUN chmod +x /scripts/run.sh

# 포트 노출
EXPOSE 8000

# 컨테이너 시작 시 run.sh 실행
CMD ["/scripts/run.sh"]



# 도커이미지 만들기
# docker build -t django-financial .


# 멈추고 지운 다음 다시 생성 + 시작하기
# docker stop django-financial
# docker rm django-financial
# docker run -d -p 8000:8000 --name django-financial django-financial