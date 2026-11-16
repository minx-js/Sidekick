"""Simple user accounts for the Sidekick: register with an invite code, then log in.

Passwords are never stored. Only a salted scrypt hash is kept in a small SQLite file.
Set DATA_DIR to a persistent disk (for example /data on Render) so accounts survive redeploys.
"""

import hashlib
import hmac
import os
import re
import secrets
import sqlite3

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
DB_PATH = os.path.join(DATA_DIR, "users.db")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")
MIN_PASSWORD = 8


def _connect():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, salt BLOB NOT NULL, hash BLOB NOT NULL)")
    return conn


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)


def register_user(username: str, password: str, confirm: str, code: str) -> str:
    """Create an account. Returns a message for the user."""
    invite = os.environ.get("REGISTRATION_CODE", "")
    if not invite:
        return "Registration is closed."
    if not hmac.compare_digest((code or "").encode(), invite.encode()):
        return "Wrong invite code."
    username = (username or "").strip().lower()
    if not USERNAME_RE.match(username):
        return "Username must be 3-30 characters: letters, numbers, dot, dash or underscore."
    if len(password or "") < MIN_PASSWORD:
        return f"Password must be at least {MIN_PASSWORD} characters."
    if password != confirm:
        return "The two passwords do not match."
    salt = secrets.token_bytes(16)
    try:
        with _connect() as conn:
            conn.execute("INSERT INTO users VALUES (?, ?, ?)", (username, salt, _hash(password, salt)))
    except sqlite3.IntegrityError:
        return "That username is taken."
    return "Account created. You can log in now."


def verify_user(username: str, password: str) -> bool:
    username = (username or "").strip().lower()
    with _connect() as conn:
        row = conn.execute("SELECT salt, hash FROM users WHERE username = ?", (username,)).fetchone()
    salt, stored = row if row else (b"\0" * 16, b"\0" * 32)
    candidate = _hash(password or "", salt)  # always hash, so a missing user takes the same time
    return row is not None and hmac.compare_digest(candidate, stored)
