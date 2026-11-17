import type { ReactNode } from "react";
import { AppShell, ShellHeader } from "./shell";
import { FirstVisitHint } from "./first-visit-hint";
import type { Me } from "@/lib/types";

export function AppPage({
  user,
  eyebrow,
  title,
  action,
  children,
}: {
  user: Me;
  eyebrow: string;
  title: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <AppShell user={user}>
      <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-8">
        <ShellHeader eyebrow={eyebrow} title={title} action={action} />
        <FirstVisitHint />
        {children}
      </div>
    </AppShell>
  );
}
