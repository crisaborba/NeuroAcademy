import logging
import os
import secrets

from flask import Flask, g, render_template

from auth import load_logged_in_user
from csrf import csrf_protect, inject_csrf_token
from db import init_db

# Debug/production mode is controlled by an env var, never hardcoded.
# Defaults to OFF so an accidental deploy never ships the Werkzeug debugger
# (which allows arbitrary code execution) or a stack-trace-leaking 500 page.
DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"


def create_app():
    app = Flask(__name__)
    app.debug = DEBUG

    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        if DEBUG:
            # Fine for local development only: sessions reset every restart.
            secret_key = "neuroacademy-dev-secret-change-me"
        else:
            # Never fall back to a guessable key outside of debug mode --
            # a known SECRET_KEY lets an attacker forge session cookies.
            secret_key = secrets.token_hex(32)
            logging.warning(
                "SECRET_KEY environment variable is not set. A random key was "
                "generated for this process, which means all sessions will be "
                "invalidated on restart. Set SECRET_KEY explicitly in production."
            )
    app.config["SECRET_KEY"] = secret_key

    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config["DATABASE"] = os.environ.get(
        "DATABASE_PATH", os.path.join(basedir, "neuroacademy.db")
    )

    # Session cookie hardening.
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    # Only force "Secure" (HTTPS-only) cookies when explicitly running behind
    # TLS; forcing it in local/plain-HTTP dev would silently break login.
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FORCE_HTTPS", "0") == "1"

    init_db(app)

    from seed import seed_all
    seed_all(app)

    from seed_course_ia_iniciantes import seed_course_ia_iniciantes
    seed_course_ia_iniciantes(app)

    from seed_achievements import seed_achievements
    seed_achievements(app)

    from seed_aula1_blocks import seed_aula1_blocks
    seed_aula1_blocks(app)

    app.before_request(load_logged_in_user)
    app.before_request(csrf_protect)

    @app.context_processor
    def inject_current_user():
        return {"current_user": g.user, "csrf_token": inject_csrf_token}

    @app.template_filter("brl")
    def brl_filter(value):
        try:
            return "{:,}".format(int(value)).replace(",", ".")
        except (ValueError, TypeError):
            return value

    @app.template_filter("lesson_markdown")
    def lesson_markdown_filter(value):
        # Trusted, admin/staff-authored lesson content only (never user
        # input -- community posts/comments etc. stay auto-escaped plain
        # text elsewhere). Gives real headings/bold/lists instead of a flat
        # wall of text, per the course-content readability requirement.
        import markdown as _markdown
        from markupsafe import Markup
        html = _markdown.markdown(value or "", extensions=["nl2br"])
        return Markup(html)

    from routes import bp as main_bp
    app.register_blueprint(main_bp)

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def server_error(e):
        # Never leak stack traces / internals to the client.
        logging.exception("Unhandled server error")
        return render_template("errors/500.html"), 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=DEBUG)
