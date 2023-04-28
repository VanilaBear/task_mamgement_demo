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
Apply migrations:
```shell
docker-compose exec app python manage.py migratate
```
Create superuser:
```shell
docker-compose exec app python manage.py createsuperuser
```
Open Django administration [`http://localhost:8000/admin/`](http://localhost:8000/admin/) to create users

Navigation [`http://localhost:8000/`](http://localhost:8000/)

Login (UI) [`http://localhost:8000/login/`](http://localhost:8000/login/)

For authorized users:
 - Swagger API [`http://localhost:8000/swagger/`](http://localhost:8000/swagger/)

 - Task table (very simple) [`http://localhost:8000/tasks/`](http://localhost:8000/tasks/)


Flower [`http://localhost:5555/`](http://localhost:5555/)


Token (API) - Obtain an authentication token for the user with `POST` `http://localhost:8000/auth/token/`
```json
{
    "username": "<user_username>",
    "password": "<user_password>"
}
```
