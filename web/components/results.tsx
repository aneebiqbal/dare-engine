"use client";

import { useEffect, useState } from "react";
import { api, type Results } from "@/lib/api";
import {
  Badge,
  Button,
  Card,
  Dialog,
  Field,
  Input,
  PageState,
  Stat,
  Table,
  Td,
  Tr,
  useToast,
} from "@/components/ui";

export function Results({ initial }: { initial: Results | null }) {
  const [data, setData] = useState<Results | null>(initial);
  const [summary, setSummary] = useState<string | null>(null);
  const [fallback, setFallback] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [metricFor, setMetricFor] = useState<{ clip_id: string; title: string | null } | null>(null);
  const [views, setViews] = useState("");
  const [avg, setAvg] = useState("");
  const [swiped, setSwiped] = useState("");
  const [saves, setSaves] = useState("");
  const [shares, setShares] = useState("");
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  async function load() {
    try {
      const [r, s] = await Promise.all([api.results(), api.resultsSummary()]);
      setData(r);
      setSummary(s.summary);
      setFallback(s.fallback);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load results");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function saveMetric() {
    if (!metricFor) return;
    setBusy(true);
    try {
      await api.recordMetric(metricFor.clip_id, Number(views), Number(avg), {
        swiped: Number(swiped || 0),
        saves: Number(saves || 0),
        shares: Number(shares || 0),
      });
      setMetricFor(null);
      setViews("");
      setAvg("");
      setSwiped("");
      setSaves("");
      setShares("");
      await load();
      toast("Metrics saved", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not save metrics", "danger");
    } finally {
      setBusy(false);
    }
  }

  const totalViews = data?.clips.reduce((n, c) => n + c.views, 0) ?? 0;

  return (
    <div className="grid gap-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <Stat label="Total views" value={totalViews.toLocaleString()} />
        </Card>
        <Card>
          <Stat
            label="Swipe-through"
            value={
              data?.leading?.swipe_through_rate != null
                ? `${Math.round(data.leading.swipe_through_rate * 100)}%`
                : "—"
            }
            hint={data?.leading ? `${data.leading.swiped.toLocaleString()} swiped` : undefined}
          />
        </Card>
        <Card>
          <Stat
            label="Saves / shares"
            value={`${data?.leading?.saves?.toLocaleString() ?? 0} / ${data?.leading?.shares?.toLocaleString() ?? 0}`}
            hint={
              data?.leading?.saves_per_1000 != null
                ? `${data.leading.saves_per_1000} saves per 1k views`
                : undefined
            }
          />
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

      <PageState
        loading={loading}
        error={error}
        empty={!data || data.clips.length === 0}
        emptyTitle="No results yet"
        emptyBody="Record views for a clip and the numbers show up here."
      >
        <div className="grid gap-6">
          <Table
            caption="Views and retention per clip"
            head={["Clip", "Views", "Avg. view %", "Record"]}
          >
            {data?.clips?.map((c) => (
              <Tr key={c.clip_id}>
                <Td>{c.title}</Td>
                <Td>{c.views?.toLocaleString() ?? "—"}</Td>
                <Td>{c.avg_view_percentage != null ? `${c.avg_view_percentage}%` : "—"}</Td>
                <Td>
                  <Button size="sm" variant="outline" onClick={() => setMetricFor({ clip_id: c.clip_id, title: c.title })}>
                    Add metrics
                  </Button>
                </Td>
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
                    {t.avg_view_percentage != null ? ` · ${t.avg_view_percentage}%` : ""}
                  </span>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </PageState>

      <Dialog
        open={Boolean(metricFor)}
        onClose={() => setMetricFor(null)}
        title={`Record metrics${metricFor?.title ? ` — ${metricFor.title}` : ""}`}
      >
        <div className="flex flex-col gap-4">
          <Field label="Views" hint="From your channel analytics.">
            <Input
              type="number"
              min={0}
              value={views}
              onChange={(e) => setViews(e.target.value)}
              placeholder="1204"
            />
          </Field>
          <Field label="Average view %" hint="0 to 100.">
            <Input
              type="number"
              min={0}
              max={100}
              value={avg}
              onChange={(e) => setAvg(e.target.value)}
              placeholder="42"
            />
          </Field>
          <Field label="Swiped past" hint="Views that did not hold.">
            <Input
              type="number"
              min={0}
              value={swiped}
              onChange={(e) => setSwiped(e.target.value)}
              placeholder="300"
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Saves">
              <Input
                type="number"
                min={0}
                value={saves}
                onChange={(e) => setSaves(e.target.value)}
                placeholder="12"
              />
            </Field>
            <Field label="Shares">
              <Input
                type="number"
                min={0}
                value={shares}
                onChange={(e) => setShares(e.target.value)}
                placeholder="8"
              />
            </Field>
          </div>
          <div className="flex justify-end gap-3">
            <Button variant="ghost" onClick={() => setMetricFor(null)}>
              Cancel
            </Button>
            <Button onClick={saveMetric} disabled={busy || !views}>
              Save metrics
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
