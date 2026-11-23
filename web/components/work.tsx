"use client";

import Link from "next/link";
import { Fragment, type ReactNode } from "react";
import type { AdminOverview } from "@/lib/api";
import { Badge, Progress, StatusDot } from "./ui";

/** The closed status vocabulary. Colour always means one of these. */
export type WorkStatus = "running" | "needs" | "done" | "failed" | "idle";

export const STATUS_META: Record<
  WorkStatus,
  { label: string; tone: "accent" | "needs" | "success" | "danger" | "muted"; dot: "accent" | "success" | "danger" | "muted" }
> = {
  running: { label: "Running", tone: "accent", dot: "accent" },
  needs: { label: "Needs you", tone: "needs", dot: "accent" },
  done: { label: "Done", tone: "success", dot: "success" },
  failed: { label: "Failed", tone: "danger", dot: "danger" },
  idle: { label: "Idle", tone: "muted", dot: "muted" },
};

export function LiveDot({ tone = "accent", label }: { tone?: "accent" | "success" | "danger" | "muted"; label?: string }) {
  const tones = {
    accent: "bg-accent",
    success: "bg-success",
    danger: "bg-danger",
    muted: "bg-surface-3",
  }[tone];
  return (
    <span
      className={`inline-block h-1.5 w-1.5 rounded-full ${tones} ${tone === "accent" ? "animate-live" : ""}`}
      role="status"
      aria-label={label ?? tone}
      title={label}
    />
  );
}

export function StatusBadge({ status, label }: { status: WorkStatus; label?: string }) {
  const meta = STATUS_META[status];
  return (
    <Badge tone={meta.tone}>
      <span className={`h-1.5 w-1.5 rounded-full bg-current ${status === "running" ? "animate-live" : ""}`} />
      {label ?? meta.label}
    </Badge>
  );
}

/* ------------------------------------------------------------------ header */

export function WorkHeader({
  eyebrow,
  title,
  status,
  actions,
}: {
  eyebrow: string;
  title: string;
  status?: WorkStatus;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div className="flex flex-col gap-3">
        <span className="w-fit rounded-full bg-surface-2 px-3 py-1 text-[10px] uppercase tracking-[0.18em] text-muted ring-surface">
          {eyebrow}
        </span>
        <h1 className="text-balance text-3xl font-semibold leading-[1.1] tracking-tight sm:text-4xl">
          {title}
        </h1>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        {status && <StatusBadge status={status} />}
        {actions}
      </div>
    </header>
  );
}

/* ----------------------------------------------------------------- section */

export function Section({
  title,
  count,
  action,
  live,
  children,
}: {
  title: string;
  count?: number;
  action?: ReactNode;
  live?: boolean;
  children: ReactNode;
}) {
  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.14em] text-muted">
          {live && <LiveDot tone="accent" label="live" />}
          {title}
          {count != null && <span className="font-mono text-xs text-muted">({count})</span>}
        </h2>
        {action}
      </div>
      {children}
    </section>
  );
}

export function Rail({ children }: { children: ReactNode }) {
  return (
    <aside className="flex min-w-0 flex-col gap-4 lg:w-80 lg:shrink-0">{children}</aside>
  );
}

/* --------------------------------------------------------------- pipeline */

