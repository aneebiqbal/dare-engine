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
  type SystemLoad,
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
  const [users, setUsers] = useState<User[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [pool, setPool] = useState<PoolEntry[]>([]);
  const [usage, setUsage] = useState<AiUsage[]>([]);
  const [errors, setErrors] = useState<ErrorReport[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [storage, setStorage] = useState<{ driver: string; bytes: number } | null>(null);
  const [setup, setSetup] = useState<{ name: string; ok: boolean; detail: string }[]>([]);
  const [health, setHealth] = useState<SystemLoad | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.adminUsers(),
      api.adminInvites(),
      api.adminJobs("?page_size=50"),
      api.pool(),
      api.adminAiUsage(),
      api.adminStorage(),
      api.projects(),
    ])
      .then(([u, i, j, p, a, s, pr]) => {
        setUsers(u.items);
        setInvites(i.items);
        setJobs(j.items);
        setPool(p.items);
        setUsage(a.items);
        setStorage(s);
        setProjects(pr.items);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  // The doctor checks and the live system probe are slow (seconds); stream them
  // in after the main dashboard so nothing waits on them.
  useEffect(() => {
    Promise.all([api.adminSetup(), api.studioSystem().catch(() => null), api.adminErrors()])
      .then(([st, h, e]) => {
        setSetup(st.checks);
        setHealth(h);
        setErrors(e.items);
      })
      .catch(() => {});
  }, []);

  const failed = jobs.filter((j) => j.state === "failed").length;
  const running = jobs.filter((j) => j.state === "running" || j.state === "queued").length;
  const fallback = usage.filter((u) => u.fallback).length;
  const tokens = usage.reduce((n, u) => n + u.prompt_tokens + u.completion_tokens, 0);
  const avgLatency = usage.length
    ? Math.round(usage.reduce((n, u) => n + u.latency_ms, 0) / usage.length)
    : null;
  const activeJobs = jobs.filter(
    (j) => j.state === "failed" || j.state === "running" || j.state === "queued",
  );

  return (
    <div className="grid gap-6" data-tour="admin-overview">
      <PageState loading={loading} error={error} empty={false}>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Link href="/admin/users"><Card><Stat label="Users" value={users.length} /></Card></Link>
          <Link href="/admin/invites">
            <Card>
              <Stat label="Invites" value={invites.length} hint={`${invites.filter((i) => !i.used && !i.revoked).length} open`} />
            </Card>
          </Link>
          <Link href="/admin/jobs"><Card><Stat label="Jobs" value={running} hint={`${failed} failed`} /></Card></Link>
          <Link href="/admin/projects">
            <Card>
              <Stat
                label="Projects"
                value={projects.length}
                hint={
                  projects.length
                    ? `${projects.filter((p) => p.stage === "exported").length} exported`
                    : "none yet"
                }
              />
            </Card>
          </Link>
          <Link href="/admin/pool"><Card><Stat label="Dares awaiting review" value={pool.length} /></Card></Link>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Link href="/admin/ai">
            <Card>
              <Stat label="AI calls" value={usage.length} hint={`${fallback} fallbacks`} />
            </Card>
          </Link>
          <Card>
            <Stat
              label="Storage"
              value={storage ? `${(storage.bytes / 1_000_000).toFixed(1)} MB` : "—"}
              hint={storage?.driver}
            />
          </Card>
          <Link href="/admin/setup">
            <Card>
              <Stat
                label="Setup"
                value={`${setup.filter((c) => c.ok).length}/${setup.length}`}
                hint="checks passing"
              />
            </Card>
          </Link>
          <Card>
            <Stat
              label="System"
              value={health && Number.isFinite(health.cpu_percent) ? `${Math.round(health.cpu_percent)}%` : "—"}
              hint={
                health && Number.isFinite(health.memory_percent)
                  ? `CPU · ${Math.round(health.memory_percent)}% memory`
                  : "unavailable"
              }
            />
          </Card>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card><Stat label="Tokens" value={tokens.toLocaleString()} hint="prompt + completion" /></Card>
          <Card>
            <Stat label="Avg. latency" value={avgLatency != null ? `${avgLatency} ms` : "—"} hint="per AI call" />
          </Card>
          <Card>
            <Stat
              label="GPU"
              value={
                health?.gpu && Number.isFinite(health.gpu.utilization_percent)
                  ? `${Math.round(health.gpu.utilization_percent)}%`
                  : "—"
              }
              hint={
                health?.gpu && Number.isFinite(health.gpu.memory_used_mb)
                  ? `${health.gpu.memory_used_mb}/${health.gpu.memory_total_mb} MB`
                  : "not detected"
              }
            />
          </Card>
          <Card>
            <Stat label="Failed jobs" value={failed} hint={failed ? "needs attention" : "clear"} />
          </Card>
        </div>
      </PageState>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <div className="flex flex-col gap-3">
            <h2 className="text-base font-medium">Job queue</h2>
            {activeJobs.length === 0 ? (
              <p className="text-sm text-muted">No active or failed jobs.</p>
            ) : (
              activeJobs.slice(0, 6).map((j) => (
                <div key={j.id} className="flex items-center justify-between gap-3 text-sm">
                  <span className="truncate">{j.kind}</span>
                  <span className="text-muted">{j.stage ?? "—"}</span>
                  <Badge tone={j.state === "failed" ? "danger" : "muted"}>{j.state}</Badge>
                </div>
              ))
            )}
          </div>
        </Card>
        <Card>
          <div className="flex flex-col gap-3">
            <h2 className="text-base font-medium">Recent AI calls</h2>
            {usage.slice(0, 5).length === 0 ? (
              <p className="text-sm text-muted">No AI calls yet.</p>
            ) : (
              usage.slice(0, 5).map((u) => (
                <div key={u.id} className="flex items-center justify-between text-sm">
                  <span>{u.page} · {u.kind}</span>
                  <span className="text-muted">
                    {u.prompt_tokens + u.completion_tokens} tokens · {u.latency_ms} ms
                  </span>
                </div>
              ))
            )}
          </div>
        </Card>
        <Card>
          <div className="flex flex-col gap-3">
            <h2 className="text-base font-medium">Recent client errors</h2>
            {errors.length === 0 ? (
              <p className="text-sm text-muted">No browser errors reported.</p>
            ) : (
              errors.slice(0, 5).map((e) => (
                <div key={e.id} className="flex flex-col gap-1 text-sm">
                  <span className="truncate">{e.message}</span>
                  <span className="text-xs text-muted">
                    {e.path ?? "—"} · {new Date(e.created_at).toLocaleString()}
                  </span>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      <Card>
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-medium">Projects</h2>
            <Link href="/admin/projects" className="text-xs text-accent hover:underline">
              View all
            </Link>
          </div>
          {projects.length === 0 ? (
            <p className="text-sm text-muted">
              No projects yet. Import a recording to start one.
            </p>
          ) : (
            projects.slice(0, 5).map((p) => (
              <Link
                key={p.id}
                href="/admin/projects"
                className="flex items-center justify-between gap-3 text-sm"
              >
                <span className="truncate">{p.name}</span>
                <span className="text-muted">{p.stage.replace(/_/g, " ")}</span>
                <span className="w-16 text-right text-muted">{p.progress}%</span>
              </Link>
            ))
          )}
        </div>
      </Card>
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
  const { items, loading, error, reload } = useList(api.pool);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [review, setReview] = useState<PoolReview | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [assignFor, setAssignFor] = useState<PoolEntry | null>(null);
  const [assignee, setAssignee] = useState("");
  const toast = useToast();

  async function write(questions?: string[]) {
    const list = questions ?? text.split("\n").map((q) => q.trim()).filter(Boolean);
    if (!list.length) return;
    setBusy(true);
    try {
      await api.writeCards(list);
      setText("");
      await reload();
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

  async function approve(id: string) {
    try {
      await api.approve(id);
      await reload();
      toast("Dare approved", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not approve", "danger");
    }
  }

  async function reject(id: string) {
    try {
      await api.reject(id);
      await reload();
      toast("Dare rejected", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not reject", "danger");
    }
  }

  async function openAssign(entry: PoolEntry) {
    setAssignFor(entry);
    setAssignee("");
    try {
      const res = await api.adminUsers("?page_size=100");
      setUsers(res.items.filter((u) => u.role !== "admin"));
    } catch {
      setUsers([]);
    }
  }

  async function assign() {
    if (!assignFor || !assignee) return;
    try {
      await api.assign(assignFor.id, assignee);
      toast("Dare assigned", "success");
      setAssignFor(null);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not assign", "danger");
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <div className="flex flex-col gap-4">
          <Textarea
            data-testid="questions"
            aria-label="Audience questions, one per line"
            rows={5}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={"One question per line.\nCan you outrun five stars on a bicycle?"}
          />
          <div className="flex flex-wrap gap-2">
            <Button data-testid="write-cards" onClick={() => void write()} disabled={busy}>
              Write cards
            </Button>
            <Button variant="outline" onClick={reviewQuestions} disabled={busy}>
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

      <PageState
        loading={loading}
        error={error}
        empty={items.length === 0}
        emptyTitle="No dares awaiting review"
        emptyBody="Write cards from audience questions to fill the pool."
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((entry) => (
            <Card key={entry.id}>
              <div className="flex h-full flex-col gap-3">
                <div className="flex items-center justify-between">
                  <Badge tone="accent">{entry.id}</Badge>
                  <Badge tone={entry.state === "candidate" ? "muted" : "success"}>{entry.state}</Badge>
                </div>
                <h3 className="text-base font-medium leading-snug">{entry.card?.question ?? "Untitled"}</h3>
                <p className="text-sm text-muted">{entry.card?.hook_text}</p>
                <Sources sources={entry.sources} />
                <div className="mt-auto flex gap-2 pt-2">
                  <Button size="sm" data-testid="approve-button" onClick={() => void approve(entry.id)}>
                    Approve
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => void openAssign(entry)}>
                    Assign
                  </Button>
                  <Button size="sm" variant="danger" onClick={() => void reject(entry.id)}>
                    Reject
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
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
            <Button onClick={assign} disabled={!assignee || busy}>
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
    <PageState loading={loading} error={error} empty={items.length === 0}>
      <Table head={["Kind", "State", "Stage", "Attempts", "Retry", "Error", "Updated", "Actions"]}>
        {items.map((j) => (
          <Tr key={j.id}>
            <Td>{j.kind}</Td>
            <Td><Badge tone={j.state === "failed" ? "danger" : j.state === "done" ? "success" : "muted"}>{j.state}</Badge></Td>
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
      <PageState loading={false} error={configError} empty={false}>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <Stat label="Provider" value={config?.provider ?? "—"} hint={config ? (config.configured ? "configured" : "not configured") : undefined} />
          </Card>
          <Card><Stat label="Model" value={config?.model || "—"} /></Card>
          <Card><Stat label="Key present" value={config ? (config.key_present ? "yes" : "no") : "—"} /></Card>
          <Card><Stat label="Base URL" value={config?.base_url ?? "—"} /></Card>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card><Stat label="Calls" value={items.length} /></Card>
          <Card><Stat label="Tokens" value={tokens.toLocaleString()} hint="prompt + completion" /></Card>
          <Card><Stat label="Avg. latency" value={avg != null ? `${avg} ms` : "—"} /></Card>
          <Card><Stat label="Fallbacks" value={items.filter((u) => u.fallback).length} /></Card>
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

  return (
    <div className="grid gap-6">
      <PageState
        loading={loading}
        error={error}
        empty={checks !== null && checks.length === 0}
        emptyTitle="No checks"
        emptyBody="The setup checks did not return anything."
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card><Stat label="Provider" value={config?.provider ?? "—"} /></Card>
          <Card><Stat label="Model" value={config?.model || "—"} /></Card>
          <Card><Stat label="Key present" value={config ? (config.key_present ? "yes" : "no") : "—"} /></Card>
          <Card><Stat label="Storage" value={storage ? `${(storage.bytes / 1_000_000).toFixed(1)} MB` : "—"} /></Card>
        </div>
        <Card>
          <div className="flex flex-col gap-3">
            {checks?.map((c) => (
              <div key={c.name} className="flex items-center justify-between gap-4">
                <span className="text-sm">
                  <Badge tone={c.ok ? "success" : "danger"}>{c.ok ? "PASS" : "FAIL"}</Badge>{" "}
                  {c.name}
                </span>
                <span className="text-xs text-muted">{c.detail}</span>
              </div>
            ))}
          </div>
        </Card>
      </PageState>
    </div>
  );
}
