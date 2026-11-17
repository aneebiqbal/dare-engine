"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button, Card, Field, Input, PageState } from "@/components/ui";

function SignUpForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState(params.get("code") ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.csrf().catch(() => {});
  }, []);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await api.signUp(email, password, name, code || undefined);
      router.push("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sign-up failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageState loading={false} error={error} empty={false}>
      <Card>
        <div className="flex flex-col gap-4">
          <Field label="Invite code">
            <Input value={code} onChange={(e) => setCode(e.target.value)} data-testid="invite-code" />
          </Field>
          <Field label="Email">
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} data-testid="email" />
          </Field>
          <Field label="Display name">
            <Input value={name} onChange={(e) => setName(e.target.value)} data-testid="display-name" />
          </Field>
          <Field label="Password" hint="At least 10 characters.">
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              data-testid="password"
              onKeyDown={(e) => e.key === "Enter" && void submit()}
            />
          </Field>
          <Button onClick={submit} disabled={busy || !email || !password || !name} data-testid="signup-submit">
            {busy ? "Creating account…" : "Create account"}
          </Button>
          <p className="text-xs text-muted">
            Already have an account?{" "}
            <Link href="/signin" className="text-accent hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </Card>
    </PageState>
  );
}

export function SignUp() {
  return (
    <Suspense>
      <SignUpForm />
    </Suspense>
  );
}
