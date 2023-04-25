# Task management system [demo]

## Stack

 - Django and Django Rest Framework (DRF)
 - Celery
 - PostgreSQL
 - RabbitMQ
 - Redis

## Quick start

Launch the app:
```shell
docker-compose up
```
Create superuser:
```shell
docker-compose exec app python manage.py createsuperuser
```
Open Django administration `http://localhost:8000/admin/` to create users

Navigation `http://127.0.0.1:8000/`

Login (UI) `http://localhost:8000/login/`

Swagger API `http://localhost:8000/swagger/`

Login (API) - Obtain an authentication token for the user with `POST` `http://localhost:8000/auth/token/`
```json
{
    "username": "<user_username>",
    "password": "<user_password>"
}
```
