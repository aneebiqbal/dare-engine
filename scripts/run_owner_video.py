"""Upload one owner video through the real API and wait for the pipeline.

    python scripts/run_owner_video.py "/Users/mac/Downloads/last gta stream .mp4" [TOP_N]

The upload is streamed so a multi-gigabyte recording never sits in RAM.
"""
import http.client
import http.cookiejar
import json
import os
import pathlib
import sys
import time
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "acceptance"))

API_HOST = "localhost"
API_PORT = 8000
EMAIL = os.environ.get("CLIPDESK_EMAIL", "admin@example.com")
PASSWORD = os.environ.get("CLIPDESK_PASSWORD", "admin-password-123")


class Client:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )

    def _cookies(self):
        return "; ".join(f"{c.name}={c.value}" for c in self.jar)

    def csrf(self):
        req = urllib.request.Request(f"http://{API_HOST}:{API_PORT}/auth/csrf")
        with self.opener.open(req, timeout=30) as resp:
            resp.read()
        return self._cookie("clipdesk_csrf")

    def _cookie(self, name):
        for c in self.jar:
            if c.name == name:
                return c.value
        raise RuntimeError(f"no {name} cookie")

    def sign_in(self):
        body = json.dumps({"email": EMAIL, "password": PASSWORD}).encode()
        req = urllib.request.Request(
            f"http://{API_HOST}:{API_PORT}/auth/sign-in",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-CSRF-Token": self.csrf(),
                "Cookie": self._cookies(),
            },
        )
        with self.opener.open(req, timeout=30) as resp:
            resp.read()

    def upload(self, path: str) -> dict:
        """Stream a multipart upload with no size limit in memory."""
        target = pathlib.Path(path)
        boundary = "----clipdeskowner"
        prefix = (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"{target.name}\"\r\nContent-Type: video/mp4\r\n\r\n"
        ).encode()
        suffix = f"\r\n--{boundary}--\r\n".encode()
        conn = http.client.HTTPConnection(API_HOST, API_PORT, timeout=3600)
        conn.putrequest("POST", "/pipeline/upload")
        conn.putheader("Content-Type", f"multipart/form-data; boundary={boundary}")
        conn.putheader("X-CSRF-Token", self.csrf())
        conn.putheader("Cookie", self._cookies())
        conn.putheader("Content-Length", str(len(prefix) + target.stat().st_size + len(suffix)))
        conn.endheaders()
        conn.send(prefix)
        sent = 0
        started = time.time()
        with open(target, "rb") as fh:
            while chunk := fh.read(4 << 20):
                conn.send(chunk)
                sent += len(chunk)
                if sent % (128 << 20) < len(chunk):
                    print(f"  uploaded {sent / 1e9:.2f} GB", flush=True)
        conn.send(suffix)
        resp = conn.getresponse()
        body = resp.read()
        conn.close()
        if resp.status != 200:
            raise RuntimeError(f"upload failed {resp.status}: {body[:300]!r}")
        print(f"uploaded in {time.time() - started:.1f}s", flush=True)
        return json.loads(body)


def main():
    path = sys.argv[1]
    top_n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    client = Client()
    client.sign_in()
    res = client.upload(path)
    run_id = res["run_id"]
    if top_n != 10:
        from helpers import sql

        sql(f"UPDATE pipeline_runs SET top_n = {top_n} WHERE id = '{run_id}'")
    print("run", run_id, "duration", res.get("duration_seconds"), flush=True)
    deadline = time.time() + 6 * 3600
    while time.time() < deadline:
        req = urllib.request.Request(
            f"http://{API_HOST}:{API_PORT}/pipeline/{run_id}",
            headers={"Cookie": client._cookies()},
        )
        with client.opener.open(req, timeout=60) as resp:
            state = json.loads(resp.read())
        run = state["run"]
        print(run["state"], run["stage"], run["progress"], run["action"], flush=True)
        if run["state"] in ("done", "failed", "paused"):
            print("TIMINGS", json.dumps(run["stage_timings"], indent=1))
            print("COMPUTE", run["compute_path"])
            print("NOTES", run["notes"])
            print("MEMORY", json.dumps(run["memory"]))
            print("CLIPS", len(state["clips"]), [c["duration_seconds"] for c in state["clips"]])
            return
        time.sleep(10)


if __name__ == "__main__":
    main()
