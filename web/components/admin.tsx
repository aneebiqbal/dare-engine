"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  api,
  type AiConfig,
  type AiUsage,
  type AuditEntry,
  type ErrorReport,
  type Invite,
  type Job,
  type PoolEntry,
  type Project,
  type EngineEvent,
  type SystemLoad,
  type AdminOverview,
  type Game,
  type User,
} from "@/lib/api";
import {
  Badge,
  Button,
  Card,
  Dialog,
  Field,
  Input,
  Notice,
  PageState,
  Select,
  Stat,
  Table,
  Td,
  Textarea,
  Tr,
  useToast,
} from "@/components/ui";
import { Sources } from "./games";
import { AdminKeys } from "./admin-keys";
import {
  ActivityFeed,
  DataTable,
  FilterBar,
  LiveStrip,
  Metric,
  ProgressCard,
  Rail,
  Section,
  StatusBadge,
  WorkHeader,
  WorkQueue,
  type Column,
  type WorkItem,
} from "./work";

function useList<T>(fetcher: (params?: string) => Promise<{ items: T[]; total: number }>, params = "") {
  const [items, setItems] = useState<T[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetcher(params);
      setItems(res.items);
      setTotal(res.total);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [fetcher, params]);
  useEffect(() => {
    void load();
  }, [load]);
  return { items, total, loading, error, reload: load, setItems };
}

