"""The redesign endpoints: the batched overview, admin projects, pool bulk and
the pool filter bar. All on the real API and database."""
import time
import urllib.parse

from helpers import dev_sign_in, sql


def test_overview_reports_live_state():
    admin = dev_sign_in("admin")
    overview = admin.get("/admin/overview")
    for key in (
        "jobs", "research", "projects", "pool", "keys", "system",
        "activity", "results", "clips_today", "users", "invites",
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
    stamp = int(time.time())
    ids = [f"m_bulk_{stamp}_a", f"m_bulk_{stamp}_b"]
    try:
        for mid in ids:
            sql(
                f"INSERT INTO missions (id, card, status) VALUES ('{mid}', '{{\"question\": \"bulk test\"}}', 'candidate') "
                "ON CONFLICT (id) DO NOTHING"
            )
        approved = admin.post("/admin/pool/bulk", {"ids": [ids[0]], "action": "approve"})
        assert approved["updated"] >= 1
        rejected = admin.post("/admin/pool/bulk", {"ids": [ids[1]], "action": "reject"})
        assert rejected["updated"] >= 1
        assert sql(f"SELECT status FROM missions WHERE id='{ids[0]}'").strip() == "unverified"
        assert sql(f"SELECT status FROM missions WHERE id='{ids[1]}'").strip() == "rejected"

        try:
            admin.post("/admin/pool/bulk", {"ids": [ids[0]], "action": "nope"})
            raise AssertionError("an invalid bulk action must be rejected")
        except Exception as exc:
            assert "422" in str(exc) or "unprocessable" in str(exc).lower()
    finally:
        sql(f"DELETE FROM missions WHERE id IN ('{ids[0]}', '{ids[1]}')")


def test_pool_filters_by_query():
    admin = dev_sign_in("admin")
    stamp = int(time.time())
    mid = f"m_filter_{stamp}"
    question = f"Can you filter a unique zebra {stamp}?"
    try:
        sql(
            f"INSERT INTO missions (id, card, status) VALUES ('{mid}', "
            f"'{{\"question\": \"{question}\", \"hook_text\": \"ZEBRA\"}}', 'candidate')"
        )
        found = []
        for _ in range(20):
            found = admin.get(f"/admin/pool?q=zebra")["items"]
            if found:
                break
            time.sleep(0.5)
        assert found, "the query filter found nothing"
        assert all(
            "zebra" in (e["card"]["question"] + e["card"].get("hook_text", "")).lower()
            for e in found
        )
    finally:
        sql(f"DELETE FROM missions WHERE id='{mid}'")
