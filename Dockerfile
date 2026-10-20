FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY forest_archive/ ./forest_archive/

RUN mkdir -p /app/data

CMD ["python", "-m", "src.bot.main"]