export function AdminOverview() {
  const [data, setData] = useState<AdminOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  const load = useCallback(async () => {
    try {
      setData(await api.adminOverview());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load the overview");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = setInterval(() => void load(), 5000);
    return () => clearInterval(timer);
  }, [load]);

  async function retry(id: string) {
    try {
      await api.retryJob(id);
      toast("Job requeued", "success");
      await load();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not retry", "danger");
    }
  }

  const needs: WorkItem[] = [];
  if (data) {
    for (const job of data.jobs.active.filter((j) => j.state === "failed").slice(0, 4)) {
      needs.push({
        id: job.id,
        title: job.kind,
        subtitle: job.error ?? "Failed",
        status: "failed",
        meta: job.stage ?? undefined,
        href: "/admin/jobs",
        action: (
          <Button size="sm" variant="outline" onClick={() => void retry(job.id)}>
            Retry
          </Button>
        ),
      });
    }
    for (const key of data.keys.integrations.filter((k) => k.configured && k.status !== "connected")) {
      needs.push({
        id: key.name,
        title: key.label,
        subtitle: key.status_detail ?? key.status,
        status: "needs",
        href: "/admin/setup",
      });
    }
    if (data.pool.candidate > 0) {
      needs.push({
        id: "pool",
        title: `${data.pool.candidate} idea${data.pool.candidate === 1 ? "" : "s"} awaiting review`,
        subtitle: "Approve, reject or assign",
        status: "needs",
        href: "/admin/pool",
      });
    }
    if (data.users.locked > 0) {
      needs.push({
        id: "locked",
        title: `${data.users.locked} locked account${data.users.locked === 1 ? "" : "s"}`,
        subtitle: "Someone cannot sign in",
        status: "needs",
        href: "/admin/users",
      });
    }
  }

  const jobItems: WorkItem[] = (data?.jobs.active ?? []).map((j) => ({
    id: j.id,
    title: j.kind,
    subtitle: j.error ?? undefined,
    status: j.state === "failed" ? "failed" : "running",
    meta: j.stage ?? j.state,
    href: "/admin/jobs",
  }));

  const live = Boolean(
    data && (data.jobs.running > 0 || data.research.active.length > 0 || data.projects.some((p) => p.stage === "analyzing")),
  );

  return (
    <div className="grid gap-6" data-tour="admin-overview">
      <WorkHeader
        eyebrow="Admin"
        title="Overview"
        status={live ? "running" : "idle"}
        actions={
          <Button variant="outline" onClick={() => void load()} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh"}
          </Button>
        }
      />
      <PageState loading={loading} error={error} empty={false}>
        {data && (
          <>
            <LiveStrip overview={data} />
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
              <div className="flex min-w-0 flex-col gap-6">
                <Section title="Needs you" count={needs.length} live={needs.length > 0}>
                  <Card>
                    <WorkQueue
                      items={needs}
                      empty={<p className="px-2 py-3 text-sm text-muted">Nothing needs you right now.</p>}
                    />
                  </Card>
                </Section>

                <Section
                  title="Projects"
                  count={data.projects.length}
                  action={
                    <Link href="/admin/projects" className="text-xs text-accent hover:underline">
                      All projects
                    </Link>
                  }
                >
                  {data.projects.length === 0 ? (
                    <Card>
                      <p className="px-2 py-3 text-sm text-muted">
                        No projects yet. Import a recording to start one.
                      </p>
                    </Card>
                  ) : (
                    <div className="grid gap-3 md:grid-cols-2">
                      {data.projects.slice(0, 4).map((p) => (
                        <ProgressCard
                          key={p.id}
                          title={p.name}
                          status={
                             p.stage === "exported"
                               ? "done"
                               : p.queued || p.stage === "analyzing"
                                 ? "running"
                                 : p.stage === "clips_ready" || p.stage === "reviewed" || p.stage === "imported"
                                   ? "needs"
                                   : "idle"
                           }
                          progress={p.progress}
                          stage={p.stage.replace(/_/g, " ")}
                          meta={`${p.candidates} candidates · ${p.clips.ready}/${p.clips.total} clips`}
                          action={
                            <Link
                              href="/admin/projects"
                              className="inline-flex items-center rounded-full px-4 py-2 text-sm font-medium text-muted ring-surface transition hover:bg-surface-2 hover:text-text"
                            >
                              Open
                            </Link>
                          }
                        />
                      ))}
                    </div>
                  )}
                </Section>

                <Section
                  title="Job queue"
                  count={jobItems.length}
                  action={
                    <Link href="/admin/jobs" className="text-xs text-accent hover:underline">
                      All jobs
                    </Link>
                  }
                >
                  <Card>
                    <WorkQueue
                      items={jobItems}
                      empty={<p className="px-2 py-3 text-sm text-muted">No queued, running or failed jobs.</p>}
                    />
                  </Card>
                </Section>
              </div>

              <Rail>
                <Card>
                  <div className="flex flex-col gap-3">
                    <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-muted">
                      Engine activity
                    </h2>
                    <ActivityFeed items={data.activity} />
                  </div>
                </Card>

                <Card>
                  <div className="flex flex-col gap-3">
                    <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-muted">
                      Results
                    </h2>
                    {data.results.best || data.results.worst ? (
                      <div className="flex flex-col gap-3">
                        {data.results.best && (
                          <div className="flex flex-col gap-1">
                            <span className="text-[10px] uppercase tracking-[0.18em] text-success">Best</span>
                            <span className="truncate text-sm font-medium">{data.results.best.title ?? data.results.best.clip_id}</span>
                            <span className="font-mono text-xs text-muted">
                              {data.results.best.views.toLocaleString()} views
                            </span>
                          </div>
                        )}
                        {data.results.worst && (
                          <div className="flex flex-col gap-1">
                            <span className="text-[10px] uppercase tracking-[0.18em] text-danger">Worst retention</span>
                            <span className="truncate text-sm font-medium">{data.results.worst.title ?? data.results.worst.clip_id}</span>
                            <span className="font-mono text-xs text-muted">
                              {data.results.worst.avg_view_percentage ?? "—"}% avg view
                            </span>
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-sm text-muted">No metrics recorded yet.</p>
                    )}
                    <Link href="/results" className="text-xs text-accent hover:underline">
                      Open results
                    </Link>
                  </div>
                </Card>

                <Card>
                  <div className="flex flex-col gap-3">
                    <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-muted">Keys</h2>
                    <div className="flex flex-col gap-2">
                      {data.keys.integrations.map((k) => (
                        <div key={k.name} className="flex items-center justify-between gap-2 text-sm">
                          <span className="truncate">{k.label}</span>
                          <StatusBadge
                            status={k.status === "connected" ? "done" : k.status === "invalid" ? "failed" : k.status === "unreachable" ? "needs" : "idle"}
                          />
                        </div>
                      ))}
                    </div>
                    <Link href="/admin/setup" className="text-xs text-accent hover:underline">
                      Manage keys
                    </Link>
                  </div>
                </Card>
              </Rail>
            </div>
          </>
        )}
      </PageState>
    </div>
  );
}

export function AdminUsers() {
  const { items, loading, error, reload, setItems } = useList(api.adminUsers);
  const [resetUrl, setResetUrl] = useState<string | null>(null);
  const toast = useToast();

  async function setRole(id: string, role: string) {
    try {
      await api.adminUpdateUser(id, role);
      setItems((prev) => prev.map((u) => (u.id === id ? { ...u, role: role as User["role"] } : u)));
      toast("Role updated", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "danger");
    }
  }

  async function reset(id: string) {
    try {
      const res = await api.adminResetLink(id);
      setResetUrl(res.url);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "danger");
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <WorkHeader
        eyebrow="Manage"
        title="Users"
        status={items.some((u) => u.locked) ? "needs" : "idle"}
        actions={
          <div className="flex items-center gap-4">
            <Metric label="Total" value={items.length} />
            <Metric label="Admins" value={items.filter((u) => u.role === "admin").length} />
            <Metric label="Locked" value={items.filter((u) => u.locked).length} />
          </div>
        }
      />
      {resetUrl && (
        <Notice>
          One-time reset link (give it to the creator): <code className="break-all">{resetUrl}</code>
        </Notice>
      )}
      <PageState loading={loading} error={error} empty={items.length === 0}>
        <Table head={["Email", "Name", "Role", "Locked", "Last sign-in", "Actions"]}>
          {items.map((u) => (
            <Tr key={u.id}>
              <Td>{u.email}</Td>
              <Td>{u.display_name}</Td>
              <Td>
                <Select
                  aria-label={`Role for ${u.email ?? u.display_name ?? u.id}`}
                  value={u.role}
                  onChange={(e) => void setRole(u.id, e.target.value)}
                >
                  <option value="creator">creator</option>
                  <option value="admin">admin</option>
                </Select>
              </Td>
              <Td>{u.locked ? <Badge tone="danger">locked</Badge> : <Badge tone="success">no</Badge>}</Td>
              <Td>{u.last_login_at?.slice(0, 10) ?? "—"}</Td>
              <Td>
                <Button size="sm" variant="outline" onClick={() => void reset(u.id)}>
                  Reset link
                </Button>
              </Td>
            </Tr>
          ))}
        </Table>
      </PageState>
    </div>
  );
}

export function AdminInvites() {
  const { items, loading, error, reload } = useList(api.adminInvites);
  const [email, setEmail] = useState("");
  const [created, setCreated] = useState<{ id: string; code: string; url: string } | null>(null);
  const toast = useToast();

  async function create() {
    try {
      const invite = await api.adminCreateInvite(email || undefined);
      setCreated(invite);
      setEmail("");
      await reload();
      toast("Invite created", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "danger");
    }
  }

  async function revoke(id: string) {
    try {
      await api.adminRevokeInvite(id);
      await reload();
      toast("Invite revoked", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not revoke", "danger");
    }
  }

  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      toast("Copied", "success");
    } catch {
      toast("Copy failed", "danger");
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <WorkHeader
        eyebrow="Manage"
        title="Invites"
        status={items.some((i) => !i.used && !i.revoked) ? "needs" : "idle"}
        actions={
          <Metric
            label="Open invites"
            value={items.filter((i) => !i.used && !i.revoked).length}
          />
        }
      />
      <Card>
        <div className="flex flex-col gap-3">
          <Field label="Invite" hint="Optional email; leave empty for a general code.">
            <div className="flex gap-2">
              <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="creator@example.com" />
              <Button onClick={create}>Create invite</Button>
            </div>
          </Field>
          {created && (
            <Notice>
              Code <code>{created.code}</code> ·{" "}
              <code className="break-all">{created.url}</code>
            </Notice>
          )}
        </div>
      </Card>
      <PageState loading={loading} error={error} empty={items.length === 0}>
        <Table head={["Code", "Email", "Created", "State", "Actions"]}>
          {items.map((i) => (
            <Tr key={i.id}>
              <Td>
                <button
                  type="button"
                  onClick={() => void copy(i.code)}
                  className="text-accent hover:underline"
                  title="Copy code"
                >
                  <code>{i.code}</code>
                </button>
              </Td>
              <Td>{i.email ?? "—"}</Td>
              <Td>{i.created_at.slice(0, 10)}</Td>
              <Td>
                {i.used ? <Badge tone="success">used</Badge> : i.revoked ? <Badge tone="danger">revoked</Badge> : <Badge tone="accent">open</Badge>}
              </Td>
              <Td>
                {!i.used && !i.revoked && (
                  <Button size="sm" variant="danger" onClick={() => void revoke(i.id)}>
                    Revoke
                  </Button>
                )}
              </Td>
            </Tr>
          ))}
        </Table>
      </PageState>
    </div>
  );
}

type PoolReview = {
  merged: { question: string; count: number }[];
  policy_flags: { question: string; reason: string }[];
  fallback: boolean;
};

export function AdminPool() {
  const [items, setItems] = useState<PoolEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [review, setReview] = useState<PoolReview | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [games, setGames] = useState<Game[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [assignFor, setAssignFor] = useState<PoolEntry | null>(null);
  const [assignee, setAssignee] = useState("");
  const [filters, setFilters] = useState({
    q: "",
    game_id: "",
    source: "",
    min_score: "",
    sort: "created_at",
    order: "desc",
  });
  const toast = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        status: "candidate",
        page_size: "100",
        sort: filters.sort,
        order: filters.order,
      });
      if (filters.game_id) params.set("game_id", filters.game_id);
      if (filters.source) params.set("source", filters.source);
      if (filters.q) params.set("q", filters.q);
      if (filters.min_score) params.set("min_score", filters.min_score);
      const res = await api.pool(`?${params.toString()}`);
      setItems(res.items);
      setTotal(res.total);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load the pool");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    api.adminGames("?page_size=100").then((r) => setGames(r.items)).catch(() => {});
    api.adminUsers("?page_size=100")
      .then((r) => setUsers(r.items.filter((u) => u.role !== "admin")))
      .catch(() => {});
  }, []);

  async function write(questions?: string[]) {
    const list = questions ?? text.split("\n").map((q) => q.trim()).filter(Boolean);
    if (!list.length) return;
    setBusy(true);
    try {
      await api.writeCards(list);
      setText("");
      await load();
      toast("Cards written", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "danger");
    } finally {
      setBusy(false);
    }
  }

  async function reviewQuestions() {
    const questions = text.split("\n").map((q) => q.trim()).filter(Boolean);
    if (!questions.length) return;
    setBusy(true);
    try {
      setReview(await api.poolReview(questions));
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "danger");
    } finally {
      setBusy(false);
    }
  }

  async function actOne(id: string, action: "approve" | "reject") {
    setBusy(true);
    try {
      const res = await api.poolBulk([id], action);
      toast(`${res.updated} idea(s) ${action === "approve" ? "approved" : "rejected"}`, "success");
      await load();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Action failed", "danger");
    } finally {
      setBusy(false);
    }
  }

  async function assignOne() {
    if (!assignFor || !assignee) return;
    setBusy(true);
    try {
      await api.poolBulk([assignFor.id], "assign", assignee);
      toast("Dare assigned", "success");
      setAssignFor(null);
      setAssignee("");
      await load();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not assign", "danger");
    } finally {
      setBusy(false);
    }
  }

  async function bulk(action: "approve" | "reject" | "assign", user_id?: string) {
    if (!selected.size) return;
    setBusy(true);
    try {
      const res = await api.poolBulk(Array.from(selected), action, user_id);
      toast(
        `${res.updated} idea(s) ${action === "approve" ? "approved" : action === "reject" ? "rejected" : "assigned"}`,
        "success",
      );
      setSelected(new Set());
      setAssignee("");
      await load();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Bulk action failed", "danger");
    } finally {
      setBusy(false);
    }
  }

  function toggleSelected(key: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function toggleExpanded(key: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  const columns: Column<PoolEntry>[] = [
    {
      key: "question",
      label: "Idea",
      sortable: false,
      render: (e) => (
        <div className="flex min-w-0 flex-col gap-0.5">
          <span className="font-medium leading-snug">{e.card?.question ?? "Untitled"}</span>
          {e.card?.hook_text && <span className="truncate text-xs text-muted">{e.card.hook_text}</span>}
        </div>
      ),
    },
    {
      key: "mode",
      label: "Mode",
      sortable: false,
      render: (e) => (
        <span className="font-mono text-xs text-muted">
          {e.card?.mode ?? "—"}
          {e.card?.est_minutes != null ? ` · ~${e.card.est_minutes}m` : ""}
        </span>
      ),
    },
    {
      key: "score",
      label: "Virality",
      sortable: true,
      render: (e) => (
        <span className="font-mono text-xs font-semibold">{e.score ? e.score.toFixed(2) : "—"}</span>
      ),
    },
    {
      key: "sources",
      label: "Sources",
      sortable: false,
      render: (e) => (
        <div className="flex flex-wrap gap-1">
          {(e.sources ?? []).slice(0, 3).map((s) => (
            <Badge key={s.url} tone="muted">{s.kind}</Badge>
          ))}
          {(e.sources ?? []).length === 0 && <span className="text-xs text-danger">none</span>}
        </div>
      ),
    },
    {
      key: "actions",
      label: "Actions",
      sortable: false,
      render: (e) => (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" data-testid="approve-button" onClick={() => void actOne(e.id, "approve")} disabled={busy}>
            Approve
          </Button>
          <Button size="sm" variant="outline" onClick={() => { setAssignFor(e); setAssignee(""); }}>
            Assign
          </Button>
          <Button size="sm" variant="ghost" onClick={() => void actOne(e.id, "reject")} disabled={busy}>
            Reject
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="grid gap-6">
      <WorkHeader
        eyebrow="Plan"
        title="Mission pool"
        status={items.length ? "needs" : "idle"}
        actions={
          <Button data-testid="write-cards" onClick={() => void write()} disabled={busy || !text.trim()}>
            Write cards
          </Button>
        }
      />

      <Card>
        <div className="flex flex-col gap-3">
          <Textarea
            data-testid="questions"
            aria-label="Audience questions, one per line"
            rows={3}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={"One question per line.\nCan you outrun five stars on a bicycle?"}
          />
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={reviewQuestions} disabled={busy || !text.trim()}>
              Review with AI
            </Button>
          </div>
        </div>
      </Card>

      {review && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <Badge tone="accent">Merged</Badge>
                {review.merged.length > 0 && (
                  <Button size="sm" variant="outline" onClick={() => void write(review.merged.map((m) => m.question))} disabled={busy}>
                    Write merged as cards
                  </Button>
                )}
              </div>
              {review.merged.map((m, i) => (
                <div key={i} className="flex justify-between text-sm">
                  <span>{m.question}</span>
                  <span className="text-muted">×{m.count}</span>
                </div>
              ))}
              {review.fallback && <Notice tone="warn">AI unavailable; questions shown as typed.</Notice>}
            </div>
          </Card>
          <Card>
            <div className="flex flex-col gap-2">
              <Badge tone="danger">Policy flags</Badge>
              {review.policy_flags.length === 0 ? (
                <p className="text-sm text-muted">No policy problems found.</p>
              ) : (
                review.policy_flags.map((f, i) => (
                  <div key={i} className="text-sm">
                    <span>{f.question}</span>
                    <span className="text-danger"> — {f.reason}</span>
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>
      )}

      <FilterBar
        aside={
          selected.size > 0 ? (
            <>
              <span className="font-mono text-xs text-muted">{selected.size} selected</span>
              <Button size="sm" variant="outline" onClick={() => void bulk("approve")} disabled={busy}>
                Approve
              </Button>
              <Button size="sm" variant="outline" onClick={() => void bulk("reject")} disabled={busy}>
                Reject
              </Button>
              <Select
                aria-label="Assign selected to"
                value={assignee}
                onChange={(e) => setAssignee(e.target.value)}
                className="w-40"
              >
                <option value="">Assign to…</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.display_name ?? u.email ?? u.id}
                  </option>
                ))}
              </Select>
              <Button size="sm" onClick={() => void bulk("assign", assignee)} disabled={busy || !assignee}>
                Assign
              </Button>
            </>
          ) : undefined
        }
      >
        <Input
          aria-label="Search ideas"
          value={filters.q}
          onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value }))}
          placeholder="Search question or hook…"
          className="sm:w-64"
        />
        <Select
          aria-label="Game"
          value={filters.game_id}
          onChange={(e) => setFilters((f) => ({ ...f, game_id: e.target.value }))}
          className="sm:w-48"
        >
          <option value="">All games</option>
          {games.map((g) => (
            <option key={g.id} value={g.id}>{g.name}</option>
          ))}
        </Select>
        <Select
          aria-label="Source kind"
          value={filters.source}
          onChange={(e) => setFilters((f) => ({ ...f, source: e.target.value }))}
          className="sm:w-40"
        >
          <option value="">Any source</option>
          <option value="youtube">YouTube</option>
          <option value="reddit">Reddit</option>
          <option value="news">News</option>
        </Select>
        <Input
          aria-label="Minimum virality"
          type="number"
          min={0}
          value={filters.min_score}
          onChange={(e) => setFilters((f) => ({ ...f, min_score: e.target.value }))}
          placeholder="Min score"
          className="sm:w-28"
        />
        <Select
          aria-label="Sort by"
          value={filters.sort}
          onChange={(e) => setFilters((f) => ({ ...f, sort: e.target.value }))}
          className="sm:w-40"
        >
          <option value="created_at">Newest</option>
          <option value="score">Virality</option>
        </Select>
      </FilterBar>

      <PageState
        loading={loading}
        error={error}
        empty={!loading && items.length === 0}
        emptyTitle="No dares awaiting review"
        emptyBody="Write cards from audience questions to fill the pool."
      >
        <DataTable
          columns={columns}
          rows={items}
          rowKey={(e) => e.id}
          selected={selected}
          onSelect={toggleSelected}
          onSelectAll={() =>
            setSelected((prev) => (prev.size === items.length ? new Set() : new Set(items.map((e) => e.id))))
          }
          sort={{ key: filters.sort, dir: filters.order as "asc" | "desc" }}
          onSort={(key) =>
            setFilters((f) => ({
              ...f,
              sort: key,
              order: f.sort === key && f.order === "desc" ? "asc" : "desc",
            }))
          }
          expanded={expanded}
          onToggleExpand={toggleExpanded}
          detail={(e) => (
            <div className="grid gap-4 sm:grid-cols-[1fr_14rem]">
              <div className="flex flex-col gap-2">
                <p className="text-sm font-medium">{e.card?.question}</p>
                {e.card?.hook_text && <p className="text-sm text-muted">Hook: {e.card.hook_text}</p>}
                {e.card?.setup && <p className="text-sm text-muted">Setup: {e.card.setup}</p>}
                {e.card?.win_condition && (
                  <p className="text-sm text-muted">Win condition: {e.card.win_condition}</p>
                )}
                {e.card?.title_options?.length ? (
                  <div className="flex flex-col gap-1">
                    <span className="text-[10px] uppercase tracking-[0.18em] text-muted">Title options</span>
                    {e.card.title_options.map((t, i) => (
                      <span key={i} className="text-sm">{t}</span>
                    ))}
                  </div>
                ) : null}
              </div>
              <Sources sources={e.sources} />
            </div>
          )}
        />
        <p className="text-xs text-muted">
          {total} candidate(s). Select rows to approve, reject or assign in bulk.
        </p>
      </PageState>

      <Dialog
        open={Boolean(assignFor)}
        onClose={() => setAssignFor(null)}
        title={`Assign ${assignFor?.id ?? ""}`}
      >
        <div className="flex flex-col gap-4">
          <Select aria-label="Gamer" value={assignee} onChange={(e) => setAssignee(e.target.value)}>
            <option value="">Choose a gamer…</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.display_name ?? u.email ?? u.id}
              </option>
            ))}
          </Select>
          <div className="flex justify-end gap-3">
            <Button variant="ghost" onClick={() => setAssignFor(null)}>
              Cancel
            </Button>
            <Button onClick={assignOne} disabled={!assignee || busy}>
              Assign dare
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}

