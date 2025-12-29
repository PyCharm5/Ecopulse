"""
Декораторы для проверки прав доступа
"""
from functools import wraps
from flask import jsonify, current_app
from flask_login import current_user
from typing import Callable, Any

def admin_required(f: Callable) -> Callable:
    """
    Декоратор для проверки прав администратора
    """
    @wraps(f)
    def decorated_function(*args, **kwargs) -> Any:
        if not current_user.is_authenticated:
            return jsonify({'status': 'error', 'message': 'Требуется авторизация'}), 401
        if not current_user.is_admin:
            return jsonify({'status': 'error', 'message': 'Требуются права администратора'}), 403
        return f(*args, **kwargs)
    return decorated_function


def worker_required(f: Callable) -> Callable:
    """
    Декоратор для проверки прав работника
    """
    @wraps(f)
    def decorated_function(*args, **kwargs) -> Any:
        if not current_user.is_authenticated:
            return jsonify({'status': 'error', 'message': 'Требуется авторизация'}), 401
        if not (current_user.is_worker or current_user.is_admin):
            return jsonify({'status': 'error', 'message': 'Требуются права работника'}), 403
        return f(*args, **kwargs)
    return decorated_function
