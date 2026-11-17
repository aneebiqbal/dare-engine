"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button, Card, Eyebrow, Field, Input, PageState, useToast } from "@/components/ui";

const DEV = process.env.NEXT_PUBLIC_DEV_AUTH === "1";
const DEV_USERS = ["Alice", "Bob", "Admin"];

export function SignIn() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  useEffect(() => {
    // Establish the CSRF cookie before any state-changing request.
    api.csrf().catch(() => {});
  }, []);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await api.signIn(email, password);
      router.push("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  async function devSignIn(name: string) {
    setBusy(true);
    setError(null);
    try {
      await api.devSignIn(name);
      router.push("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageState loading={false} error={error} empty={false}>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <div className="flex flex-col gap-4">
            <Eyebrow>Email and password</Eyebrow>
            <Field label="Email">
              <Input
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                data-testid="email"
              />
            </Field>
            <Field label="Password">
              <Input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                data-testid="password"
                onKeyDown={(e) => e.key === "Enter" && void submit()}
              />
            </Field>
            <Button onClick={submit} disabled={busy || !email || !password} data-testid="signin-submit">
              {busy ? "Signing in…" : "Sign in"}
            </Button>
            <p className="text-xs text-muted">
              New here?{" "}
              <Link href="/signup" className="text-accent hover:underline">
                Sign up with an invite code
              </Link>
            </p>
          </div>
        </Card>

        <Card>
          <div className="flex flex-col gap-4">
            <Eyebrow>Development sign-in</Eyebrow>
            <p className="text-sm leading-relaxed text-muted">
              Creates a real user and a real session in the database. Enabled only in
              tests, and the API refuses to start with it in production.
            </p>
            {DEV ? (
              <div className="flex flex-wrap gap-3">
                {DEV_USERS.map((name) => (
                  <Button
                    key={name}
                    data-testid={`signin-${name.toLowerCase()}`}
                    disabled={busy}
                    onClick={() => devSignIn(name)}
                  >
                    Continue as {name}
                  </Button>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted">Development sign-in is disabled.</p>
            )}
          </div>
        </Card>
      </div>
    </PageState>
  );
}
