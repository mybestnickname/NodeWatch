FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir pipenv

COPY . /app

RUN pipenv install --deploy --ignore-pipfile

EXPOSE 8000

CMD ["pipenv", "run", "uvicorn", "app.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]