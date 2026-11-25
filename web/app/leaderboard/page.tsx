import { Page } from "@/components/page";
import { Badge, Card, EmptyState, Table, Td, Tr } from "@/components/ui";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function LeaderboardPage() {
  let rows: { rank: number; user_id: string; display_name: string; result_value: number | null }[] = [];
  let question: string | null = null;
  let error: string | null = null;
  try {
    const today = await api.today();
    const mission = today.daily ?? today.picks[0] ?? null;
    if (mission) {
      question = mission.question;
      rows = (await api.leaderboard(mission.id)).items;
    }
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load";
  }

  return (
    <Page eyebrow="Leaderboard" title="Daily Mission board">
      {question && (
        <Card>
          <div className="flex flex-col gap-2">
            <Badge tone="accent">Daily Mission</Badge>
            <h2 className="text-lg font-medium leading-snug">{question}</h2>
          </div>
        </Card>
      )}
      {error ? (
        <Card>
          <p className="text-sm text-danger" role="alert">{error}</p>
        </Card>
      ) : rows.length === 0 ? (
        <EmptyState
          title="No attempts yet"
          body="Be the first to complete the Daily Mission."
        />
      ) : (
        <Table caption="Ranked attempts" head={["Rank", "Creator", "Result"]}>
          {rows.map((r) => (
            <Tr key={`${r.rank}-${r.user_id}`}>
              <Td>
                <span
                  className={
                    r.rank <= 3
                      ? "text-2xl font-semibold tracking-tight text-accent"
                      : "text-2xl font-semibold tracking-tight text-muted"
                  }
                >
                  {r.rank}
                </span>
              </Td>
              <Td className="font-medium">{r.display_name}</Td>
              <Td>{r.result_value ?? "—"}</Td>
            </Tr>
          ))}
        </Table>
      )}
    </Page>
  );
}
