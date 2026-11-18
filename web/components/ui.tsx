"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";
import { forwardRef } from "react";

/* ------------------------------------------------------------------ button */

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
};

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  ...props
}: ButtonProps) {
  const sizes = {
    sm: "px-4 py-2 text-sm",
    md: "px-5 py-2.5 text-sm",
    lg: "px-7 py-4 text-base",
  }[size];
  const variants = {
    primary: "bg-accent text-accent-contrast hover:opacity-90",
    outline: "ring-surface bg-surface hover:bg-surface-2 text-text",
    ghost: "bg-transparent hover:bg-surface-2 text-muted hover:text-text",
    danger: "bg-danger/10 text-danger hover:bg-danger/15",
  }[variant];
  return (
    <button
      className={`inline-flex items-center justify-center gap-3 rounded-full font-medium transition duration-300 ease-out active:scale-[0.98] disabled:opacity-45 disabled:pointer-events-none ${sizes} ${variants} ${className}`}
      {...props}
    />
  );
}

/* ------------------------------------------------------------------- input */

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className = "", ...props }, ref) {
    return (
      <input
        ref={ref}
        className={`w-full rounded-xl bg-surface px-4 py-3 text-sm text-text ring-surface outline-none transition duration-300 ease-out placeholder:text-muted focus:bg-surface-2 ${className}`}
        {...props}
      />
    );
  },
);

export function Textarea({ className = "", ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={`w-full rounded-xl bg-surface px-4 py-3 text-sm text-text ring-surface outline-none transition duration-300 ease-out placeholder:text-muted focus:bg-surface-2 ${className}`}
      {...props}
    />
  );
}

export function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <label className="flex flex-col gap-2">
      <span className="text-xs uppercase tracking-[0.2em] text-muted">{label}</span>
      {children}
      {error ? (
        <span className="text-xs text-danger" role="alert">
          {error}
        </span>
      ) : hint ? (
        <span className="text-xs text-muted">{hint}</span>
      ) : null}
    </label>
  );
}

/* -------------------------------------------------------------------- card */

export function Card({
  children,
  className = "",
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "article" | "section" | "li";
}) {
  return (
    <div className={`rounded-lg bg-surface p-1.5 ring-surface ${className}`}>
      <Tag className="h-full rounded-[calc(2rem-0.375rem)] bg-surface-2 p-5">{children}</Tag>
    </div>
  );
}

/* ------------------------------------------------------------------- badge */

export function Badge({
  children,
  tone = "muted",
  className = "",
  ...props
}: {
  children: ReactNode;
  tone?: "muted" | "accent" | "success" | "danger";
  className?: string;
} & HTMLAttributes<HTMLSpanElement>) {
  const tones = {
    muted: "bg-surface-2 text-muted",
    accent: "bg-accent-soft text-accent",
    success: "bg-success/10 text-success",
    danger: "bg-danger/10 text-danger",
  }[tone];
  return (
    <span
      className={`inline-flex items-center gap-2 self-start rounded-full px-3 py-1 text-[10px] font-medium uppercase tracking-[0.2em] ${tones} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <span className="w-fit rounded-full bg-surface-2 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-muted ring-surface">
      {children}
    </span>
  );
}

/* -------------------------------------------------------------------- tabs */

export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: { id: string; label: string }[];
  active: string;
  onChange: (id: string) => void;
}) {
  return (
    <div role="tablist" className="inline-flex gap-1 rounded-full bg-surface-2 p-1 ring-surface">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={active === tab.id}
          onClick={() => onChange(tab.id)}
          className={`rounded-full px-4 py-2 text-sm transition duration-300 ease-out ${
            active === tab.id ? "bg-surface text-text shadow-ambient" : "text-muted hover:text-text"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ dialog */

export function Dialog({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const previousFocus = useRef<Element | null>(null);

  useEffect(() => {
    if (!open) return;
    previousFocus.current = document.activeElement;
    const panel = panelRef.current;
    const focusables = panel?.querySelector<HTMLElement>(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    );
    (focusables ?? panel)?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== "Tab" || !panel) return;
      const items = Array.from(
        panel.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])',
        ),
      );
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      if (previousFocus.current instanceof HTMLElement) previousFocus.current.focus();
    };
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-4 sm:items-center"
      onClick={onClose}
    >
      <div
        ref={panelRef}
        tabIndex={-1}
        className="w-full max-w-md rounded-lg bg-surface p-1.5 ring-surface outline-none"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="rounded-[calc(2rem-0.375rem)] bg-surface-2 p-6">
          <h2 id={titleId} className="mb-4 text-lg font-semibold">
            {title}
          </h2>
          {children}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------- toast */

type Toast = { id: number; message: string; tone: "info" | "success" | "danger" };
const ToastContext = createContext<(message: string, tone?: Toast["tone"]) => void>(() => {});

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((message: string, tone: Toast["tone"] = "info") => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message, tone }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3500);
  }, []);
  const value = useMemo(() => push, [push]);
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-4 left-1/2 z-50 flex w-full max-w-sm -translate-x-1/2 flex-col gap-2 px-4">
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className="rounded-xl bg-surface px-4 py-3 text-sm text-text shadow-ambient ring-surface"
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/* ------------------------------------------------------------------- table */

