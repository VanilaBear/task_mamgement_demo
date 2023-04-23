from rest_framework import permissions


class TaskBasePermission(permissions.BasePermission):
    """Base permissions class for TaskViewSet"""

    def has_object_permission(self, request, view, obj):
        return request.method == "GET" or request.user.is_staff


class TaskCancelPermission(permissions.BasePermission):
    """Permissions class for TaskViewSet stop operation"""

    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or request.user == obj.user
