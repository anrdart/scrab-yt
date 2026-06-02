import { type ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`bg-[var(--surface)] rounded-lg border border-[var(--border-strong)] shadow-[var(--shadow-soft)] ${className}`}>
      {children}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div className={`h-4 rounded bg-[var(--surface-muted)] animate-pulse ${className}`} />
  );
}
