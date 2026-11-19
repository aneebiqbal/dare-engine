"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { api, type Me } from "@/lib/api";
import { Tour } from "./tour";
import { ThemeToggle } from "./theme";
import { Icon } from "./icons";
import { Badge, Button } from "./ui";

const CREATOR: [string, string, string][] = [
  ["/", "Dashboard", "grid"],
  ["/today", "Today", "target"],
  ["/live", "Go Live", "radio"],
  ["/clips", "Clips", "film"],
  ["/results", "Results", "chart"],
  ["/history", "History", "clock"],
  ["/help", "Help", "help"],
  ["/settings", "Settings", "gear"],
];

const ADMIN: [string, string, string][] = [
  ["/admin", "Overview", "grid"],
  ["/admin/games", "Games", "gamepad"],
  ["/admin/users", "Users", "users"],
  ["/admin/invites", "Invites", "mail"],
  ["/admin/pool", "Pool", "layers"],
  ["/admin/studio", "Studio", "film"],
  ["/admin/templates", "Templates", "layout"],
  ["/admin/jobs", "Jobs", "queue"],
  ["/admin/ai", "AI usage", "spark"],
  ["/admin/audit", "Audit log", "scroll"],
  ["/admin/setup", "Setup status", "check"],
];

export function AppShell({ user, children }: { user: Me; children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [accountOpen, setAccountOpen] = useState(false);
  const [tourOpen, setTourOpen] = useState(false);

  useEffect(() => {
    const open = (e: Event) => setTourOpen(true);
    window.addEventListener("clipdesk:tour", open);
    return () => window.removeEventListener("clipdesk:tour", open);
  }, []);

  // First sign-in: open the tour on the dashboard unless it was finished or
  // skipped. It does not follow the user to every page.
  useEffect(() => {
    if (pathname !== "/") return;
    const tourId = user.role === "admin" ? "admin" : "creator";
    api
      .tours()
      .then((list) => {
        const progress = list.find((t) => t.tour_id === tourId);
        if (!progress || (!progress.completed && !progress.skipped)) setTourOpen(true);
      })
      .catch(() => {});
  }, [user.role, pathname]);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!mobileOpen && !accountOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setMobileOpen(false);
        setAccountOpen(false);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [mobileOpen, accountOpen]);

  useEffect(() => {
    if (!accountOpen) return;
    const onDown = (e: MouseEvent) => {
      const target = e.target;
      if (!(target instanceof HTMLElement && target.closest("[data-account-menu]"))) {
        setAccountOpen(false);
      }
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [accountOpen]);

  const links = useMemo(() => {
    const all = user.role === "admin" ? [...CREATOR, ...ADMIN] : CREATOR;
    const q = query.trim().toLowerCase();
    return q ? all.filter(([, label]) => label.toLowerCase().includes(q)) : all;
  }, [query, user.role]);

  const signOut = async () => {
    try {
      await api.signOut();
    } finally {
      router.push("/signin");
    }
  };

  const sidebar = (
    <div className="flex h-full flex-col gap-6 p-4">
      <div className="flex items-center justify-between gap-3 px-2">
        <Link href="/" className="text-sm font-semibold tracking-tight">
          clipdesk
        </Link>
        <button
          type="button"
          onClick={() => setCollapsed((v) => !v)}
          aria-label={collapsed ? "» Expand sidebar" : "« Collapse sidebar"}
          className="hidden rounded-full p-2 text-muted ring-surface transition hover:text-text md:block"
        >
          {collapsed ? "»" : "«"}
        </button>
      </div>

      <nav className="flex flex-col gap-1" aria-label="Primary">
        {links.map(([href, label, icon]) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              data-tour={`nav-${label.toLowerCase().replace(/\s+/g, "-")}`}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-3 rounded-full px-3 py-2.5 text-sm transition duration-300 ease-out ${
                active
                  ? "bg-accent-soft text-accent"
                  : "text-muted hover:bg-surface-2 hover:text-text"
              } ${collapsed ? "justify-center" : ""}`}
            >
              <span className="w-5 text-center text-muted">
                <Icon name={icon} size={15} />
              </span>
              {!collapsed && <span>{label}</span>}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto flex flex-col gap-2">
        <Button
          variant="outline"
          size="sm"
          data-tour="help-button"
          onClick={() => setTourOpen(true)}
          className={collapsed ? "justify-center" : ""}
        >
          {collapsed ? "?" : "Replay tour"}
        </Button>
        <div className="flex items-center justify-between px-2">
          <ThemeToggle />
          <span className="text-[10px] uppercase tracking-[0.2em] text-muted">
            {collapsed ? "" : user.role}
          </span>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-[100dvh]">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-accent focus:px-4 focus:py-2 focus:text-sm focus:text-accent-contrast"
      >
        Skip to content
      </a>
      {/* Desktop sidebar */}
      <aside
        className={`hidden shrink-0 border-r border-border bg-surface transition-[width] duration-300 ease-out md:block ${
          collapsed ? "w-16" : "w-64"
        }`}
      >
        {sidebar}
      </aside>

      {/* Mobile sidebar */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 md:hidden"
          role="dialog"
          aria-modal="true"
          aria-label="Menu"
        >
          <div className="absolute inset-0 bg-black/50" onClick={() => setMobileOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-64 border-r border-border bg-surface">
            {sidebar}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-border bg-bg/80 px-4 py-3 backdrop-blur">
          <button
            type="button"
            className="rounded-full p-2 text-muted ring-surface md:hidden"
            aria-label="Open menu"
            onClick={() => setMobileOpen(true)}
          >
            <Icon name="menu" size={18} />
          </button>
          <label className="relative min-w-0 flex-1 sm:max-w-md">
            <span className="sr-only">Search pages</span>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search pages"
              className="w-full rounded-full bg-surface px-4 py-2 text-sm text-text ring-surface outline-none transition placeholder:text-muted focus:bg-surface-2"
            />
          </label>
          <div className="relative ml-auto" data-account-menu>
            <button
              type="button"
              data-tour="account-menu"
              onClick={() => setAccountOpen((v) => !v)}
              aria-haspopup="menu"
              aria-expanded={accountOpen}
              className="flex items-center gap-2 rounded-full bg-surface px-3 py-1.5 text-sm ring-surface transition hover:bg-surface-2"
            >
              <span
                aria-hidden="true"
                className="flex h-6 w-6 items-center justify-center rounded-full bg-accent-soft text-[10px] font-semibold text-accent"
              >
                {(user.display_name || user.email || "?").slice(0, 1).toUpperCase()}
              </span>
              <span className="truncate">{user.display_name || user.email}</span>
            </button>
            {accountOpen && (
              <div
                role="menu"
                className="absolute right-0 top-full mt-2 w-56 rounded-lg bg-surface p-1.5 ring-surface"
              >
                <Link
                  href="/settings"
                  role="menuitem"
                  className="block rounded-[calc(2rem-0.375rem)] px-4 py-2.5 text-sm text-muted hover:bg-surface-2 hover:text-text"
                >
                  Account settings
                </Link>
                <Link
                  href="/help"
                  role="menuitem"
                  className="block rounded-[calc(2rem-0.375rem)] px-4 py-2.5 text-sm text-muted hover:bg-surface-2 hover:text-text"
                >
                  Help and tours
                </Link>
                <button
                  role="menuitem"
                  onClick={() => void api.signOutAll().then(() => router.push("/signin"))}
                  className="block w-full rounded-[calc(2rem-0.375rem)] px-4 py-2.5 text-left text-sm text-muted hover:bg-surface-2 hover:text-text"
                >
                  Sign out everywhere
                </button>
                <button
                  role="menuitem"
                  onClick={signOut}
                  className="block w-full rounded-[calc(2rem-0.375rem)] px-4 py-2.5 text-left text-sm text-danger hover:bg-surface-2"
                >
                  Sign out
                </button>
              </div>
            )}
          </div>
        </header>

        <main
          id="main-content"
          className="min-w-0 flex-1 animate-entry px-4 py-6 sm:px-8 sm:py-8"
        >
          {children}
        </main>
      </div>

      {tourOpen && <Tour tourId={user.role === "admin" ? "admin" : "creator"} onClose={() => setTourOpen(false)} />}
    </div>
  );
}

export function ShellHeader({
  eyebrow,
  title,
  action,
}: {
  eyebrow: string;
  title: string;
  action?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div className="flex flex-col gap-3">
        <span className="w-fit rounded-full bg-surface-2 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-muted ring-surface">
          {eyebrow}
        </span>
        <h1 className="text-balance text-4xl font-semibold leading-[1.05] tracking-tight sm:text-5xl">
          {title}
        </h1>
      </div>
      {action}
    </header>
  );
}

export function RoleBadge({ role }: { role: string }) {
  return <Badge tone={role === "admin" ? "accent" : "muted"}>{role}</Badge>;
}
