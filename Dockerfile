FROM python:3.8

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

COPY . .

EXPOSE 5003

ENV FLASK_DEBUG=0
ENV REDIS_ENABLED=0

CMD ["python", "run.py"]
