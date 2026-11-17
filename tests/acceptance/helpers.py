"""Shared helpers for acceptance tests: real accounts, CSRF, pagination."""
import http.cookiejar
import json
import pathlib
import subprocess
import urllib.request

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
API = "http://localhost:8000"
WEB = "http://localhost:3100"


class Client:
    def __init__(self) -> None:
        self.cookiejar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookiejar)
        )
        self._csrf: str | None = None

    def csrf(self) -> str:
        # Read the current cookie each time: sign-in rotates it.
        for cookie in self.cookiejar:
            if cookie.name == "clipdesk_csrf":
                return cookie.value
        with self.opener.open(f"{API}/auth/csrf", timeout=30) as resp:
            json.loads(resp.read())
        for cookie in self.cookiejar:
            if cookie.name == "clipdesk_csrf":
                return cookie.value
        raise RuntimeError("no csrf cookie issued")

    def call(self, method: str, path: str, body=None, raw=None, ctype="application/json"):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        headers = {}
        if data and ctype != "multipart/form-data":
            headers["Content-Type"] = ctype
        elif raw is not None:
            headers["Content-Type"] = ctype
        if method not in ("GET", "HEAD", "OPTIONS"):
            headers["X-CSRF-Token"] = self.csrf()
        req = urllib.request.Request(f"{API}{path}", data=data, method=method, headers=headers)
        with self.opener.open(req, timeout=180) as resp:
            return json.loads(resp.read())

    def get(self, path: str):
        return self.call("GET", path)

    def post(self, path: str, body=None):
        return self.call("POST", path, body)

    def patch(self, path: str, body=None):
        return self.call("PATCH", path, body)

    def delete(self, path: str):
        return self.call("DELETE", path)


def dev_sign_in(name: str) -> Client:
    client = Client()
    client.post("/auth/dev/sign-in", {"display_name": name})
    return client


def sql(statement: str) -> str:
    return subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "psql", "-U", "clipdesk", "-d", "clipdesk", "-t", "-A", "-F", ",", "-c", statement],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout


def truncate(*tables: str) -> None:
    sql("TRUNCATE " + ", ".join(tables) + " RESTART IDENTITY CASCADE;")


def make_admin(email: str = "admin@example.com", password: str = "admin-password-123") -> Client:
    """Create the first admin directly, then sign in."""
    from argon2 import PasswordHasher

    sql(f"DELETE FROM login_attempts WHERE email='{email}'")
    sql(
        "INSERT INTO users (email, display_name, password_hash, role) VALUES ("
        f"'{email}', 'Admin', '{PasswordHasher().hash(password)}', 'admin') "
        "ON CONFLICT (lower(email)) DO UPDATE SET role='admin'"
    )
    client = Client()
    client.post("/auth/sign-in", {"email": email, "password": password})
    return client


def make_invite(admin: Client, email: str = "creator@example.com") -> str:
    return admin.post("/admin/invites", {"email": email})["code"]


def create_user_with_invite(admin: Client, email: str, password: str = "creator-password-123", name: str = "Creator") -> Client:
    code = make_invite(admin, email)
    client = Client()
    client.post("/auth/sign-up", {
        "email": email, "password": password, "display_name": name, "invite_code": code,
    })
    return client


def sign_up(email: str = "creator@example.com", password: str = "creator-password-123", name: str = "Creator") -> Client:
    return create_user_with_invite(make_admin(), email, password, name)


def seed_mission(admin: Client, question: str = "Can you outrun five stars on a bicycle?") -> str:
    # Re-writing a card does not reset its status, so clear the pool first.
    truncate("missions", "assignments", "attempts", "daily_sets")
    admin.post("/admin/questions", {"questions": [question]})
    mission_id = admin.get("/admin/pool")["items"][0]["id"]
    admin.post(f"/admin/pool/{mission_id}/approve", {})
    return mission_id


def upload_recording(client: Client, marks: list[dict], filename: str = "recording.mp4") -> dict:
    boundary = "----clipdesk-test"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
        f"Content-Type: video/mp4\r\n\r\n"
    ).encode() + (ROOT / "tests/fixtures/standin_speech_45s.mp4").read_bytes() + (
        f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"marks\"\r\n\r\n"
        f"{json.dumps(marks)}\r\n--{boundary}--\r\n"
    ).encode()
    return client.call("POST", "/uploads", raw=body, ctype=f"multipart/form-data; boundary={boundary}")


def storage_keys() -> set[str]:
    out = subprocess.run(
        ["docker", "compose", "exec", "-T", "api", "python", "-c",
         "from app import storage; print('\\n'.join(storage.list_keys()))"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return {line for line in out.stdout.splitlines() if line.strip()}


@pytest.fixture(scope="session")
def admin() -> Client:
    return make_admin()
