"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, type IntegrationKey, type KeyStatusResponse } from "@/lib/api";
import {
  Badge,
  Button,
  Card,
  Input,
  Notice,
  PageState,
  StatusDot,
  useToast,
} from "./ui";

const STATUS_TONE: Record<IntegrationKey["status"], "success" | "danger" | "accent" | "muted"> = {
  connected: "success",
  invalid: "danger",
  unreachable: "accent",
  untested: "muted",
};

const STATUS_LABEL: Record<IntegrationKey["status"], string> = {
  connected: "Connected",
  invalid: "Invalid",
  unreachable: "Unreachable",
  untested: "Not tested",
};

function KeyRow({ integration, onChanged }: { integration: IntegrationKey; onChanged: () => void }) {
  const toast = useToast();
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState<{ tone: "info" | "warn"; text: string } | null>(null);

  async function save() {
    if (!value.trim()) return;
    setBusy(true);
    setMessage(null);
    try {
      const res = await api.adminSaveKey(integration.name, value.trim());
      setValue("");
      setMessage({ tone: "info", text: `Saved as ${res.masked}. Run Test to confirm it works.` });
      toast(`${integration.label} saved`, "success");
      onChanged();
    } catch (e) {
      setMessage({ tone: "warn", text: e instanceof Error ? e.message : "Could not save" });
    } finally {
      setBusy(false);
    }
  }

  async function test() {
    setTesting(true);
    setMessage(null);
    try {
      const res = await api.adminTestKey(integration.name);
      setMessage({ tone: res.ok ? "info" : "warn", text: res.detail });
      onChanged();
    } catch (e) {
      setMessage({ tone: "warn", text: e instanceof Error ? e.message : "Test failed" });
    } finally {
      setTesting(false);
    }
  }

  async function remove() {
    setBusy(true);
    setMessage(null);
    try {
      await api.adminRemoveKey(integration.name);
      toast(`${integration.label} removed`, "success");
      onChanged();
    } catch (e) {
      setMessage({ tone: "warn", text: e instanceof Error ? e.message : "Could not remove" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-[calc(2rem-0.375rem)] bg-surface p-4 ring-surface">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <StatusDot tone={STATUS_TONE[integration.status]} label={STATUS_LABEL[integration.status]} />
        <span className="text-sm font-medium">{integration.label}</span>
        <Badge tone={STATUS_TONE[integration.status]}>{STATUS_LABEL[integration.status]}</Badge>
        {integration.source !== "none" && (
          <Badge tone="muted">{integration.source === "stored" ? "saved" : "from .env"}</Badge>
        )}
        <span className="ml-auto font-mono text-xs text-muted">
          {integration.masked || "no key"}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-3 text-xs text-muted">
        <a
          href={integration.docs}
          target="_blank"
          rel="noreferrer"
          className="text-accent hover:underline"
        >
          Where to get this
        </a>
        {integration.tested_at && (
          <span>Last tested {integration.tested_at.slice(0, 19).replace("T", " ")}</span>
        )}
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        <Input
          type="password"
          autoComplete="off"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={integration.configured ? "Replace the saved key" : "Paste the key"}
          aria-label={`${integration.label} value`}
        />
        <div className="flex shrink-0 flex-wrap gap-2">
          <Button size="sm" onClick={save} disabled={busy || !value.trim()}>
            Save
          </Button>
          <Button size="sm" variant="outline" onClick={test} disabled={testing || !integration.configured}>
            {testing ? "Testing…" : "Test"}
          </Button>
          {integration.source === "stored" && (
            <Button size="sm" variant="ghost" onClick={remove} disabled={busy}>
              Remove
            </Button>
          )}
        </div>
      </div>

      {message && <Notice tone={message.tone}>{message.text}</Notice>}
    </div>
  );
}

export function AdminKeys() {
  const [data, setData] = useState<KeyStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setData(await api.adminKeys());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load keys");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const groups = data
    ? [...new Set(data.integrations.map((i) => i.group))].map((group) => ({
        group,
        items: data.integrations.filter((i) => i.group === group),
      }))
    : [];

  return (
    <Card>
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-col gap-1">
            <h2 className="text-base font-semibold">Integration keys</h2>
            <p className="text-xs text-muted">
              Encrypted at rest. A saved key overrides <code>.env</code>; the key is never shown in
              full after saving.
            </p>
          </div>
          {data && !data.research_sources_configured && (
            <Badge tone="accent">sample feed</Badge>
          )}
        </div>

        {data && !data.research_sources_configured && (
          <Notice tone="warn">
            No research source is connected, so research is using the sample feed. Add a YouTube or
            Reddit key to get live trends.
          </Notice>
        )}

        <PageState loading={loading} error={error} empty={false}>
          <div className="grid gap-5">
            {groups.map(({ group, items }) => (
              <div key={group} className="flex flex-col gap-2">
                <span className="text-[10px] uppercase tracking-[0.2em] text-muted">{group}</span>
                <div className="grid gap-3">
                  {items.map((integration) => (
                    <KeyRow key={integration.name} integration={integration} onChanged={load} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </PageState>
      </div>
    </Card>
  );
}

export function ResearchSourceBanner() {
  const [configured, setConfigured] = useState(true);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    api
      .adminKeys()
      .then((d) => setConfigured(d.research_sources_configured))
      .catch(() => {})
      .finally(() => setChecked(true));
  }, []);

  if (!checked || configured) return null;
  return (
    <Notice tone="warn">
      Connect a source to get live trends. Research is using the sample feed until a YouTube or
      Reddit key is added in{" "}
      <Link href="/admin/setup" className="underline">
        Admin → Setup
      </Link>
      .
    </Notice>
  );
}
