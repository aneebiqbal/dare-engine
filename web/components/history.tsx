"use client";

import { useState } from "react";
import { api, type HistoryEntry } from "@/lib/api";
import { Badge, Card, EmptyState, PageState, Table, Td, Tr } from "@/components/ui";

export function History({ initial }: { initial: HistoryEntry[] }) {
  const [rows, setRows] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      setRows((await api.history()).items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load history");
    } finally {
      setLoading(false);
    }
  }

  if (error) {
    return (
      <Card>
        <p className="text-sm text-danger">{error}</p>
      </Card>
    );
  }
  if (rows.length === 0) {
    return <EmptyState title="No missions yet" body="Accept a mission to start your history." />;
  }

  return (
    <Table head={["Mission", "Date", "State", "Result", "Clip"]}>
      {rows.map((r) => (
        <Tr key={`${r.mission_id}-${r.date}-${r.clip_id ?? ""}`}>
          <Td>{r.mission_id}</Td>
          <Td>{r.date}</Td>
          <Td>
            <Badge tone={r.state === "done" ? "success" : "muted"}>{r.state}</Badge>
          </Td>
          <Td>{r.result_value ?? "—"}</Td>
          <Td>
            {r.clip_id ? (
              <a href={`/clips/${r.clip_id}`} className="text-accent hover:underline">
                {r.clip_state ?? "view"}
              </a>
            ) : (
              "—"
            )}
          </Td>
        </Tr>
      ))}
    </Table>
  );
}
