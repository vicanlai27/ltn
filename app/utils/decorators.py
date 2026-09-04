from functools import wraps

from flask import abort, redirect, url_for, flash
from flask_login import current_user, login_required


def role_required(*roles):
    """
    Require the current user to have one of the specified roles.
    Usage: @role_required('admin', 'super_admin')
    """
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(fn):
    """Require admin or super_admin role."""
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role not in (User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN):
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def super_admin_required(fn):
    """Require super_admin role."""
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role != User.ROLE_SUPER_ADMIN:
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def editor_required(fn):
    """Require editor or above (editor, admin, super_admin).

    NOT teacher_editor — despite this decorator's old docstring, the
    hierarchy check below (is_at_least) always excluded it. teacher_editor,
    author, and the student/alumni contributor roles get their own
    workspace at /newsroom instead (see app.routes.newsroom).
    """
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_at_least(User.ROLE_EDITOR):
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


# Import here to avoid circular dependency
from app.models.user import User