"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
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

export function AdminCalendar() {
  const toast = useToast();
  const [data, setData] = useState<CalendarResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [clipId, setClipId] = useState("");
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

  async function schedule() {
    if (!clipId || !date) return;
    await scheduleClip(clipId, date);
  }

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
  const byDay: Record<string, number> = {};
  for (const e of entries) byDay[e.date] = (byDay[e.date] ?? 0) + 1;
  const week = useMemo(() => {
    const today = new Date();
    const start = new Date(today);
    start.setDate(today.getDate() - ((today.getDay() + 6) % 7));
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      return d;
    });
  }, []);
  const dayKey = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

  return (
    <div className="grid gap-6">
      {data && data.warnings.length > 0 && (
        <Notice tone="warn">
          <ul className="list-disc pl-4">
            {data.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </Notice>
      )}

      <Card>
        <div className="flex flex-col gap-4">
          <div>
            <span className="text-xs uppercase tracking-[0.2em] text-muted">Schedule a Short</span>
            <p className="mt-1 text-sm text-muted">
              Review the export, pick a day, and publish manually. The default cadence is{" "}
              {data?.daily_limit ?? 2} Shorts a day.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
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
          </div>

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

          <div className="grid grid-cols-7 gap-2">
            {week.map((d) => {
              const key = dayKey(d);
              const count = byDay[key] ?? 0;
              const over = count > (data?.daily_limit ?? 2);
              return (
                <div
                  key={key}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    const id = e.dataTransfer.getData("text/clip-id");
                    if (id) void scheduleClip(id, key);
                  }}
                  className={`flex flex-col items-center gap-1 rounded-xl px-2 py-3 ring-surface transition ${
                    over ? "bg-danger/10 ring-danger/30" : "bg-surface-2"
                  }`}
                >
                  <span className="text-[10px] uppercase tracking-[0.2em] text-muted">
                    {d.toLocaleDateString(undefined, { weekday: "short" })}
                  </span>
                  <span className="text-base font-semibold">{d.getDate()}</span>
                  <span className="text-xs text-muted">
                    {count} {count === 1 ? "Short" : "Shorts"}
                  </span>
                  {over && <Badge tone="danger">over</Badge>}
                </div>
              );
            })}
          </div>
        </div>
      </Card>

      <Card>
        <span className="text-xs uppercase tracking-[0.2em] text-muted">Queue</span>
        <div className="mt-4">
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
                  <Badge tone={e.state === "published" ? "success" : "muted"}>{e.state}</Badge>
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
          Publishing is manual or YouTube-API only. TikTok and Instagram need platform
          approval and are disabled. The YouTube API is not connected, so “Mark published”
          records your own upload — it is not an API post.
        </p>
      </Card>

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
