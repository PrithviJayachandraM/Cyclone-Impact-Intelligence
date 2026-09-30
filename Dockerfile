FROM python:3.11-slim

WORKDIR /app
COPY src /app/src
COPY web /app/web
COPY data /app/data
ENV PYTHONPATH=/app/src
ENV APP_HOST=0.0.0.0
ENV PORT=8080
EXPOSE 8080
CMD ["python", "-m", "cyclone.main"]
