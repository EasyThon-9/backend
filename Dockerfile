# Python 3.13.1 slim 이미지 사용
FROM python:3.13.1-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 필요한 기본 도구 설치
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates build-essential \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉터리 설정
WORKDIR /app

# Python 의존성 파일 복사
COPY requirements.txt /tmp/requirements.txt

# pip 기반으로 의존성 설치
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir gunicorn \
    && pip install --no-cache-dir langchain-community==0.3.12 numpy==1.26.4

# 애플리케이션 코드 복사
COPY . .

EXPOSE 8000

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
