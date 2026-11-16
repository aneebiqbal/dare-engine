import { Page } from "@/components/page";
import { Badge, Card, EmptyState, Table, Td, Tr } from "@/components/ui";
import { api, type HistoryEntry } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HistoryPage() {
  let rows: HistoryEntry[] = [];
  let error: string | null = null;
  try {
    rows = await api.history();
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load history";
  }

  return (
    <Page eyebrow="History" title="Mission history">
      {error ? (
        <Card>
          <p className="text-sm text-danger">{error}</p>
        </Card>
      ) : rows.length === 0 ? (
        <EmptyState title="No missions yet" body="Accept a mission to start your history." />
      ) : (
        <Table head={["Mission", "Date", "State", "Result"]}>
          {rows.map((r) => (
            <Tr key={`${r.mission_id}-${r.date}`}>
              <Td>{r.mission_id}</Td>
              <Td>{r.date}</Td>
              <Td>
                <Badge tone={r.state === "done" ? "success" : "muted"}>{r.state}</Badge>
              </Td>
              <Td>{r.result_value ?? "—"}</Td>
            </Tr>
          ))}
        </Table>
      )}
    </Page>
  );
}
