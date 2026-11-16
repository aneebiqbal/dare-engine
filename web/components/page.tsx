import type { ReactNode } from "react";
import { Nav } from "./nav";
import { Eyebrow } from "./ui";

export function Page({
  eyebrow,
  title,
  children,
  action,
}: {
  eyebrow: string;
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <main className="mx-auto flex min-h-[100dvh] w-full max-w-5xl flex-col gap-8 px-5 pb-24 pt-6 sm:px-8">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <Eyebrow>{eyebrow}</Eyebrow>
        <Nav />
      </header>
      <section className="flex flex-col gap-4">
        <h1 className="text-balance text-4xl font-semibold leading-[1.05] tracking-tight sm:text-5xl">
          {title}
        </h1>
        {action}
      </section>
      {children}
    </main>
  );
}
