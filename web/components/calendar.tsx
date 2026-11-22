"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { CalendarResponse } from "@/lib/types";
import { NextStep } from "./next-step";
import {
  Badge,
  Button,
  Card,
  Field,
  Input,
  Notice,
  PageState,
  Select,
  Table,
  Td,
  Tr,
  useToast,
} from "./ui";
import { Metric, Section, StatusBadge, WorkHeader } from "./work";

export function AdminCalendar() {
  const toast = useToast();
  const [data, setData] = useState<CalendarResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [date, setDate] = useState("");
  const [platform, setPlatform] = useState("youtube");

  const load = useCallback(async () => {
    try {
      setData(await api.adminCalendar());
      setError(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Could not load the calendar.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function scheduleClip(id: string, day: string) {
    if (!day) return;
    try {
      await api.adminSchedule(id, day, platform);
      toast("Scheduled", "success");
      load();
    } catch (exc) {
      toast(exc instanceof Error ? exc.message : "Could not schedule", "danger");
    }
  }

  async function publish(id: string) {
    try {
      await api.adminPublish(id);
      toast("Marked published (manual).", "success");
      load();
    } catch (exc) {
      toast(exc instanceof Error ? exc.message : "Could not publish", "danger");
    }
  }

  async function remove(id: string) {
    try {
      await api.adminUnschedule(id);
      toast("Removed from the queue", "success");
      load();
    } catch (exc) {
      toast(exc instanceof Error ? exc.message : "Could not remove", "danger");
    }
  }

  if (loading) return <PageState loading />;
  if (error && !data) return <PageState error={error} />;

  const entries = data?.entries ?? [];
  const unscheduled = data?.unscheduled ?? [];
  const limit = data?.daily_limit ?? 2;
  const byDay: Record<string, number> = {};
  for (const e of entries) byDay[e.date] = (byDay[e.date] ?? 0) + 1;
  const week = (() => {
    const today = new Date();
    const start = new Date(today);
    start.setDate(today.getDate() - ((today.getDay() + 6) % 7));
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      return d;
    });
  })();
  const dayKey = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const todayKey = dayKey(new Date());

  return (
    <div className="grid gap-6">
      <WorkHeader
        eyebrow="Create"
        title="Calendar"
        status={unscheduled.length ? "needs" : entries.length ? "idle" : "idle"}
        actions={
          <div className="flex items-center gap-4">
            <Metric label="Scheduled" value={entries.length} />
            <Metric label="Waiting" value={unscheduled.length} />
            <Metric label="Cadence" value={`${limit}/day`} />
          </div>
        }
      />

      {data && data.warnings.length > 0 && (
        <Notice tone="warn">
          <ul className="list-disc pl-4">
            {data.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </Notice>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <Card>
          <Section
            title="This week"
            count={entries.length}
            action={<span className="font-mono text-xs text-muted">{limit} Shorts/day</span>}
          >
            <div className="mt-1 grid grid-cols-7 gap-2">
              {week.map((d) => {
                const key = dayKey(d);
                const count = byDay[key] ?? 0;
                const over = count > limit;
                const isToday = key === todayKey;
                return (
                  <div
                    key={key}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => {
                      e.preventDefault();
                      const id = e.dataTransfer.getData("text/clip-id");
                      if (id) void scheduleClip(id, key);
                    }}
                    className={`flex min-h-[6rem] flex-col items-center gap-1 rounded-xl px-2 py-3 ring-surface transition ${
                      over ? "bg-danger-soft ring-danger/40" : isToday ? "bg-accent-soft" : "bg-surface-2"
                    }`}
                  >
                    <span className="text-[10px] uppercase tracking-[0.18em] text-muted">
                      {d.toLocaleDateString(undefined, { weekday: "short" })}
                    </span>
                    <span className="text-base font-semibold">{d.getDate()}</span>
                    <span className="font-mono text-xs text-muted">
                      {count}/{limit}
                    </span>
                    {over && <Badge tone="danger">over</Badge>}
                    {isToday && <span className="text-[10px] uppercase tracking-[0.14em] text-accent">today</span>}
                  </div>
                );
              })}
            </div>
            <p className="mt-3 text-xs text-muted">
              Drag an approved Short onto a day. The guardrail lights up when a day is over the
              cadence.
            </p>
          </Section>
        </Card>

        <Card>
          <Section title="Schedule a Short" count={unscheduled.length}>
            <div className="mt-1 flex flex-col gap-3">
              <Field label="Date">
                <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
              </Field>
              <Field label="Platform">
                <Select value={platform} onChange={(e) => setPlatform(e.target.value)}>
                  <option value="youtube">YouTube</option>
                  <option value="tiktok" disabled>
                    TikTok (approval required)
                  </option>
                  <option value="instagram" disabled>
                    Instagram (approval required)
                  </option>
                </Select>
              </Field>
              <div className="flex flex-col gap-2">
                {unscheduled.length === 0 && (
                  <p className="text-xs text-muted">
                    No approved clips waiting. Approve a clip from its review page first.
                  </p>
                )}
                {unscheduled.map((c) => (
                  <div
                    key={c.id}
                    draggable
                    onDragStart={(e) => e.dataTransfer.setData("text/clip-id", c.id)}
                    className="flex cursor-grab items-center justify-between gap-3 rounded-xl bg-surface px-4 py-3 ring-surface transition hover:bg-surface-2"
                  >
                    <span className="truncate text-sm">{c.title ?? c.id}</span>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={!date}
                      onClick={() => scheduleClip(c.id, date)}
                    >
                      Add
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          </Section>
        </Card>
      </div>

      <Section title="Queue" count={entries.length}>
        <Card>
          <div className="mt-1">
            <Table head={["Date", "Clip", "Platform", "State", "Actions"]} caption="Scheduled posts">
              {entries.length === 0 && (
                <Tr>
                  <Td colSpan={5}>Nothing scheduled yet.</Td>
                </Tr>
              )}
              {entries.map((e) => (
                <Tr key={e.id}>
                  <Td>{e.date}</Td>
                  <Td>{e.title ?? e.clip_id}</Td>
                  <Td>{data?.platforms?.[e.platform] ?? e.platform}</Td>
                  <Td>
                    <StatusBadge
                      status={e.state === "published" ? "done" : e.state === "failed" ? "failed" : "idle"}
                      label={e.state}
                    />
                  </Td>
                  <Td>
                    <div className="flex gap-2">
                      {e.state !== "published" && (
                        <Button size="sm" variant="outline" onClick={() => publish(e.id)}>
                          Mark published
                        </Button>
                      )}
                      <Button size="sm" variant="ghost" onClick={() => remove(e.id)}>
                        Remove
                      </Button>
                    </div>
                  </Td>
                </Tr>
              ))}
            </Table>
          </div>
          <p className="mt-3 text-xs text-muted">
            Publishing is manual or YouTube-API only. TikTok and Instagram need platform approval
            and are disabled. The YouTube API is not connected, so “Mark published” records your
            own upload — it is not an API post.
          </p>
        </Card>
      </Section>

      {entries.length > 0 ? (
        <NextStep
          href="/admin/long-form"
          title="Build a long-form video"
          body="Assemble the scheduled Shorts into one video."
        />
      ) : (
        <NextStep
          href="/clips"
          title="Approve a clip"
          body="Approved clips appear here ready to schedule."
        />
      )}
    </div>
  );
}
