"use client";

import { useEffect, useState } from "react";
import { api, type Results } from "@/lib/api";
import { NextStep } from "./next-step";
import { Thumb } from "./media";
import {
  Badge,
  Button,
  Card,
  Dialog,
  Field,
  Input,
  PageState,
  Table,
  Td,
  Tr,
  useToast,
} from "@/components/ui";
import { Metric, Section, StatusBadge, WorkHeader } from "./work";

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
  const [sort, setSort] = useState<"views" | "avg">("views");
  const clips = [...(data?.clips ?? [])].sort((a, b) =>
    sort === "views"
      ? b.views - a.views
      : (b.avg_view_percentage ?? 0) - (a.avg_view_percentage ?? 0),
  );
  const best = clips[0];
  const worst = clips.length ? clips[clips.length - 1] : undefined;

  return (
    <div className="grid gap-6">
      <WorkHeader
        eyebrow="Review"
        title="Results"
        status="idle"
        actions={<Metric label="Total views" value={totalViews.toLocaleString()} />}
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <div className="flex flex-col gap-3">
            <span className="folio">
              Leading indicators
            </span>
            <div className="grid grid-cols-3 gap-3">
              <Metric
                label="Swipe-through"
                value={
                  data?.leading?.swipe_through_rate != null
                    ? `${Math.round(data.leading.swipe_through_rate * 100)}%`
                    : "—"
                }
              />
              <Metric
                label="Saves / 1k"
                value={data?.leading?.saves_per_1000 != null ? String(data.leading.saves_per_1000) : "—"}
              />
              <Metric
                label="Shares / 1k"
                value={data?.leading?.shares_per_1000 != null ? String(data.leading.shares_per_1000) : "—"}
              />
            </div>
            <p className="text-xs text-muted">
              {data?.leading?.swiped.toLocaleString() ?? 0} swiped ·{" "}
              {data?.leading?.saves.toLocaleString() ?? 0} saves ·{" "}
              {data?.leading?.shares.toLocaleString() ?? 0} shares
            </p>
          </div>
        </Card>
        <Card>
          <div className="flex flex-col gap-2">
            <span className="folio text-success">Best clip</span>
            {best ? (
              <>
                <span className="truncate text-sm font-medium">{best.title ?? best.clip_id}</span>
                <span className="font-mono text-xs text-muted">
                  {best.views.toLocaleString()} views
                  {best.avg_view_percentage != null ? ` · ${best.avg_view_percentage}% avg` : ""}
                </span>
              </>
            ) : (
              <p className="text-sm text-muted">No metrics recorded yet.</p>
            )}
          </div>
        </Card>
        <Card>
          <div className="flex flex-col gap-2">
            <span className="folio text-danger">
              Weakest retention
            </span>
            {worst && clips.length > 1 ? (
              <>
                <span className="truncate text-sm font-medium">{worst.title ?? worst.clip_id}</span>
                <span className="font-mono text-xs text-muted">
                  {worst.avg_view_percentage ?? "—"}% avg · {worst.views.toLocaleString()} views
                </span>
              </>
            ) : (
              <p className="text-sm text-muted">Not enough clips to compare yet.</p>
            )}
          </div>
        </Card>
      </div>

      {summary && (
        <Card>
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <Badge tone="muted">AI summary</Badge>
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
          <Section
            title="Clips"
            count={clips.length}
            action={
              <div className="flex gap-1 border-b border-border">
                {(["views", "avg"] as const).map((key) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setSort(key)}
                    className={`-mb-px border-b px-3 py-1.5 text-xs transition ${
                      sort === key
                        ? "border-text text-text"
                        : "border-transparent text-muted hover:text-text"
                    }`}
                  >
                    {key === "views" ? "By views" : "By retention"}
                  </button>
                ))}
              </div>
            }
          >
            <Table caption="Views and retention per clip" head={["Clip", "Views", "Avg. view %", "Record"]}>
              {clips.map((c) => (
                <Tr key={c.clip_id}>
                  <Td>
                    <div className="flex items-center gap-3">
                      <Thumb
                        src={api.thumbnailUrl(c.clip_id)}
                        alt=""
                        className="h-12 aspect-[9/16] w-auto shrink-0 rounded-sm object-contain ring-surface"
                      />
                      <span className="truncate">{c.title}</span>
                    </div>
                  </Td>
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
          </Section>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data?.by_type?.map((t) => (
              <Card key={t.mode}>
                <div className="flex items-center justify-between gap-3">
                  <span className="folio">{t.mode}</span>
                  <span className="font-mono text-xs text-muted">
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

      <NextStep
        href="/today"
        title="Back to today's ideas"
        body="Pick the next dare from what worked."
      />
    </div>
  );
}
