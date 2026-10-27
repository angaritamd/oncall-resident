import type { ReactNode } from "react";
import type { Reason } from "@/lib/api";

export function ReasonChip({ r }: { r: Reason }) {
  const tone =
    r.kind === "critical"
      ? "border-critical/60 bg-critical/10 text-critical"
      : r.kind === "unknown"
        ? "border-review/60 bg-review/10 text-review"
        : "border-line bg-surface-2 text-fg";
  return (
    <span className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[13px] leading-5 ${tone}`}>
      <span className="font-medium">{r.label}</span>
      <span aria-hidden className="opacity-60">·</span>
      <span className="opacity-90">{r.source}</span>
    </span>
  );
}

export function CaseId({ id }: { id: string }) {
  return <span className="font-mono text-[13px] tracking-tight text-muted">{id}</span>;
}

export function Card({ children, label, tone }: { children: ReactNode; label?: string; tone?: "critical" }) {
  return (
    <section
      aria-label={label}
      className={`rounded-xl border bg-surface p-3.5 ${tone === "critical" ? "border-critical/50" : "border-line"}`}
    >
      {children}
    </section>
  );
}

export function Button({
  children,
  onClick,
  variant = "secondary",
  ...rest
}: { children: ReactNode; onClick?: () => void; variant?: "primary" | "secondary" | "ghost" } & Omit<
  React.ButtonHTMLAttributes<HTMLButtonElement>,
  "onClick"
>) {
  const styles = {
    primary: "bg-action text-on-action font-semibold hover:bg-action/90",
    secondary: "border border-line bg-surface-2 text-fg hover:border-muted/50",
    ghost: "text-action hover:bg-surface-2",
  }[variant];
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-3.5 text-[15px] transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${styles}`}
      {...rest}
    >
      {children}
    </button>
  );
}

export function Monogram({ size = 36 }: { size?: number }) {
  return (
    <span
      aria-hidden
      style={{ width: size, height: size }}
      className="inline-flex shrink-0 items-center justify-center rounded-[10px] border border-line bg-surface text-[17px] font-semibold text-fg"
    >
      R
    </span>
  );
}

export function ErrorNote({ text, retryLabel, onRetry }: { text: string; retryLabel: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-wrap items-center gap-3 rounded-xl border border-review/50 bg-review/10 p-3 text-[15px] text-fg">
      <span className="min-w-0 flex-1">{text}</span>
      {onRetry && (
        <Button onClick={onRetry} variant="secondary">
          {retryLabel}
        </Button>
      )}
    </div>
  );
}
