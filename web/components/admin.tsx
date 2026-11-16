"use client";

import { useState } from "react";
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
  const toast = useToast();

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
          <Tr>
            <Td>blur_fit</Td>
            <Td>1</Td>
          </Tr>
          <Tr>
            <Td>center_crop</Td>
            <Td>1</Td>
          </Tr>
        </Table>
      )}

      {tab === "users" && (
        <Table head={["User", "Role", "Plan"]}>
          <Tr>
            <Td>Dev Creator</Td>
            <Td>creator</Td>
            <Td>free</Td>
          </Tr>
        </Table>
      )}

      {tab === "jobs" && (
        <EmptyState title="No queued jobs" body="Jobs appear while clips render." />
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
