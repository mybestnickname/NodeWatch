FROM python:3.10-slim

WORKDIR /app

# Install afick (the file-integrity engine) and its runtime dependencies.
RUN apt-get update && apt-get install -y --no-install-recommends \
    afick \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install pipenv.
RUN pip install --no-cache-dir pipenv

COPY . /app

RUN pipenv install --deploy --ignore-pipfile

# Initialise the afick baseline database.
RUN mkdir -p /var/lib/afick && \
    afick --init

# Default configuration path (override by mounting your own config).
ENV NODEWATCH_CONFIG=/app/config.example.json

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request,sys; \
    sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/nodewatch/v1alpha1/health').status==200 else 1)"

CMD ["pipenv", "run", "uvicorn", "app.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
