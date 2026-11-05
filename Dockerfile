FROM python:3.12-slim

# Tesseract with Thai + English for scanned pages and images
RUN apt-get update \
 && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-tha tesseract-ocr-eng \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY docbridge ./docbridge
RUN pip install --no-cache-dir ".[api,ocr]"

ENV DOCBRIDGE_MAX_MB=25
EXPOSE 8000
CMD ["uvicorn", "docbridge.api:app", "--host", "0.0.0.0", "--port", "8000"]
