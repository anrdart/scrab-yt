import { type ReactNode } from "react";

interface BadgeProps { children: ReactNode; variant?: "default" | "success" | "danger" | "muted" | "warning"; dot?: boolean }

export function Badge({ children, variant = "default", dot = false }: BadgeProps) {
  const colors: Record<string, string> = {
    default: "bg-[var(--surface-muted)] text-[var(--text-secondary)] border-[var(--border-strong)]",
    success: "bg-[var(--success-light)] text-[var(--success)] border-[#b4ddcc]",
    danger: "bg-[var(--danger-light)] text-[var(--danger)] border-[#f1b9bd]",
    muted: "bg-[#f8f3ea] text-[var(--text-secondary)] border-[var(--border)]",
    warning: "bg-[var(--warning-light)] text-[var(--warning)] border-[#ead195]",
  };

  const dotColors: Record<string, string> = {
    default: "bg-[var(--text-soft)]",
    success: "bg-[var(--success)]",
    danger: "bg-[var(--danger)]",
    muted: "bg-[var(--text-soft)]",
    warning: "bg-[var(--warning)]",
  };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-[11px] font-bold tracking-wide uppercase ${colors[variant]}`}>
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${dotColors[variant]} ${variant === "muted" ? "animate-pulse" : ""}`} />}
      {children}
    </span>
  );
}