export function Table({
  head,
  caption,
  children,
}: {
  head: ReactNode[];
  caption?: string;
  children: ReactNode;
}) {
  return (
    <div className="overflow-x-auto rounded-lg bg-surface p-1.5 ring-surface" tabIndex={0}>
      <table className="w-full text-left text-sm">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr className="border-b border-border">
            {head.map((h, i) => (
              <th
                key={i}
                scope="col"
                className="px-4 py-3 text-xs uppercase tracking-[0.2em] text-muted"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export function Tr({ children }: { children: ReactNode }) {
  return <tr className="border-b border-border last:border-0">{children}</tr>;
}

export function Td({
  children,
  className = "",
  colSpan,
  title,
}: {
  children: ReactNode;
  className?: string;
  colSpan?: number;
  title?: string;
}) {
  return (
    <td colSpan={colSpan} title={title} className={`px-4 py-3 align-middle ${className}`}>
      {children}
    </td>
  );
}

/* -------------------------------------------------------------- empty/state */

export function EmptyState({
  title,
  body,
  action,
  icon = "◌",
}: {
  title: string;
  body?: string;
  action?: ReactNode;
  icon?: string;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg bg-surface p-1.5 ring-surface">
      <div className="flex w-full flex-col items-center gap-3 rounded-[calc(2rem-0.375rem)] bg-surface-2 px-6 py-16 text-center">
        <span aria-hidden className="text-2xl text-muted">
          {icon}
        </span>
        <h3 className="text-base font-medium">{title}</h3>
        {body && <p className="max-w-sm text-sm text-muted">{body}</p>}
        {action}
      </div>
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-surface-2 ${className}`} aria-hidden />;
}

export function Select({
  className = "",
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={`w-full appearance-none rounded-xl bg-surface px-4 py-3 text-sm text-text ring-surface outline-none transition duration-300 ease-out focus:bg-surface-2 ${className}`}
      {...props}
    >
      {children}
    </select>
  );
}

export function Progress({
  value,
  className = "",
  label = "Progress",
}: {
  value: number;
  className?: string;
  label?: string;
}) {
  return (
    <div
      className={`h-1.5 w-full overflow-hidden rounded-full bg-surface-2 ${className}`}
      role="progressbar"
      aria-label={label}
      aria-valuenow={Math.round(value)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className="h-full rounded-full bg-accent transition-[width] duration-500 ease-out"
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
}

export function Notice({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "warn" }) {
  const styles =
    tone === "warn"
      ? "bg-danger/10 text-danger ring-danger/20"
      : "bg-accent-soft text-accent ring-accent/20";
  return (
    <p className={`rounded-xl px-4 py-3 text-xs leading-relaxed ring-1 ${styles}`} role="status">
      {children}
    </p>
  );
}

export function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-[0.2em] text-muted">{label}</span>
      <span className="text-2xl font-semibold tracking-tight">{value}</span>
      {hint && <span className="text-xs text-muted">{hint}</span>}
    </div>
  );
}

export function PageState({
  loading,
  error,
  empty,
  emptyTitle = "Nothing here yet",
  emptyBody = "This will fill up as you go.",
  emptyAction,
  children,
}: {
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
  emptyTitle?: string;
  emptyBody?: string;
  emptyAction?: ReactNode;
  children?: ReactNode;
}) {
  if (loading) {
    return (
      <div
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        aria-busy="true"
        role="status"
        aria-label="Loading"
      >
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-48" />
        ))}
      </div>
    );
  }
  if (error) {
    return (
      <div role="alert">
        <EmptyState title="Something went wrong" body={error} icon="!" />
      </div>
    );
  }
  if (empty) {
    return <EmptyState title={emptyTitle} body={emptyBody} action={emptyAction} />;
  }
  return <>{children}</>;
}

export function StatusDot({
  tone = "muted",
  label,
  className = "",
}: {
  tone?: "muted" | "accent" | "success" | "danger";
  label?: string;
  className?: string;
}) {
  const tones = {
    muted: "bg-muted",
    accent: "bg-accent",
    success: "bg-success",
    danger: "bg-danger",
  }[tone];
  return (
    <span
      className={`inline-block h-1.5 w-1.5 rounded-full ${tones} ${className}`}
      role="status"
      aria-label={label ?? tone}
      title={label}
    />
  );
}
