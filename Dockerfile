FROM python:3.11-slim
RUN pip install requests prometheus-client python-dotenv --no-cache-dir
WORKDIR /app