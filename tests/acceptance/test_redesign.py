"""The redesign endpoints: the batched overview, admin projects, pool bulk and
the pool filter bar. All on the real API and database."""
import time
import urllib.parse

from helpers import dev_sign_in


def test_overview_reports_live_state():
    admin = dev_sign_in("admin")
    overview = admin.get("/admin/overview")
    for key in (
        "jobs", "research", "projects", "pool", "keys", "system",
        "activity", "results", "clips_today", "users", "invites", "storage",
    ):
        assert key in overview, f"overview missing {key}"
    assert "counts" in overview["jobs"]
    assert isinstance(overview["projects"], list)
    assert isinstance(overview["keys"]["research_sources_configured"], bool)
    assert isinstance(overview["results"]["total_views"], int)


def test_admin_projects_is_admin_only_and_lists_projects():
    admin = dev_sign_in("admin")
    res = admin.get("/admin/projects")
    assert isinstance(res["items"], list)
    creator = dev_sign_in("projects-creator")
    try:
        creator.get("/admin/projects")
        raise AssertionError("a creator must not read every user's projects")
    except Exception as exc:
        assert "403" in str(exc) or "401" in str(exc)


def test_pool_bulk_approves_and_rejects():
    admin = dev_sign_in("admin")
    admin.post("/admin/questions", {"questions": ["Bulk approve me?", "Bulk reject me?"]})
    items = []
    for _ in range(20):
        items = admin.get("/admin/pool")["items"]
        if len(items) >= 2:
            break
        time.sleep(0.5)
    assert len(items) >= 2, "the pool did not fill"

    approved = admin.post("/admin/pool/bulk", {"ids": [items[0]["id"]], "action": "approve"})
    assert approved["updated"] >= 1
    rejected = admin.post("/admin/pool/bulk", {"ids": [items[1]["id"]], "action": "reject"})
    assert rejected["updated"] >= 1

    try:
        admin.post("/admin/pool/bulk", {"ids": [items[0]["id"]], "action": "nope"})
        raise AssertionError("an invalid bulk action must be rejected")
    except Exception as exc:
        assert "422" in str(exc) or "unprocessable" in str(exc).lower()


def test_pool_filters_by_query():
    admin = dev_sign_in("admin")
    admin.post("/admin/questions", {"questions": ["Can you outrun five stars on a bicycle?"]})
    query = ""
    for _ in range(20):
        items = admin.get("/admin/pool")["items"]
        if items:
            query = items[0]["card"]["question"][:12]
            break
        time.sleep(0.5)
    assert query, "no candidate to filter"
    found = admin.get(f"/admin/pool?q={urllib.parse.quote(query)}")["items"]
    assert found, "the query filter found nothing"
    assert all(query.lower() in (e["card"]["question"] + e["card"].get("hook_text", "")).lower() for e in found)
