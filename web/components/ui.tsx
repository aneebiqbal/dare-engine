"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type TextareaHTMLAttributes,
} from "react";

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

export function Input({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`w-full rounded-xl bg-surface px-4 py-3 text-sm text-text ring-surface outline-none transition duration-300 ease-out placeholder:text-muted focus:bg-surface-2 ${className}`}
      {...props}
    />
  );
}

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
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-lg bg-surface p-1.5 ring-surface"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="rounded-[calc(2rem-0.375rem)] bg-surface-2 p-6">
          <h2 className="mb-4 text-lg font-semibold">{title}</h2>
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
  children,
}: {
  head: ReactNode[];
  children: ReactNode;
}) {
  return (
    <div className="overflow-x-auto rounded-lg bg-surface p-1.5 ring-surface">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-border">
            {head.map((h, i) => (
              <th key={i} className="px-4 py-3 text-xs uppercase tracking-[0.2em] text-muted">
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
}: {
  children: ReactNode;
  className?: string;
  colSpan?: number;
}) {
  return (
    <td colSpan={colSpan} className={`px-4 py-3 align-middle ${className}`}>
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

export function PageState({
  loading,
  error,
  empty,
  children,
}: {
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
  children: ReactNode;
}) {
  if (loading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-48" />
        ))}
      </div>
    );
  }
  if (error) {
    return (
      <EmptyState title="Something went wrong" body={error} icon="!" />
    );
  }
  if (empty) {
    return <EmptyState title="Nothing here yet" body="This will fill up as you go." />;
  }
  return <>{children}</>;
}
