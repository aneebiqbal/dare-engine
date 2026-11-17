"use client";

import { useCallback, useEffect, useState } from "react";
import {
  api,
  type AiConfig,
  type AiUsage,
  type AuditEntry,
  type Invite,
  type Job,
  type PoolEntry,
  type User,
} from "@/lib/api";
import {
  Badge,
  Button,
  Card,
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
  const [storage, setStorage] = useState<{ driver: string; bytes: number } | null>(null);
  const [setup, setSetup] = useState<{ name: string; ok: boolean; detail: string }[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.adminUsers(),
      api.adminInvites(),
      api.adminJobs("?page_size=50"),
      api.pool(),
      api.adminAiUsage(),
      api.adminStorage(),
      api.adminSetup(),
    ])
      .then(([u, i, j, p, a, s, st]) => {
        setUsers(u.items);
        setInvites(i.items);
        setJobs(j.items);
        setPool(p.items);
        setUsage(a.items);
        setStorage(s);
        setSetup(st.checks);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  const failed = jobs.filter((j) => j.state === "failed").length;
  const running = jobs.filter((j) => j.state === "running" || j.state === "queued").length;
  const fallback = usage.filter((u) => u.fallback).length;

  return (
    <div className="grid gap-6" data-tour="admin-overview">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card><Stat label="Users" value={users.length} /></Card>
        <Card><Stat label="Invites" value={invites.length} hint={`${invites.filter((i) => !i.used && !i.revoked).length} open`} /></Card>
        <Card><Stat label="Jobs" value={running} hint={`${failed} failed`} /></Card>
        <Card><Stat label="Pool" value={pool.length} hint="awaiting review" /></Card>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card><Stat label="AI calls" value={usage.length} hint={`${fallback} fallbacks`} /></Card>
        <Card>
          <Stat
            label="Storage"
            value={storage ? `${(storage.bytes / 1_000_000).toFixed(1)} MB` : "—"}
            hint={storage?.driver}
          />
        </Card>
        <Card>
          <Stat
            label="Setup"
            value={`${setup.filter((c) => c.ok).length}/${setup.length}`}
            hint="checks passing"
          />
        </Card>
        <Card>
          <Stat label="Failed jobs" value={failed} hint={failed ? "needs attention" : "clear"} />
        </Card>
      </div>
      {error && <Notice tone="warn">{error}</Notice>}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <div className="flex flex-col gap-3">
            <h2 className="text-base font-medium">Recent jobs</h2>
            {jobs.filter((j) => j.state === "failed" || j.state === "running" || j.state === "queued").length === 0 ? (
              <p className="text-sm text-muted">No active or failed jobs.</p>
            ) : (
              jobs
                .filter((j) => j.state === "failed" || j.state === "running" || j.state === "queued")
                .slice(0, 5)
                .map((j) => (
                  <div key={j.id} className="flex items-center justify-between text-sm">
                    <span>{j.kind}</span>
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
                  <span className="text-muted">{u.latency_ms} ms</span>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>
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
                <Select value={u.role} onChange={(e) => void setRole(u.id, e.target.value)}>
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
    await api.adminRevokeInvite(id).catch(() => {});
    await reload();
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
              <Td><code>{i.code}</code></Td>
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

export function AdminPool() {
  const { items, loading, error, reload } = useList(api.pool);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [review, setReview] = useState<{ merged: { question: string; count: number }[]; policy_flags: { question: string; reason: string }[]; fallback: boolean } | null>(null);
  const toast = useToast();

  async function write() {
    const questions = text.split("\n").map((q) => q.trim()).filter(Boolean);
    if (!questions.length) return;
    setBusy(true);
    try {
      await api.writeCards(questions);
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
    await api.approve(id);
    await reload();
  }

  async function reject(id: string) {
    await api.reject(id);
    await reload();
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <div className="flex flex-col gap-4">
          <Textarea
            data-testid="questions"
            rows={5}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={"One question per line.\nCan you outrun five stars on a bicycle?"}
          />
          <div className="flex flex-wrap gap-2">
            <Button data-testid="write-cards" onClick={write} disabled={busy}>Write cards</Button>
            <Button variant="outline" onClick={reviewQuestions} disabled={busy}>Review with AI</Button>
          </div>
        </div>
      </Card>

      {review && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <div className="flex flex-col gap-2">
              <Badge tone="accent">Merged</Badge>
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

      <PageState loading={loading} error={error} empty={items.length === 0}>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((entry) => (
            <Card key={entry.id}>
              <div className="flex h-full flex-col gap-3">
                <Badge tone="accent">{entry.id}</Badge>
                <h3 className="text-base font-medium leading-snug">{entry.card?.question ?? "Untitled"}</h3>
                <p className="text-sm text-muted">{entry.card?.hook_text}</p>
                <div className="mt-auto flex gap-2 pt-2">
                  <Button size="sm" data-testid="approve-button" onClick={() => void approve(entry.id)}>
                    Approve
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
      <Table head={["Kind", "State", "Attempts", "Retry", "Error", "Updated", "Actions"]}>
        {items.map((j) => (
          <Tr key={j.id}>
            <Td>{j.kind}</Td>
            <Td><Badge tone={j.state === "failed" ? "danger" : j.state === "done" ? "success" : "muted"}>{j.state}</Badge></Td>
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
  useEffect(() => {
    api.adminAiConfig().then(setConfig).catch(() => {});
  }, []);
  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card><Stat label="Provider" value={config?.provider ?? "—"} /></Card>
        <Card><Stat label="Model" value={config?.model || "—"} /></Card>
        <Card><Stat label="Key present" value={config ? (config.key_present ? "yes" : "no") : "—"} /></Card>
        <Card><Stat label="Base URL" value={config?.base_url ?? "—"} /></Card>
      </div>
      <PageState loading={loading} error={error} empty={items.length === 0}>
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
            <Td>{a.actor_id?.slice(0, 8) ?? "—"}</Td>
            <Td>{a.action}</Td>
            <Td>{a.target_type ? `${a.target_type}:${a.target_id}` : "—"}</Td>
            <Td className="max-w-[20rem] truncate" title={JSON.stringify(a.meta)}>
              {JSON.stringify(a.meta)}
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
  const [config, setConfig] = useState<AiConfig | null>(null);
  const [storage, setStorage] = useState<{ driver: string; bytes: number } | null>(null);

  useEffect(() => {
    Promise.all([api.adminSetup(), api.adminAiConfig(), api.adminStorage()])
      .then(([s, c, st]) => {
        setChecks(s.checks);
        setConfig(c);
        setStorage(st);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  return (
    <div className="grid gap-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card><Stat label="Provider" value={config?.provider ?? "—"} /></Card>
        <Card><Stat label="Model" value={config?.model || "—"} /></Card>
        <Card><Stat label="Key present" value={config ? (config.key_present ? "yes" : "no") : "—"} /></Card>
        <Card><Stat label="Storage" value={storage ? `${(storage.bytes / 1_000_000).toFixed(1)} MB` : "—"} /></Card>
      </div>
      {error && <Notice tone="warn">{error}</Notice>}
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
    </div>
  );
}
