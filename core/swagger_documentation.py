from drf_yasg.openapi import Schema, TYPE_OBJECT, TYPE_INTEGER, TYPE_STRING, Response
from rest_framework import status

from core.serializers import TaskCreateSerializer

CREATE_TASK_REQUEST_BODY = Schema(
    type=TYPE_OBJECT,
    properties={
        "name": Schema(type=TYPE_STRING, example="some_task_name"),
        "params": Schema(
            type=TYPE_OBJECT,
            properties={
                "param1": Schema(type=TYPE_INTEGER, example=60),
                "param2": Schema(type=TYPE_STRING, example="some param"),
            },
        ),
        "options": Schema(
            type=TYPE_OBJECT,
            properties={
                "retry": Schema(type=TYPE_INTEGER, example=2),
                "delay": Schema(type=TYPE_INTEGER, example=3000),
            },
        ),
    },
)

CREATE_TASK_RESPONSES = {status.HTTP_201_CREATED: Response("Success", TaskCreateSerializer)}

CANCEL_TASK_RESPONSES = {
    status.HTTP_200_OK: Response(
        description="Contains a message confirming that the task has been successfully canceled.",
        schema=Schema(
            type=TYPE_OBJECT,
            properties={
                "message": Schema(type=TYPE_STRING),
            },
        ),
        examples={
            "application/json": {"message": f"Task 3fa85f64-5717-4562-b3fc-2c963f66afa6 has been successfully canceled"}
        },
    ),
    status.HTTP_409_CONFLICT: Response(
        description="This response is generated in cases where task can not be canceled.",
        schema=Schema(
            type=TYPE_OBJECT,
            properties={
                "message": Schema(type=TYPE_STRING),
            },
        ),
        examples={
            "application/json": {
                "message": "Can not change status from CANCELED to CANCELED for the task 3fa85f64-5717-4562-b3fc-2c963f66afa6.",
            }
        },
    ),
}
