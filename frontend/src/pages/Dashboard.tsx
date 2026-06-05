import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card, Skeleton } from "../components/Card";
import { Badge } from "../components/Badge";
import { listAnalyses, deleteAnalysis, cancelAnalysis } from "../lib/api";
import { useI18n } from "../lib/i18n";
import type { AnalysisSummary } from "../lib/api";

function StatusBadge({ status }: { status: string }) {
  const { t } = useI18n();
  const map: Record<string, { v: "success" | "muted" | "danger"; key: string; dot: boolean }> = {
    completed: { v: "success", key: "status.done", dot: false },
    running: { v: "muted", key: "status.running", dot: true },
    failed: { v: "danger", key: "status.failed", dot: false },
    cancelled: { v: "muted", key: "status.cancelled", dot: false },
    pending: { v: "muted", key: "status.pending", dot: false },
  };
  const c = map[status] ?? { v: "muted" as const, key: status, dot: false };
  return <Badge variant={c.v} dot={c.dot}>{t(c.key as any)}</Badge>;
}

function Stat({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="animate-fade-up">
      <Card className="p-5 transition-all duration-200 hover:shadow-[var(--shadow-hover)] hover:-translate-y-0.5">
        <p className="text-[11px] font-extrabold uppercase tracking-wider text-[var(--text-secondary)]">{label}</p>
        <p className={`mt-2 text-3xl font-black tabular-nums ${color || ""}`}>{value.toLocaleString("id-ID")}</p>
      </Card>
    </div>
  );
}

function channelName(url: string) {
  const m = url.match(/@([\w.-]+)/);
  return m ? `@${m[1]}` : url.replace(/^https?:\/\//, "").slice(0, 28);
}

function fmtDate(d: string | null) {
  if (!d) return "-";
  return new Date(d).toLocaleDateString("id-ID", { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function Dashboard() {
  const { t } = useI18n();
  const [data, setData] = useState<AnalysisSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const analyses = await listAnalyses();
        if (!cancelled) setData(analyses);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    const timer = window.setInterval(() => {
      load();
    }, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm(t("dashboard.confirmDelete"))) return;
    try {
      await deleteAnalysis(id);
      setData((p) => p.filter((a) => a.id !== id));
    } catch (err) {
      alert(err instanceof Error ? err.message : t("dashboard.deleteFailed"));
    }
  };

  const handleCancel = async (id: string) => {
    if (!confirm(t("dashboard.confirmCancel"))) return;
    try {
      await cancelAnalysis(id);
      setData((p) => p.map((a) => a.id === id ? { ...a, status: "cancelled" } : a));
    } catch (err) {
      alert(err instanceof Error ? err.message : t("dashboard.cancelFailed"));
    }
  };

  const totalV = data.reduce((s, a) => s + a.total_videos, 0);
  const totalC = data.reduce((s, a) => s + a.total_clusters, 0);
  const totalD = data.reduce((s, a) => s + a.total_duplicates, 0);

  return (
    <div className="page-frame space-y-8">
      <div className="flex items-end justify-between gap-4 animate-fade-up">
        <div>
          <p className="page-kicker">{t("dashboard.kicker")}</p>
          <h1 className="section-title mt-2 text-[var(--text)]">{t("dashboard.title")}</h1>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">{t("dashboard.subtitle")}</p>
        </div>
        <Link to="/analyses/new" className="action-primary rounded-md px-4 py-2.5 text-sm font-black">
          {t("nav.newScan")}
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="animate-fade-up stagger-1">
          <Stat label={t("dashboard.totalVideos")} value={totalV} />
        </div>
        <div className="animate-fade-up stagger-2">
          <Stat label={t("dashboard.clusters")} value={totalC} />
        </div>
        <div className="animate-fade-up stagger-3">
          <Stat label={t("dashboard.duplicates")} value={totalD} color="text-[var(--danger)]" />
        </div>
      </div>

      <Card className="animate-fade-up stagger-4 overflow-hidden">
        <div className="border-b border-[var(--border-strong)] bg-[var(--surface-muted)] px-5 py-4">
          <h2 className="text-sm font-black text-[var(--text)]">{t("dashboard.history")}</h2>
        </div>

        {loading ? (
          <div className="p-5 space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-4">
                <Skeleton className="w-36" />
                <Skeleton className="w-16" />
                <Skeleton className="w-10 ml-auto" />
                <Skeleton className="w-10" />
                <Skeleton className="w-10" />
                <Skeleton className="w-28" />
              </div>
            ))}
          </div>
        ) : data.length === 0 ? (
          <div className="py-20 text-center">
            <p className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-md border border-[var(--border-strong)] bg-[var(--surface-muted)] text-2xl font-black text-[var(--primary)]">0</p>
            <p className="text-sm font-bold text-[var(--text-secondary)]">{t("dashboard.noData")}</p>
            <Link to="/analyses/new" className="mt-5 inline-flex rounded-md px-4 py-2 text-sm font-black action-secondary">
              {t("dashboard.firstScan")}
            </Link>
          </div>
        ) : (
          <div className="table-shell">
            <table className="data-table w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-strong)] text-left text-[11px] font-black uppercase tracking-wider text-[var(--text-secondary)]">
                  <th className="px-5 py-3">{t("table.channel")}</th>
                  <th className="px-4 py-3">{t("table.status")}</th>
                  <th className="px-4 py-3 text-right">{t("table.videos")}</th>
                  <th className="px-4 py-3 text-right">{t("table.clusters")}</th>
                  <th className="px-4 py-3 text-right">{t("table.duplicates")}</th>
                  <th className="px-4 py-3">{t("table.date")}</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {data.map((a, i) => (
                  <tr key={a.id} className={`group border-b border-[var(--border)] transition-colors animate-fade-up stagger-${Math.min(i + 5, 9)}`}>
                    <td className="max-w-[220px] truncate px-5 py-3 font-bold">{channelName(a.channel_url)}</td>
                    <td className="px-4 py-3"><StatusBadge status={a.status} /></td>
                    <td className="px-4 py-3 text-right tabular-nums">{a.total_videos.toLocaleString("id-ID")}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{a.total_clusters}</td>
                    <td className="px-4 py-3 text-right font-bold tabular-nums text-[var(--danger)]">{a.total_duplicates}</td>
                    <td className="px-4 py-3 text-xs text-[var(--text-secondary)]">{fmtDate(a.created_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2 opacity-100 transition-opacity md:opacity-0 md:group-hover:opacity-100">
                        <Link to={`/analyses/${a.id}`} className="rounded-md px-2 py-1 text-xs font-black text-[var(--primary)] hover:bg-[var(--primary-light)]">{t("dashboard.view")}</Link>
                        {a.status === "running" ? (
                          <button onClick={() => handleCancel(a.id)} className="cursor-pointer rounded-md border-none bg-transparent px-2 py-1 text-xs font-black text-[var(--danger)] opacity-70 transition-opacity hover:bg-[var(--danger-light)] hover:opacity-100">{t("dashboard.cancel")}</button>
                        ) : (
                          <button onClick={() => handleDelete(a.id)} className="cursor-pointer rounded-md border-none bg-transparent px-2 py-1 text-xs font-black text-[var(--danger)] opacity-70 transition-opacity hover:bg-[var(--danger-light)] hover:opacity-100">{t("dashboard.delete")}</button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
