"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button, Card, Field, Input, PageState } from "@/components/ui";

function ResetForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [token, setToken] = useState(params.get("token") ?? "");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.csrf().catch(() => {});
  }, []);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await api.resetPassword(token, password);
      router.push("/signin");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reset failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageState loading={false} error={error} empty={false}>
      <Card>
        <div className="flex flex-col gap-4">
          <Field label="One-time reset token">
            <Input value={token} onChange={(e) => setToken(e.target.value)} />
          </Field>
          <Field label="New password" hint="At least 10 characters.">
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
          <Button onClick={submit} disabled={busy || !token || !password}>
            {busy ? "Resetting…" : "Reset password"}
          </Button>
          <p className="text-xs text-muted">
            <Link href="/signin" className="text-text underline decoration-border underline-offset-4 hover:text-accent">
              Back to sign in
            </Link>
          </p>
        </div>
      </Card>
    </PageState>
  );
}

export function Reset() {
  return (
    <Suspense>
      <ResetForm />
    </Suspense>
  );
}
