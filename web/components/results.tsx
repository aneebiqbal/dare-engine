"use client";

import { useEffect, useState } from "react";
import { api, type Results } from "@/lib/api";
import { Badge, Card, PageState, Stat, Table, Td, Tr } from "@/components/ui";

export function Results({ initial }: { initial: Results | null }) {
  const [data, setData] = useState<Results | null>(initial);
  const [summary, setSummary] = useState<string | null>(null);
  const [fallback, setFallback] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.results(), api.resultsSummary()])
      .then(([r, s]) => {
        setData(r);
        setSummary(s.summary);
        setFallback(s.fallback);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load results"))
      .finally(() => setLoading(false));
  }, []);

  const totalViews = data?.clips.reduce((n, c) => n + c.views, 0) ?? 0;

  return (
    <div className="grid gap-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <Stat label="Total views" value={totalViews.toLocaleString()} />
        </Card>
        <Card>
          <Stat label="Clips" value={data?.clips.length ?? 0} />
        </Card>
        <Card>
          <Stat label="Mission types" value={data?.by_type.length ?? 0} />
        </Card>
      </div>

      {summary && (
        <Card>
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <Badge tone="accent">AI summary</Badge>
              {fallback && <Badge tone="muted">fallback</Badge>}
            </div>
            <p className="text-sm leading-relaxed">{summary}</p>
          </div>
        </Card>
      )}

      <PageState loading={loading} error={error} empty={!data || data.clips.length === 0}>
        <div className="grid gap-6">
          <Table head={["Clip", "Views", "Avg. view %"]}>
            {data?.clips?.map((c) => (
              <Tr key={c.clip_id}>
                <Td>{c.title}</Td>
                <Td>{c.views?.toLocaleString() ?? "—"}</Td>
                <Td>{c.avg_view_percentage ?? "—"}</Td>
              </Tr>
            ))}
          </Table>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data?.by_type?.map((t) => (
              <Card key={t.mode}>
                <div className="flex items-center justify-between">
                  <Badge tone="accent">{t.mode}</Badge>
                  <span className="text-sm text-muted">
                    {t.clips} clips · {t.views?.toLocaleString() ?? "—"} views
                  </span>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </PageState>
    </div>
  );
}
