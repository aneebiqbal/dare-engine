"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { CalendarResponse } from "@/lib/types";
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
    try {
      await api.adminSchedule(clipId, date, platform);
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
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label="Approved clip">
              <Select value={clipId} onChange={(e) => setClipId(e.target.value)}>
                <option value="">Choose a clip</option>
                {unscheduled.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title ?? c.id}
                  </option>
                ))}
              </Select>
            </Field>
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
          <div>
            <Button onClick={schedule} disabled={!clipId || !date}>
              Add to calendar
            </Button>
          </div>
          {unscheduled.length === 0 && (
            <p className="text-xs text-muted">
              No approved clips waiting. Approve a clip from its review page first.
            </p>
          )}
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
    </div>
  );
}
