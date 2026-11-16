"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, Card, Eyebrow, PageState } from "@/components/ui";

const DEV = process.env.NEXT_PUBLIC_DEV_AUTH === "1";
const DEV_USERS = ["Alice", "Bob"];

export function SignIn() {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function signIn(name: string) {
    setBusy(name);
    setError(null);
    try {
      const res = await fetch("/api/auth/dev/sign-in", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ display_name: name }),
      });
      if (!res.ok) throw new Error(await res.text());
      router.push("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sign-in failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <PageState loading={false} error={error} empty={false}>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <div className="flex flex-col gap-4">
            <Eyebrow>Development sign-in</Eyebrow>
            <p className="text-sm leading-relaxed text-muted">
              Creates a real user and a real session in the database. Enabled only
              by an environment flag; the API refuses to start with it in
              production. Google sign-in replaces only the identity provider.
            </p>
            {DEV ? (
              <div className="flex flex-wrap gap-3">
                {DEV_USERS.map((name) => (
                  <Button
                    key={name}
                    data-testid={`signin-${name.toLowerCase()}`}
                    disabled={busy === name}
                    onClick={() => signIn(name)}
                  >
                    {busy === name ? "Signing in" : `Continue as ${name}`}
                  </Button>
                ))}
              </div>
            ) : (
              <p className="text-xs text-danger">Development sign-in is disabled.</p>
            )}
          </div>
        </Card>
        <Card>
          <div className="flex flex-col gap-4">
            <Eyebrow>Google sign-in</Eyebrow>
            <p className="text-sm leading-relaxed text-muted">
              The production path. Blocked by Gate 0: no OAuth client yet.
            </p>
            <Button data-testid="google-signin" disabled>
              Continue with Google
            </Button>
          </div>
        </Card>
      </div>
    </PageState>
  );
}
