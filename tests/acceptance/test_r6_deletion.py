"""R6 proof: deleting an account removes every row and every stored file."""
import http.cookiejar
import json
import pathlib
import subprocess
import time
import urllib.request

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
API = "http://localhost:8000"
STANDIN = ROOT / "tests/fixtures/standin_speech_45s.mp4"


def _opener(name):
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    req = urllib.request.Request(
        f"{API}/auth/dev/sign-in",
        data=json.dumps({"display_name": name}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(req, timeout=30) as resp:
        json.loads(resp.read())
    return opener


def call(opener, method, path, body=None, raw=None, ctype="application/json"):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(
        f"{API}{path}", data=data, method=method,
        headers={"Content-Type": ctype} if data else {},
    )
    with opener.open(req, timeout=180) as resp:
        return json.loads(resp.read())


def _s3_keys():
    # S3Mock has no shell; list via boto3 from the api image.
    code = (
        "import boto3;"
        "from botocore.config import Config;"
        "c=boto3.client('s3',endpoint_url='http://storage:9090',"
        "aws_access_key_id='clipdesk',aws_secret_access_key='clipdesk-dev-secret',"
        "region_name='us-east-1',config=Config(s3={'addressing_style':'path'}));"
        "r=c.list_objects_v2(Bucket='clipdesk');"
        "print('\\n'.join(o['Key'] for o in r.get('Contents',[])))"
    )
    out = subprocess.run(
        ["docker", "compose", "exec", "-T", "api", "python", "-c", code],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return {line for line in out.stdout.splitlines() if line.strip()}


def _ensure_mission(opener):
    pool = call(opener, "GET", "/admin/pool")
    if pool:
        mission_id = pool[0]["id"]
    else:
        # The recorded provider reuses ids, so seed a candidate directly.
        mission_id = "m_r6"
        code = (
            "import json;from app import db;"
            "card=json.load(open('app/llm_recorded.json'))['cards'][0];card['id']='m_r6';"
            "conn=db.connect();cur=conn.cursor();"
            "cur.execute(\"INSERT INTO missions (id,card,status) VALUES ('m_r6',%s,'candidate') "
            "ON CONFLICT (id) DO UPDATE SET status='candidate', card=EXCLUDED.card\","
            "(json.dumps(card),));conn.commit()"
        )
        subprocess.run(
            ["docker", "compose", "exec", "-T", "api", "python", "-c", code],
            cwd=ROOT, check=True, capture_output=True,
        )
    call(opener, "POST", f"/admin/pool/{mission_id}/approve", {})
    return mission_id


def test_deleting_an_account_removes_rows_and_files():
    name = f"Delete Me {int(time.time())}"
    opener = _opener(name)
    me = call(opener, "GET", "/me")["user"]
    user_id = me["id"]

    mission_id = _ensure_mission(opener)

    boundary = "----r6"
    marks = json.dumps([{"mission_id": mission_id, "start": 5, "end": 20, "result": "0:41"}])
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"rec.mp4\"\r\n"
        f"Content-Type: video/mp4\r\n\r\n"
    ).encode() + STANDIN.read_bytes() + (
        f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"marks\"\r\n\r\n{marks}\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    call(opener, "POST", "/uploads", raw=body, ctype=f"multipart/form-data; boundary={boundary}")

    before = _s3_keys()
    assert any(k.startswith(f"recordings/{user_id}/") for k in before), "recording not stored"

    rows = subprocess.run(
        [
            "docker", "compose", "exec", "-T", "db", "psql", "-U", "clipdesk", "-d", "clipdesk",
            "-t", "-c",
            "SELECT (SELECT count(*) FROM users WHERE id=%s) || ',' || "
            "(SELECT count(*) FROM assignments WHERE user_id=%s) || ',' || "
            "(SELECT count(*) FROM sessions WHERE user_id=%s) || ',' || "
            "(SELECT count(*) FROM streams WHERE user_id=%s);",
        ],
        cwd=ROOT, capture_output=True, text=True,
    )
    # The query above needs parameters; do it with a small Python check instead.
    counts = subprocess.run(
        ["docker", "compose", "exec", "-T", "api", "python", "-c",
         f"from app import db;"
         f"conn=db.connect();cur=conn.cursor();"
         f"cur.execute(\"SELECT (SELECT count(*) FROM users WHERE id='{user_id}'),\""
         f"\" (SELECT count(*) FROM assignments WHERE user_id='{user_id}'),\""
         f"\" (SELECT count(*) FROM sessions WHERE user_id='{user_id}'),\""
         f"\" (SELECT count(*) FROM streams WHERE user_id='{user_id}')\");"
         f"print(','.join(map(str,cur.fetchone())))"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()
    users, assignments, sessions, streams = (int(x) for x in counts.split(","))
    assert users == assignments == sessions == streams == 1

    assert call(opener, "DELETE", "/account")["ok"] is True

    after = subprocess.run(
        ["docker", "compose", "exec", "-T", "api", "python", "-c",
         f"from app import db;"
         f"conn=db.connect();cur=conn.cursor();"
         f"cur.execute(\"SELECT (SELECT count(*) FROM users WHERE id='{user_id}'),\""
         f"\" (SELECT count(*) FROM assignments WHERE user_id='{user_id}'),\""
         f"\" (SELECT count(*) FROM sessions WHERE user_id='{user_id}'),\""
         f"\" (SELECT count(*) FROM streams WHERE user_id='{user_id}'),\""
         f"\" (SELECT count(*) FROM clips WHERE assignment_id IN (SELECT id FROM assignments WHERE user_id='{user_id}'))\");"
         f"print(','.join(map(str,cur.fetchone())))"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert all(int(x) == 0 for x in after.split(",")), f"rows left behind: {after}"

    keys_after = _s3_keys()
    assert not any(k.startswith(f"recordings/{user_id}/") for k in keys_after), "files left behind"
