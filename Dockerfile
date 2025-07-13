FROM python:3.10-slim

WORKDIR /app

# Установка зависимостей для afick
RUN apt-get update && apt-get install -y --no-install-recommends \
    afick \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Установка pipenv
RUN pip install --no-cache-dir pipenv

COPY . /app

RUN pipenv install --deploy --ignore-pipfile

# Инициализация базы afick
RUN mkdir -p /var/lib/afick && \
    afick --init

EXPOSE 8000

CMD ["pipenv", "run", "uvicorn", "app.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]