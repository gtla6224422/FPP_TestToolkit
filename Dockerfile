FROM node:20-alpine AS frontend-builder

WORKDIR /workspace/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.8-slim

WORKDIR /app/backend

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_DEBUG=0
ENV REDIS_ENABLED=0

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -i https://repo.huaweicloud.com/repository/pypi/simple

COPY backend/app ./app
COPY backend/run.py ./run.py
COPY backend/code_set.txt ./code_set.txt
COPY backend/test_case ./test_case
COPY --from=frontend-builder /workspace/frontend/dist /app/frontend/dist

EXPOSE 5003

CMD ["python", "run.py"]
