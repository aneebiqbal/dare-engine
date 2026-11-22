import type { ReactNode } from "react";
import { AppShell, ShellHeader } from "./shell";
import { FirstVisitHint } from "./first-visit-hint";
import type { Me } from "@/lib/types";

export function AppPage({
  user,
  eyebrow,
  title,
  action,
  header = true,
  children,
}: {
  user: Me;
  eyebrow: string;
  title: string;
  action?: ReactNode;
  /** Rebuilt pages render their own `WorkHeader` (with live status) instead. */
  header?: boolean;
  children: ReactNode;
}) {
  return (
    <AppShell user={user}>
      <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-8">
        {header ? <ShellHeader eyebrow={eyebrow} title={title} action={action} /> : null}
        <FirstVisitHint />
        {children}
      </div>
    </AppShell>
  );
}
