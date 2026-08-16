from functools import wraps

from flask import g, redirect, request, session, url_for

from models import AnonymousUser
from repo import get_user_by_id


def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = AnonymousUser()
    else:
        user = get_user_by_id(user_id)
        g.user = user if user else AnonymousUser()


def login_user(user, remember=False):
    session.clear()
    session["user_id"] = user.id
    if remember:
        session.permanent = True
    g.user = user


def logout_user():
    session.clear()
    g.user = AnonymousUser()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user.is_authenticated:
            return redirect(url_for("main.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    return g.user
