from task_management.settings import RABBITMQ_DEFAULT_USER, RABBITMQ_DEFAULT_PASS, RABBITMQ_HOST, REDIS_HOST

broker_url = f"amqp://{RABBITMQ_DEFAULT_USER}:{RABBITMQ_DEFAULT_PASS}@{RABBITMQ_HOST}//"
result_backend = f"redis://{REDIS_HOST}/0"
task_acks_late = True
task_track_started = True
