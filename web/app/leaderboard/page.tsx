import { Page } from "@/components/page";
import { Badge, Card, EmptyState, Table, Td, Tr } from "@/components/ui";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function LeaderboardPage() {
  let rows: { rank: number; user_id: string; result_value: number | null }[] = [];
  let error: string | null = null;
  try {
    rows = (await api.leaderboard("m_0214")).items;
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load";
  }

  return (
    <Page eyebrow="Leaderboard" title="Daily Mission board">
      {error ? (
        <Card>
          <p className="text-sm text-danger">{error}</p>
        </Card>
      ) : rows.length === 0 ? (
        <EmptyState title="No attempts yet" body="Be the first to complete the Daily Mission." />
      ) : (
        <Table head={["Rank", "Creator", "Result"]}>
          {rows.map((r) => (
            <Tr key={`${r.rank}-${r.user_id}`}>
              <Td>
                <Badge tone={r.rank === 1 ? "accent" : "muted"}>#{r.rank}</Badge>
              </Td>
              <Td>{r.user_id}</Td>
              <Td>{r.result_value ?? "—"}</Td>
            </Tr>
          ))}
        </Table>
      )}
    </Page>
  );
}
