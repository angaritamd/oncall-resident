import type { ButtonHTMLAttributes, ReactNode } from "react";
import type { Reason } from "@/lib/api";

type Tone = "light" | "dark";

const DOT: Record<string, string> = { critical: "bg-crit", urgent: "bg-urg", unknown: "bg-urg" };

/** Pill chip. Critical always carries dot + text so it never relies on color alone. */
export function ReasonChip({ r, tone = "light" }: { r: Reason; tone?: Tone }) {
  const crit = r.kind === "critical";
  const style = crit
    ? tone === "dark"
      ? "bg-crit-dk text-crit-dkt"
      : "bg-crit-bg text-crit-text"
    : tone === "dark"
      ? "bg-ink-2 text-ink-text"
      : "bg-line-2 text-ink";
  return (
    <span className={`inline-flex h-7 items-center gap-1.5 whitespace-nowrap rounded-pill px-2.5 text-[12px] font-medium ${style}`}>
      <span aria-hidden className={`size-1.5 rounded-full ${DOT[r.kind] ?? "bg-neutral"}`} />
      {r.label} · {r.source.toLowerCase()}
    </span>
  );
}

export function StudyId({ id, tone = "light" }: { id: string; tone?: Tone }) {
  return <span className={`font-mono text-[12.5px] font-medium ${tone === "dark" ? "text-muted-d" : "text-muted"}`}>{id}</span>;
}

export function SectionLabel({ children, tone = "light", as: Tag = "h2" }: { children: ReactNode; tone?: Tone; as?: "h2" | "h3" | "p" }) {
  return <Tag className={`label ${tone === "dark" ? "text-muted-d" : "text-muted"}`}>{children}</Tag>;
}

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "dark-outline" | "light-outline" | "pill" };

export function Btn({ variant = "light-outline", className = "", type = "button", ...rest }: BtnProps) {
  const v = {
    primary: "h-[46px] rounded-btn bg-blue px-4 text-[15px] font-medium text-white hover:bg-blue-text",
    "dark-outline": "h-[46px] rounded-btn border border-ink-line px-4 text-[15px] font-medium text-ink-text hover:bg-ink-2",
    "light-outline": "h-[46px] rounded-btn border border-line bg-surface px-4 text-[15px] font-medium text-ink hover:border-muted",
    pill: "min-h-11 rounded-pill border border-line bg-surface px-4 text-[14px] font-medium text-ink hover:border-muted",
  }[variant];
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-2 transition-colors disabled:cursor-not-allowed ${v} ${className}`}
      {...rest}
    />
  );
}

/** A control for something that does not exist yet: real, focusable-free button, clearly labelled. */
export function SoonPill({ label, soon }: { label: string; soon: string }) {
  return (
    <button
      type="button"
      disabled
      aria-label={`${label} (${soon})`}
      className="inline-flex min-h-11 cursor-not-allowed items-center gap-2 rounded-pill border border-dashed border-line px-4 text-[14px] text-muted"
    >
      {label}
      <span className="text-[11px] font-medium uppercase tracking-[0.08em]">· {soon}</span>
    </button>
  );
}

export function Monogram({ size = 36 }: { size?: number }) {
  return (
    <span
      aria-hidden
      style={{ width: size, height: size, fontSize: size * 0.45 }}
      className="inline-flex shrink-0 items-center justify-center rounded-full bg-ink font-semibold text-ink-text"
    >
      R
    </span>
  );
}

export function ErrorNote({ text, retryLabel, onRetry }: { text: string; retryLabel: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-wrap items-center gap-3 rounded-card-sm bg-surface p-4 text-[15px]">
      <span aria-hidden className="size-2 shrink-0 rounded-full bg-urg" />
      <span className="min-w-0 flex-1">{text}</span>
      {onRetry && (
        <Btn variant="light-outline" onClick={onRetry}>
          {retryLabel}
        </Btn>
      )}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden className={`animate-pulse rounded-card bg-line-2 ${className}`} />;
}
