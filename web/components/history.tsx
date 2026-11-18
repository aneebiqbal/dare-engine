"use client";

import { useEffect, useRef, useState } from "react";
import { api, type HistoryEntry } from "@/lib/api";
import { Badge, Input, PageState, Table, Td, Tr } from "@/components/ui";

export function History({ initial }: { initial: HistoryEntry[] }) {
  const [rows, setRows] = useState(initial);
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const first = useRef(true);

  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    const handle = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await api.history(`?page_size=100${q.trim() ? `&q=${encodeURIComponent(q.trim())}` : ""}`);
        setRows(res.items);
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load history");
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => clearTimeout(handle);
  }, [q]);

  return (
    <div className="flex flex-col gap-4">
      <Input
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search by dare or question"
        aria-label="Search history"
        data-testid="history-search"
      />
      <PageState
        loading={loading}
        error={error}
        empty={rows.length === 0}
        emptyTitle={q ? "No matching sessions" : "No sessions yet"}
        emptyBody={q ? `Nothing matches “${q}”.` : "Accept a dare to start your history."}
      >
        <Table caption="Past sessions and dares" head={["Dare", "Question", "Date", "State", "Result", "Clip"]}>
          {rows.map((r) => (
            <Tr key={`${r.mission_id}-${r.date}-${r.clip_id ?? ""}`}>
              <Td>{r.mission_id}</Td>
              <Td>{r.question ?? "—"}</Td>
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
      </PageState>
    </div>
  );
}
