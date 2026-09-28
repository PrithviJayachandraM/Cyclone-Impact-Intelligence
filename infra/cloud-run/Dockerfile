FROM python:3.11-slim

WORKDIR /app
COPY src /app/src
COPY web /app/web
COPY data/normalized /app/data/normalized
COPY data/enriched /app/data/enriched
COPY data/risk /app/data/risk
ENV PYTHONPATH=/app/src
ENV PORT=8080
EXPOSE 8080
CMD ["python", "-m", "cyclone.main"]
