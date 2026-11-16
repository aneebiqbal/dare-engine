"use client";

import { useState } from "react";
import { api, type Clip } from "@/lib/api";
import { Badge, Button, Card, EmptyState, PageState, useToast } from "@/components/ui";

const linkClass =
  "inline-flex items-center justify-center rounded-full px-4 py-2 text-sm font-medium text-muted ring-surface transition duration-300 ease-out hover:bg-surface-2 hover:text-text active:scale-[0.98]";

export function Clips({ initial }: { initial: Clip[] }) {
  const [clips, setClips] = useState(initial);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      setClips(await api.clips());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load clips");
    } finally {
      setLoading(false);
    }
  }

  function remove(id: string) {
    setClips((prev) => prev.filter((c) => c.id !== id));
    toast("Clip discarded", "success");
  }

  return (
    <PageState loading={loading} error={error} empty={clips.length === 0}>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {clips.map((clip) => (
          <Card key={clip.id ?? clip.title}>
            <div className="flex h-full flex-col gap-3">
              <div className="flex items-center justify-between">
                <Badge tone={clip.state === "ready" ? "success" : "muted"}>{clip.state}</Badge>
                <span className="text-xs text-muted">{clip.template}</span>
              </div>
              <h3 className="text-base font-medium leading-snug">{clip.title}</h3>
              <p className="text-xs text-muted">
                {clip.duration_seconds ? `${clip.duration_seconds.toFixed(1)}s` : "—"}
              </p>
              <div className="mt-auto flex flex-wrap gap-2 pt-2">
                <a className={linkClass} href={`/clips/${clip.id ?? ""}`}>
                  Review
                </a>
                {clip.download_url && (
                  <a className={linkClass} href={clip.download_url}>
                    Download
                  </a>
                )}
                <Button size="sm" variant="danger" onClick={() => remove(clip.id ?? "")}>
                  Discard
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </PageState>
  );
}
