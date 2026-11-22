"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type ModelStatus, type ObsStatus, type SsdResponse, type WizardState } from "@/lib/api";
import { AdminModels } from "./models";
import {
  Badge,
  Button,
  Card,
  Notice,
  PageState,
  Progress,
  StatusDot,
  useToast,
} from "./ui";

export function SetupWizard() {
  const toast = useToast();
  const [state, setState] = useState<WizardState | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [ssd, setSsd] = useState<SsdResponse | null>(null);
  const [obs, setObs] = useState<ObsStatus | null>(null);
  const [models, setModels] = useState<ModelStatus | null>(null);

  const load = useCallback(async () => {
    try {
      const w = await api.wizard();
      setState(w);
      setOpen((current) => current ?? w.next ?? w.steps[0]?.id ?? null);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load the wizard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // A step is unlocked when every step before it is done.
  const unlocked = useCallback(
    (index: number) => state?.steps.slice(0, index).every((s) => s.status === "done") ?? false,
    [state],
  );

  async function save(step: string, status: string, detail?: string) {
    const next = await api.saveWizardStep(step, status, detail);
    setState(next);
    const following = next.steps.find((s) => s.status !== "done");
    if (following) setOpen(following.id);
  }

  async function verify(id: string) {
    setBusy(id);
    try {
      if (id === "ssd") {
        const res = await api.studioSsd();
        setSsd(res);
        if (!res.enabled) return void save("ssd", "failed", res.reason ?? "SSD bridge is not set");
        if (res.error) return void save("ssd", "failed", res.error);
        if (!res.drives?.length) {
          return void save("ssd", "failed", "No drive detected. Plug in the SSD and check it is mounted.");
        }
        await save("ssd", "done", `${res.drives.length} drive(s) connected`);
      } else if (id === "obs") {
        const res = await api.obsStatus();
        setObs(res);
        if (!res.enabled) return void save("obs", "failed", "OBS WebSocket is not configured");
        if (!res.connected) {
          return void save("obs", "failed", res.detail ?? res.error ?? "OBS is unreachable");
        }
        await save("obs", "done", `Connected to OBS ${res.obs_version ?? ""}`.trim());
      } else if (id === "models") {
        const res = await api.adminModels();
        setModels(res);
        if (res.bridge === "down") {
          return void save("models", "failed", res.error ?? "The local engine bridge is offline");
        }
        await save("models", "done", "Local engine is up");
      } else if (id === "cloud") {
        const [me, provider] = await Promise.all([api.me(), api.adminProvider()]);
        const who = me.user.display_name ?? me.user.email ?? me.user.id;
        const detail = provider.env.configured
          ? `Signed in as ${who} · ${provider.effective.llm_provider}`
          : `Signed in as ${who} · running on local models (no AI key configured)`;
        await save("cloud", "done", detail);
      }
    } catch (e) {
      await save(id, "failed", e instanceof Error ? e.message : "Verification failed");
    } finally {
      setBusy(null);
    }
  }

  if (loading) return <PageState loading />;
  if (error && !state) return <PageState error={error} />;

  const steps = state?.steps ?? [];
  const ready = state?.ready ?? false;

  return (
    <div className="grid gap-6" data-tour="admin-wizard">
      <Card>
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs uppercase tracking-[0.2em] text-muted">Setup</span>
              <h2 className="mt-1 text-base font-medium">
                {ready ? "You're ready." : "Four steps, each verified before the next unlocks."}
              </h2>
            </div>
            <Badge tone={ready ? "success" : "accent"}>
              {steps.filter((s) => s.status === "done").length}/{steps.length}
            </Badge>
          </div>
          <Progress
            value={steps.length ? (steps.filter((s) => s.status === "done").length / steps.length) * 100 : 0}
            label="Setup progress"
          />
          {ready && (
            <Notice tone="info">
              Everything is connected. Import a recording from the SSD or the desktop app to start
              your first project.
            </Notice>
          )}
        </div>
      </Card>

      <div className="grid gap-4">
        {steps.map((step, index) => {
          const isOpen = open === step.id;
          const canOpen = unlocked(index) || step.status === "done";
          return (
            <Card key={step.id}>
              <div className="flex flex-col gap-3">
                <button
                  type="button"
                  className="flex items-center justify-between gap-3 text-left"
                  onClick={() => canOpen && setOpen(isOpen ? null : step.id)}
                  disabled={!canOpen}
                >
                  <div className="flex items-center gap-3">
                    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-surface-2 text-xs">
                      {index + 1}
                    </span>
                    <div>
                      <h3 className="text-base font-medium">{step.title}</h3>
                      <p className="text-xs text-muted">{step.body}</p>
                    </div>
                  </div>
                  <Badge
                    tone={
                      step.status === "done"
                        ? "success"
                        : step.status === "failed"
                          ? "danger"
                          : "muted"
                    }
                  >
                    {step.status === "done"
                      ? "Done"
                      : step.status === "failed"
                        ? "Needs attention"
                        : canOpen
                          ? "Tap to open"
                          : "Locked"}
                  </Badge>
                </button>

                {isOpen && (
                  <div className="grid gap-3 border-t border-surface-2 pt-4">
                    {step.status === "failed" && step.detail && (
                      <Notice tone="warn">{step.detail}</Notice>
                    )}

                    {step.id === "ssd" && ssd && (
                      <div className="text-sm">
                        <div className="flex items-center gap-2">
                          <StatusDot
                            tone={ssd.error || !ssd.drives?.length ? "danger" : "success"}
                            label={ssd.error || !ssd.drives?.length ? "not connected" : "connected"}
                          />
                          {ssd.error || !ssd.drives?.length
                            ? "No readable drive"
                            : `${ssd.drives.length} drive(s)`}
                        </div>
                        {ssd.drives?.map((d) => (
                          <div key={d.name} className="mt-1 text-xs text-muted">
                            {d.name}
                          </div>
                        ))}
                        {ssd.how_to && <p className="mt-2 text-xs text-muted">{ssd.how_to}</p>}
                      </div>
                    )}

                    {step.id === "obs" && obs && (
                      <div className="text-sm">
                        <div className="flex items-center gap-2">
                          <StatusDot
                            tone={obs.connected ? "success" : "danger"}
                            label={obs.connected ? "connected" : "not connected"}
                          />
                          {obs.connected
                            ? `OBS ${obs.obs_version ?? ""} · scene ${obs.scene ?? "—"}`
                            : obs.detail ?? obs.error ?? "Unreachable"}
                        </div>
                        {obs.connected && (
                          <p className="mt-1 text-xs text-muted">
                            Streaming: {obs.streaming ? "yes" : "no"} · Recording:{" "}
                            {obs.recording ? "yes" : "no"} · Mic:{" "}
                            {obs.audio_inputs?.length
                              ? obs.audio_inputs.map((a) => `${a.name}${a.muted ? " (muted)" : ""}`).join(", ")
                              : "—"}
                          </p>
                        )}
                        {obs.how_to_enable && <p className="mt-2 text-xs text-muted">{obs.how_to_enable}</p>}
                      </div>
                    )}

                    {step.id === "models" && <AdminModels />}

                    {step.id === "cloud" && <CloudDetail />}

                    <div className="flex flex-wrap items-center gap-2">
                      <Button
                        size="sm"
                        onClick={() => verify(step.id)}
                        disabled={busy === step.id}
                      >
                        {busy === step.id ? "Checking…" : step.status === "done" ? "Re-verify" : "Verify"}
                      </Button>
                      {step.status !== "done" && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => save(step.id, "pending")}
                        >
                          Clear
                        </Button>
                      )}
                    </div>
                    <p className="text-xs text-muted">{step.help}</p>
                  </div>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function CloudDetail() {
  const [info, setInfo] = useState<{ who: string; provider: string; configured: boolean } | null>(null);
  useEffect(() => {
    Promise.all([api.me(), api.adminProvider()])
      .then(([me, provider]) => {
        setInfo({
          who: me.user.display_name ?? me.user.email ?? me.user.id,
          provider: provider.effective.llm_provider,
          configured: provider.env.configured,
        });
      })
      .catch(() => setInfo(null));
  }, []);
  if (!info) return <p className="text-sm text-muted">Signing in…</p>;
  return (
    <div className="text-sm">
      <div className="flex items-center gap-2">
        <StatusDot tone="success" label="signed in" />
        Signed in as {info.who}
      </div>
      <p className="mt-1 text-xs text-muted">
        AI provider: {info.provider} ·{" "}
        {info.configured ? "key configured" : "no key — running on local models"}
      </p>
    </div>
  );
}