export function AdminTemplates() {
  const { items, loading, error } = useList(api.adminTemplates);
  return (
    <div className="flex flex-col gap-4">
      <WorkHeader eyebrow="Manage" title="Templates" status="idle" actions={<Metric label="Templates" value={items.length} />} />
      <PageState loading={loading} error={error} empty={items.length === 0}>
        <Table head={["Template", "Weight"]}>
          {(items as { id: string; weight: number }[]).map((t) => (
            <Tr key={t.id}>
              <Td>{t.id}</Td>
              <Td>{t.weight}</Td>
            </Tr>
          ))}
        </Table>
      </PageState>
    </div>
  );
}

export function AdminJobs() {
  const { items, loading, error, reload } = useList(api.adminJobs);
  const toast = useToast();
  async function retry(id: string) {
    try {
      await api.retryJob(id);
      await reload();
      toast("Job requeued", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "danger");
    }
  }
  return (
    <div className="flex flex-col gap-4">
      <WorkHeader
        eyebrow="Manage"
        title="Job queue"
        status={items.some((j) => j.state === "queued" || j.state === "running") ? "running" : items.some((j) => j.state === "failed") ? "failed" : "idle"}
        actions={
          <div className="flex items-center gap-4">
            <Metric label="Failed" value={items.filter((j) => j.state === "failed").length} />
            <Metric
              label="Active"
              value={items.filter((j) => j.state === "queued" || j.state === "running").length}
            />
          </div>
        }
      />
      <PageState loading={loading} error={error} empty={items.length === 0}>
        <Table head={["Kind", "State", "Stage", "Attempts", "Retry", "Error", "Updated", "Actions"]}>
          {items.map((j) => (
            <Tr key={j.id}>
              <Td>{j.kind}</Td>
              <Td><StatusBadge status={j.state === "failed" ? "failed" : j.state === "done" ? "done" : j.state === "queued" || j.state === "running" ? "running" : "idle"} label={j.state} /></Td>
              <Td>{j.stage ?? "—"}</Td>
              <Td>{j.attempts}</Td>
              <Td>{j.retry_count}</Td>
              <Td className="max-w-[20rem] truncate" title={j.error ?? ""}>{j.error ?? "—"}</Td>
              <Td>{j.updated_at.slice(0, 19).replace("T", " ")}</Td>
              <Td>
                {j.state === "failed" && (
                  <Button size="sm" variant="outline" onClick={() => void retry(j.id)}>
                    Retry
                  </Button>
                )}
              </Td>
            </Tr>
          ))}
        </Table>
      </PageState>
    </div>
  );
}

