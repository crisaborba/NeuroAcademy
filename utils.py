"""Small shared helpers used by both seed.py and routes.py.

Kept separate from seed.py so that request-handling code (routes.py) does
not need to import the database-seeding module just to reuse a string
helper -- that was an unnecessary coupling between two unrelated concerns.
"""
import re


def slugify(text):
    return (
        text.lower()
        .replace("ã", "a").replace("á", "a").replace("â", "a")
        .replace("é", "e").replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o").replace("ô", "o")
        .replace("ú", "u").replace("ç", "c")
        .replace(":", "").replace(",", "").replace(".", "")
        .replace("!", "").replace("?", "")
        .replace(" ", "-")
    )


# Password policy shared by the backend (routes.py, authoritative) and
# documented here so the frontend indicator (login.html) implements the
# exact same rules. The backend NEVER trusts the JS-side check -- it always
# re-validates with this function before creating an account.
PASSWORD_MIN_LENGTH = 8
SPECIAL_CHARS_RE = re.compile(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\];'`~/\\]")


def password_requirements(password: str) -> dict:
    """Returns which password rules are satisfied, keyed the same way the
    frontend indicator (login.html) labels them, so both sides agree."""
    password = password or ""
    return {
        "length": len(password) >= PASSWORD_MIN_LENGTH,
        "uppercase": any(c.isupper() for c in password),
        "lowercase": any(c.islower() for c in password),
        "number": any(c.isdigit() for c in password),
        "special": bool(SPECIAL_CHARS_RE.search(password)),
    }


def password_is_strong(password: str) -> bool:
    return all(password_requirements(password).values())
