"""统一业务异常。"""
from fastapi import status


class AppError(Exception):
    code = "internal_error"
    message = "内部错误"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class NotFoundError(AppError):
    code = "not_found"
    message = "资源不存在"
    status_code = status.HTTP_404_NOT_FOUND


class PermissionDeniedError(AppError):
    code = "permission_denied"
    message = "无权访问"
    status_code = status.HTTP_403_FORBIDDEN


class AuthError(AppError):
    code = "unauthorized"
    message = "未认证或凭证失效"
    status_code = status.HTTP_401_UNAUTHORIZED


class ConflictError(AppError):
    code = "conflict"
    message = "资源冲突"
    status_code = status.HTTP_409_CONFLICT


class ValidationError(AppError):
    code = "validation_error"
    message = "请求参数错误"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
