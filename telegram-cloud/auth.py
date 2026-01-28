import os
import functools
from flask import session, redirect, url_for, request, render_template

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

def verify_password(password):
    """
    Verifies the password against the backend configuration.
    Supports both plain text configuration and (future) hash checking.
    """
    admin_password = os.getenv('ADMIN_PASSWORD')
    # Simple direct comparison for this version as requested
    if admin_password and password == admin_password:
        return True
    return False
