FROM python:3.11-alpine

RUN apk update && apk add --no-cache build-base libffi-dev openssl-dev postgresql-dev

COPY . /app
WORKDIR /app

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
