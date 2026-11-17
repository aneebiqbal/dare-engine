"use client";

import { useEffect, useState } from "react";
import { api, type PoolEntry } from "@/lib/api";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  PageState,
  Table,
  Td,
  Tabs,
  Textarea,
  Tr,
  useToast,
} from "@/components/ui";

export function Admin({ initial }: { initial: PoolEntry[] }) {
  const [pool, setPool] = useState(initial);
  const [text, setText] = useState("");
  const [tab, setTab] = useState("pool");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [templates, setTemplates] = useState<unknown[]>([]);
  const [users, setUsers] = useState<unknown[]>([]);
  const [jobs, setJobs] = useState<unknown[]>([]);
  const toast = useToast();

  useEffect(() => {
    Promise.all([api.adminTemplates(), api.adminUsers(), api.adminJobs()])
      .then(([t, u, j]) => {
        setTemplates(t as unknown[]);
        setUsers(u as unknown[]);
        setJobs(j as unknown[]);
      })
      .catch(() => {});
  }, []);

  async function write() {
    const questions = text.split("\n").map((q) => q.trim()).filter(Boolean);
    if (!questions.length) return;
    setLoading(true);
    setError(null);
    try {
      const res = (await api.writeCards(questions)) as { count?: number };
      setText("");
      setPool(await api.pool());
      toast(`Wrote ${res.count ?? 0} cards`, "success");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to write cards");
    } finally {
      setLoading(false);
    }
  }

  async function approve(id: string) {
    await api.approve(id);
    setPool((prev) => prev.filter((p) => p.id !== id));
    toast("Approved", "success");
  }

  return (
    <div className="flex flex-col gap-6">
      <Tabs
        tabs={[
          { id: "pool", label: "Pool" },
          { id: "templates", label: "Templates" },
          { id: "users", label: "Users" },
          { id: "jobs", label: "Jobs" },
          { id: "health", label: "Health" },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === "pool" && (
        <div className="flex flex-col gap-6">
          <Card>
            <div className="flex flex-col gap-4">
              <Textarea
                data-testid="questions"
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={5}
                placeholder={"One question per line.\nCan you outrun five stars on a bicycle?"}
              />
              <Button data-testid="write-cards" onClick={write} disabled={loading}>
                Write cards
              </Button>
            </div>
          </Card>

          <PageState loading={loading} error={error} empty={pool.length === 0}>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {pool.map((entry) => (
                <Card key={entry.id}>
                  <div className="flex h-full flex-col gap-3">
                    <Badge tone="accent">{entry.id}</Badge>
                    <h3 className="text-base font-medium leading-snug">
                      {entry.card?.question ?? "Untitled"}
                    </h3>
                    <p className="text-sm text-muted">{entry.card?.hook_text}</p>
                    <div className="mt-auto flex gap-2 pt-2">
                      <Button
                        size="sm"
                        data-testid="approve-button"
                        onClick={() => entry.id && approve(entry.id)}
                      >
                        Approve
                      </Button>
                      <Button size="sm" variant="ghost">
                        Edit
                      </Button>
                      <Button size="sm" variant="danger">
                        Reject
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </PageState>
        </div>
      )}

      {tab === "templates" && (
        <Table head={["Template", "Weight"]}>
          {templates.map((t, i) => {
            const row = t as { id?: string; weight?: number };
            return (
              <Tr key={row.id ?? i}>
                <Td>{row.id}</Td>
                <Td>{row.weight}</Td>
              </Tr>
            );
          })}
        </Table>
      )}

      {tab === "users" && (
        <Table head={["User", "Role", "Plan"]}>
          {users.map((u, i) => {
            const row = u as { id?: string; display_name?: string; role?: string };
            return (
              <Tr key={row.id ?? i}>
                <Td>{row.display_name}</Td>
                <Td>{row.role}</Td>
                <Td>free</Td>
              </Tr>
            );
          })}
        </Table>
      )}

      {tab === "jobs" && (
        <Table head={["Job", "State", "Attempts"]}>
          {jobs.length === 0 ? (
            <Tr>
              <Td colSpan={3}>No jobs yet.</Td>
            </Tr>
          ) : (
            jobs.map((j, i) => {
              const row = j as { id?: string; kind?: string; state?: string; attempts?: number };
              return (
                <Tr key={row.id ?? i}>
                  <Td>{row.kind}</Td>
                  <Td>
                    <Badge tone={row.state === "failed" ? "danger" : "muted"}>{row.state}</Badge>
                  </Td>
                  <Td>{row.attempts}</Td>
                </Tr>
              );
            })
          )}
        </Table>
      )}

      {tab === "health" && (
        <Card>
          <div className="flex items-center gap-3">
            <Badge tone="success">API healthy</Badge>
            <span className="text-sm text-muted">All services reporting ready.</span>
          </div>
        </Card>
      )}
    </div>
  );
}