export function AdminAi() {
  const { items, loading, error } = useList(api.adminAiUsage);
  const [config, setConfig] = useState<AiConfig | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);
  useEffect(() => {
    api.adminAiConfig().then(setConfig).catch(() => setConfigError("Could not load the AI configuration."));
  }, []);
  const tokens = items.reduce((n, u) => n + u.prompt_tokens + u.completion_tokens, 0);
  const avg = items.length
    ? Math.round(items.reduce((n, u) => n + u.latency_ms, 0) / items.length)
    : null;
  return (
    <div className="flex flex-col gap-6">
      <WorkHeader
        eyebrow="Manage"
        title="AI usage"
        status={config?.configured ? "done" : "needs"}
        actions={
          <div className="flex items-center gap-4">
            <Metric label="Calls" value={items.length} />
            <Metric label="Tokens" value={tokens.toLocaleString()} />
            <Metric label="Avg. latency" value={avg != null ? `${avg} ms` : "—"} />
            <Metric label="Fallbacks" value={items.filter((u) => u.fallback).length} />
          </div>
        }
      />
      <PageState loading={false} error={configError} empty={false}>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <div className="flex flex-col gap-2">
              <span className="text-[10px] uppercase tracking-[0.18em] text-muted">Provider</span>
              <span className="font-mono text-sm font-semibold">{config?.provider ?? "—"}</span>
              <span className="text-xs text-muted">{config?.base_url || "no base URL"}</span>
            </div>
          </Card>
          <Card>
            <div className="flex flex-col gap-2">
              <span className="text-[10px] uppercase tracking-[0.18em] text-muted">Model</span>
              <span className="font-mono text-sm font-semibold">{config?.model || "—"}</span>
              <span className="text-xs text-muted">{config?.key_present ? "key present" : "no key"}</span>
            </div>
          </Card>
          <Card>
            <div className="flex flex-col gap-2">
              <span className="text-[10px] uppercase tracking-[0.18em] text-muted">Configured</span>
              <StatusBadge status={config?.configured ? "done" : "needs"} label={config?.configured ? "yes" : "no"} />
              <span className="text-xs text-muted">provider · base URL · model · key</span>
            </div>
          </Card>
          <Card>
            <div className="flex flex-col gap-2">
              <span className="text-[10px] uppercase tracking-[0.18em] text-muted">Live vs fallback</span>
              <span className="font-mono text-sm font-semibold">
                {items.filter((u) => !u.fallback).length} / {items.length}
              </span>
              <span className="text-xs text-muted">live calls</span>
            </div>
          </Card>
        </div>
      </PageState>
      <PageState
        loading={loading}
        error={error}
        empty={items.length === 0}
        emptyTitle="No AI calls yet"
        emptyBody="Calls are recorded when a page uses the AI."
      >
        <Table head={["When", "Page", "Kind", "Provider", "Model", "Tokens", "Latency", "Fallback"]}>
          {items.map((u) => (
            <Tr key={u.id}>
              <Td>{u.created_at.slice(0, 19).replace("T", " ")}</Td>
              <Td>{u.page}</Td>
              <Td>{u.kind}</Td>
              <Td>{u.provider}</Td>
              <Td>{u.model}</Td>
              <Td>{u.prompt_tokens + u.completion_tokens}</Td>
              <Td>{u.latency_ms} ms</Td>
              <Td>{u.fallback ? <Badge tone="danger">fallback</Badge> : <Badge tone="success">live</Badge>}</Td>
            </Tr>
          ))}
        </Table>
      </PageState>
    </div>
  );
}

