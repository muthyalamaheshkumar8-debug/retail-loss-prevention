FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*
COPY requirements*.txt ./
RUN pip install --no-cache-dir torch==2.7.0 torchvision==0.22.0 --index-url https://download.pytorch.org/whl/cpu && pip install --no-cache-dir -r requirements-cv.txt
COPY app ./app
RUN mkdir -p /data /app/models && useradd -m -u 10001 appuser && chown -R appuser:appuser /app /data
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