export function Pipeline({
  steps,
  current,
  label = "Progress",
}: {
  steps: string[];
  /** Index of the step in progress. Steps before it are done. */
  current: number;
  label?: string;
}) {
  return (
    <div className="overflow-x-auto pb-1" role="list" aria-label={label} tabIndex={0}>
      <div className="flex min-w-max items-start">
        {steps.map((step, i) => {
          const state = i < current ? "done" : i === current ? "current" : "todo";
          return (
            <Fragment key={step}>
              <div className="flex w-24 flex-col gap-2" role="listitem" aria-current={state === "current" ? "step" : undefined}>
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    state === "done"
                      ? "bg-success"
                      : state === "current"
                        ? "bg-accent animate-live"
                        : "bg-surface-3"
                  }`}
                />
                <span
                  className={`text-[10px] uppercase leading-tight tracking-[0.14em] ${
                    state === "current" ? "text-text" : "text-muted"
                  }`}
                >
                  {step}
                </span>
              </div>
              {i < steps.length - 1 && (
                <div className="mx-1 mt-[3px] h-px w-6 shrink-0 bg-surface-3">
                  <div
                    className="h-full origin-left bg-success transition-transform duration-500 ease-out"
                    style={{ transform: i < current ? "scaleX(1)" : "scaleX(0)" }}
                  />
                </div>
              )}
            </Fragment>
          );
        })}
      </div>
    </div>
  );
}

/* ----------------------------------------------------------- progress card */

export function ProgressCard({
  title,
  status,
  progress,
  stage,
  meta,
  href,
  action,
}: {
  title: string;
  status: WorkStatus;
  progress: number;
  stage?: string;
  meta?: string;
  href?: string;
  action?: ReactNode;
}) {
  const body = (
    <div className="flex h-full flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <span className="min-w-0 truncate text-sm font-medium">{title}</span>
        <StatusBadge status={status} />
      </div>
      <Progress value={progress} label={`${title} progress`} />
      <div className="flex flex-wrap items-center justify-between gap-2 font-mono text-xs text-muted">
        <span>{stage ?? STATUS_META[status].label}</span>
        {meta && <span>{meta}</span>}
      </div>
      {action && <div className="mt-auto flex flex-wrap gap-2 pt-1">{action}</div>}
    </div>
  );
  return (
    <div className="rounded-lg bg-surface p-1.5 bezel">
      <div className="h-full rounded-[calc(2rem-0.375rem)] bg-surface-2 p-4">{body}</div>
    </div>
  );
}

/* --------------------------------------------------------------- work queue */

export type WorkItem = {
  id: string;
  title: string;
  subtitle?: string;
  status: WorkStatus;
  meta?: string;
  href?: string;
  action?: ReactNode;
};

export function WorkQueue({ items, empty }: { items: WorkItem[]; empty?: ReactNode }) {
  if (items.length === 0) {
    return <>{empty ?? <p className="text-sm text-muted">Nothing in the queue.</p>}</>;
  }
  return (
    <ul className="flex flex-col gap-1">
      {items.map((item) => {
        const row = (
          <div className="flex items-center gap-3 px-2 py-2">
            <StatusDot tone={STATUS_META[item.status].dot} label={STATUS_META[item.status].label} />
            <div className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium">{item.title}</span>
              {item.subtitle && <span className="block truncate text-xs text-muted">{item.subtitle}</span>}
            </div>
            {item.meta && <span className="shrink-0 font-mono text-xs text-muted">{item.meta}</span>}
            {item.action}
          </div>
        );
        return (
          <li key={item.id} className="rounded-[calc(2rem-0.375rem)] transition hover:bg-surface-2">
            {item.href ? (
              <Link href={item.href} className="block">
                {row}
              </Link>
            ) : (
              row
            )}
          </li>
        );
      })}
    </ul>
  );
}

/* ------------------------------------------------------------ activity feed */

export function ActivityFeed({
  items,
}: {
  items: { id: string; kind: string; detail?: string | null; created_at?: string | null }[];
}) {
  if (items.length === 0) return <p className="text-sm text-muted">No engine activity yet.</p>;
  return (
    <ul className="flex flex-col gap-1">
      {items.map((e) => (
        <li key={e.id} className="flex items-baseline gap-3 px-2 py-1.5">
          <span className="shrink-0 font-mono text-[11px] text-muted">
            {e.created_at ? new Date(e.created_at).toLocaleTimeString() : ""}
          </span>
          <span className="shrink-0 font-mono text-[11px] uppercase tracking-wide text-accent">{e.kind}</span>
          <span className="min-w-0 truncate text-xs text-muted" title={e.detail ?? ""}>
            {e.detail ?? "—"}
          </span>
        </li>
      ))}
    </ul>
  );
}

/* ------------------------------------------------------------------ metric */

export function Metric({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-[0.18em] text-muted">{label}</span>
      <span className="font-mono text-lg font-semibold tracking-tight">{value}</span>
      {hint && <span className="text-xs text-muted">{hint}</span>}
    </div>
  );
}

/* ------------------------------------------------------------- empty state */

export function WorkEmpty({ title, body, action }: { title: string; body?: string; action?: ReactNode }) {
  return (
    <div className="rounded-lg bg-surface p-1.5 bezel">
      <div className="flex w-full flex-col items-start gap-3 rounded-[calc(2rem-0.375rem)] bg-surface-2 px-6 py-10">
        <h3 className="text-base font-medium">{title}</h3>
        {body && <p className="max-w-md text-sm text-muted">{body}</p>}
        {action}
      </div>
    </div>
  );
}

/* --------------------------------------------------------------- live strip */

export function LiveStrip({ overview }: { overview: AdminOverview }) {
  const analyzing = overview.projects.find((p) => p.stage === "analyzing" || p.queued);
  const activeResearch = overview.research.active[0];
  const configured = overview.keys.integrations.filter((k) => k.configured);
  const healthy = configured.filter((k) => k.status === "connected").length;
  const cells: {
    label: string;
    value: ReactNode;
    hint?: string;
    href: string;
    live?: boolean;
    alert?: boolean;
  }[] = [
    {
      label: "Jobs running",
      value: overview.jobs.running,
      hint: overview.jobs.active[0]
        ? `${overview.jobs.active[0].kind} · ${overview.jobs.active[0].stage ?? "queued"}`
        : "queue clear",
      href: "/admin/jobs",
      live: overview.jobs.running > 0,
    },
    {
      label: "Research",
      value: overview.research.active.length,
      hint: activeResearch ? activeResearch.game_name : "idle",
      href: "/admin/games",
      live: overview.research.active.length > 0,
    },
    {
      label: "Project",
      value: analyzing ? analyzing.name : "—",
      hint: analyzing ? analyzing.stage.replace(/_/g, " ") : "none active",
      href: "/admin/projects",
      live: Boolean(analyzing),
    },
    {
      label: "API memory",
      value: overview.system ? `${Math.round(overview.system.memory_percent)}%` : "—",
      hint: overview.system ? `CPU ${Math.round(overview.system.cpu_percent)}%` : "bridge off",
      href: "/admin/models",
    },
    {
      label: "Source keys",
      value: `${healthy}/${configured.length}`,
      hint: overview.keys.failing.length
        ? `${overview.keys.failing.length} invalid`
        : overview.keys.unreachable.length
          ? `${overview.keys.unreachable.length} unreachable`
          : "healthy",
      href: "/admin/setup",
      alert: overview.keys.failing.length > 0 || overview.keys.unreachable.length > 0,
    },
    {
      label: "Clips today",
      value: overview.clips_today,
      hint: `${overview.results.total_views.toLocaleString()} views total`,
      href: "/clips",
    },
  ];
  return (
    <div className="overflow-x-auto rounded-lg bg-surface p-1.5 bezel">
      <div className="grid grid-cols-2 divide-x divide-border sm:grid-cols-3 lg:grid-cols-6">
        {cells.map((cell) => (
          <Link
            key={cell.label}
            href={cell.href}
            className="flex min-w-0 flex-col gap-1 px-4 py-3 transition hover:bg-surface-2"
          >
            <span className="flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-muted">
              {cell.live && <LiveDot tone="accent" label="running" />}
              {cell.alert && <LiveDot tone="danger" label="attention" />}
              {cell.label}
            </span>
            <span className="truncate font-mono text-lg font-semibold tracking-tight">
              {cell.value}
            </span>
            {cell.hint && <span className="truncate text-xs text-muted">{cell.hint}</span>}
          </Link>
        ))}
      </div>
    </div>
  );
}

/* --------------------------------------------------------------- filter bar */

export function FilterBar({ children, aside }: { children: ReactNode; aside?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg bg-surface p-1.5 bezel">
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">{children}</div>
      {aside && <div className="ml-auto flex flex-wrap items-center gap-2">{aside}</div>}
    </div>
  );
}

/* ---------------------------------------------------------------- data table */

export type Column<T> = {
  key: string;
  label: string;
  sortable?: boolean;
  className?: string;
  render: (row: T) => ReactNode;
};

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  selected,
  onSelect,
  onSelectAll,
  sort,
  onSort,
  detail,
  expanded,
  onToggleExpand,
  empty,
}: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  selected?: Set<string>;
  onSelect?: (key: string) => void;
  onSelectAll?: () => void;
  sort?: { key: string; dir: "asc" | "desc" };
  onSort?: (key: string) => void;
  detail?: (row: T) => ReactNode;
  expanded?: Set<string>;
  onToggleExpand?: (key: string) => void;
  empty?: ReactNode;
}) {
  const allSelected = Boolean(selected && rows.length > 0 && selected.size === rows.length);
  const extra = (onSelect ? 1 : 0) + (detail ? 1 : 0);
  return (
    <div className="overflow-x-auto rounded-lg bg-surface p-1.5 bezel">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-border">
            {detail && <th scope="col" className="w-10 px-4 py-3" />}
            {onSelect && (
              <th scope="col" className="w-10 px-4 py-3">
                <input
                  type="checkbox"
                  aria-label="Select all"
                  checked={allSelected}
                  onChange={onSelectAll}
                  className="h-4 w-4 accent-[var(--accent)]"
                />
              </th>
            )}
            {columns.map((c) => (
              <th
                key={c.key}
                scope="col"
                className={`px-4 py-3 text-[10px] uppercase tracking-[0.18em] text-muted ${
                  c.sortable && onSort ? "cursor-pointer select-none" : ""
                }`}
                onClick={c.sortable && onSort ? () => onSort(c.key) : undefined}
              >
                {c.label}
                {c.sortable && sort?.key === c.key && (
                  <span className="ml-1 font-mono text-accent">{sort.dir === "asc" ? "↑" : "↓"}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={columns.length + extra} className="px-4 py-10 text-center text-sm text-muted">
                {empty ?? "Nothing here yet."}
              </td>
            </tr>
          )}
          {rows.map((row) => {
            const key = rowKey(row);
            const checked = selected?.has(key) ?? false;
            const open = expanded?.has(key) ?? false;
            return (
              <Fragment key={key}>
                <tr className={`border-b border-border last:border-0 ${checked ? "bg-accent-soft/40" : ""}`}>
                  {detail && (
                    <td className="px-4 py-3 align-middle">
                      <button
                        type="button"
                        aria-label={`Expand ${key}`}
                        aria-expanded={open}
                        onClick={() => onToggleExpand?.(key)}
                        className="rounded-full p-1 font-mono text-xs text-muted transition hover:bg-surface-2 hover:text-text"
                      >
                        {open ? "▾" : "▸"}
                      </button>
                    </td>
                  )}
                  {onSelect && (
                    <td className="px-4 py-3 align-middle">
                      <input
                        type="checkbox"
                        aria-label={`Select ${key}`}
                        checked={checked}
                        onChange={() => onSelect(key)}
                        className="h-4 w-4 accent-[var(--accent)]"
                      />
                    </td>
                  )}
                  {columns.map((c) => (
                    <td key={c.key} className={`px-4 py-3 align-middle ${c.className ?? ""}`}>
                      {c.render(row)}
                    </td>
                  ))}
                </tr>
                {detail && open && (
                  <tr className="border-b border-border last:border-0 bg-surface-2/50">
                    <td colSpan={columns.length + extra} className="px-6 py-4">
                      {detail(row)}
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