export function AdminAudit() {
  const { items, loading, error } = useList(api.adminAudit);
  return (
    <div className="flex flex-col gap-4">
      <WorkHeader eyebrow="Manage" title="Audit log" status="idle" actions={<Metric label="Entries" value={items.length} />} />
      <PageState loading={loading} error={error} empty={items.length === 0}>
        <Table head={["When", "Actor", "Action", "Target", "Detail"]}>
        {items.map((a) => (
          <Tr key={a.id}>
            <Td>{a.created_at.slice(0, 19).replace("T", " ")}</Td>
            <Td>{a.actor_name ?? a.actor_id?.slice(0, 8) ?? "—"}</Td>
            <Td>{a.action}</Td>
            <Td>{a.target_type ? `${a.target_type}:${a.target_id}` : "—"}</Td>
            <Td className="max-w-[20rem] truncate" title={JSON.stringify(a.meta)}>
              {Object.entries(a.meta ?? {})
                .map(([k, v]) => `${k}=${typeof v === "string" ? v : JSON.stringify(v)}`)
                .join(" · ") || "—"}
            </Td>
          </Tr>
        ))}
        </Table>
      </PageState>
    </div>
  );
}

export function AdminSetup() {
  const [checks, setChecks] = useState<{ name: string; ok: boolean; detail: string }[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [config, setConfig] = useState<AiConfig | null>(null);
  const [storage, setStorage] = useState<{ driver: string; bytes: number } | null>(null);

  useEffect(() => {
    Promise.all([api.adminSetup(), api.adminAiConfig(), api.adminStorage()])
      .then(([s, c, st]) => {
        setChecks(s.checks);
        setConfig(c);
        setStorage(st);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  const failing = checks?.filter((c) => !c.ok) ?? [];
  const passingCount = (checks?.length ?? 0) - failing.length;
  const groups = [
    {
      name: "Failing",
      items: failing,
    },
    { name: "Database", items: (checks ?? []).filter((c) => /database/i.test(c.name)) },
    { name: "AI provider", items: (checks ?? []).filter((c) => /LLM|AI /i.test(c.name)) },
    { name: "Research sources", items: (checks ?? []).filter((c) => /research/i.test(c.name)) },
    { name: "Storage", items: (checks ?? []).filter((c) => /storage/i.test(c.name)) },
    {
      name: "Security",
      items: (checks ?? []).filter((c) => /SESSION_SECRET/.test(c.name)),
    },
    {
      name: "Worker",
      items: (checks ?? []).filter((c) => /worker|TTS|voice/i.test(c.name)),
    },
    {
      name: "Web",
      items: (checks ?? []).filter((c) => /WEB_ORIGIN/.test(c.name)),
    },
  ].filter((g) => g.items.length > 0);
  const grouped = new Set(groups.flatMap((g) => g.items.map((c) => c.name)));
  const other = (checks ?? []).filter((c) => !grouped.has(c.name));
  if (other.length) groups.push({ name: "Other", items: other });

  return (
    <div className="grid gap-6">
      <WorkHeader
        eyebrow="Manage"
        title="Setup status"
        status={loading ? "idle" : failing.length ? "failed" : "done"}
        actions={
          <span className="font-mono text-xs text-muted">
            {passingCount}/{checks?.length ?? 0} checks passing
          </span>
        }
      />
      <AdminKeys />
      <PageState
        loading={loading}
        error={error}
        empty={checks !== null && checks.length === 0}
        emptyTitle="No checks"
        emptyBody="The setup checks did not return anything."
      >
        <div className="grid gap-4 sm:grid-cols-3">
          <Card>
            <div className="flex flex-col gap-2">
              <span className="text-[10px] uppercase tracking-[0.18em] text-muted">Provider</span>
              <span className="font-mono text-sm font-semibold">{config?.provider ?? "—"}</span>
              <span className="text-xs text-muted">{config?.model || "no model"}</span>
            </div>
          </Card>
          <Card>
            <div className="flex flex-col gap-2">
              <span className="text-[10px] uppercase tracking-[0.18em] text-muted">AI key</span>
              <StatusBadge status={config?.key_present ? "done" : "needs"} label={config?.key_present ? "present" : "missing"} />
              <span className="text-xs text-muted">{config?.configured ? "configured" : "not configured"}</span>
            </div>
          </Card>
          <Card>
            <div className="flex flex-col gap-2">
              <span className="text-[10px] uppercase tracking-[0.18em] text-muted">Storage</span>
              <span className="font-mono text-sm font-semibold">
                {storage ? `${(storage.bytes / 1_000_000).toFixed(1)} MB` : "—"}
              </span>
              <span className="text-xs text-muted">{storage?.driver ?? "unknown"}</span>
            </div>
          </Card>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          {groups.map((group) => (
            <Card key={group.name}>
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase tracking-[0.18em] text-muted">{group.name}</span>
                  <span className="font-mono text-xs text-muted">
                    {group.items.filter((c) => c.ok).length}/{group.items.length}
                  </span>
                </div>
                {group.items.map((c) => (
                  <div key={c.name} className="flex items-start justify-between gap-4">
                    <span className="flex items-start gap-2 text-sm">
                      <StatusBadge status={c.ok ? "done" : "failed"} label={c.ok ? "PASS" : "FAIL"} />
                      <span>{c.name}</span>
                    </span>
                    {c.detail && <span className="text-right text-xs text-muted">{c.detail}</span>}
                  </div>
                ))}
              </div>
            </Card>
          ))}
        </div>
      </PageState>
    </div>
  );
}
