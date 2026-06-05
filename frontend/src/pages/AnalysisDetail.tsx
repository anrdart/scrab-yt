import { Fragment, useEffect, useState, useCallback } from "react";
import { Link, useParams } from "react-router-dom";
import { Card } from "../components/Card";
import { Badge } from "../components/Badge";
import { apiUrl, cancelAnalysis, getClusters, getTranscripts, uploadMetadata } from "../lib/api";
import { useAnalysisProgress } from "../hooks/useAnalysisProgress";
import type { ClusterDetail, TranscriptPreview } from "../lib/api";

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; variant: "success" | "danger" | "warning" | "default" }> = {
    completed: { label: "Selesai", variant: "success" },
    running: { label: "Berjalan", variant: "warning" },
    failed: { label: "Gagal", variant: "danger" },
    cancelled: { label: "Dibatalkan", variant: "default" },
    pending: { label: "Antrian", variant: "default" },
  };
  const cfg = map[status] ?? { label: status, variant: "default" as const };
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>;
}

function ProgressRing({ progress, message }: { progress: number; message: string }) {
  const r = 54;
  const c = 2 * Math.PI * r;
  const offset = c - (progress / 100) * c;

  const stages = [
    { min: 0, max: 25, label: "Download Subtitle" },
    { min: 25, max: 50, label: "Transkripsi Audio" },
    { min: 50, max: 60, label: "Parse & Preprocessing" },
    { min: 60, max: 90, label: "Analisis Kemiripan" },
    { min: 90, max: 100, label: "Buat Laporan" },
  ];

  return (
    <Card className="p-6 animate-fade-up">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:gap-8">
        <div className="relative w-32 h-32 shrink-0">
          <svg viewBox="0 0 120 120" className="-rotate-90 w-full h-full">
            <circle cx="60" cy="60" r={r} fill="none" stroke="var(--border)" strokeWidth="6" />
            <circle cx="60" cy="60" r={r} fill="none" stroke="var(--primary)" strokeWidth="6"
              strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round"
              style={{ transition: "stroke-dashoffset 0.7s ease-out" }} />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-3xl font-black tabular-nums text-[var(--primary)]">{progress}%</span>
          </div>
        </div>
        <div className="flex-1 min-w-0 space-y-3">
          <p className="truncate text-sm font-black text-[var(--text)]">{message}</p>
          <div className="space-y-2">
            {stages.map((s, i) => {
              const done = progress >= s.max;
              const active = progress >= s.min && progress < s.max;
              return (
                <div key={i} className={`flex items-center gap-2.5 text-xs transition-colors duration-200 ${
                  done ? "text-[var(--success)]" : active ? "text-[var(--primary)] font-bold" : "text-[var(--text-soft)]"
                }`}>
                  <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 transition-all ${
                    done ? "bg-[var(--success-light)] text-[var(--success)]" :
                    active ? "bg-[var(--primary)] text-white animate-pulse-ring" :
                    "bg-[var(--surface-muted)] text-[var(--text-soft)]"
                  }`}>
                    {done ? "✓" : active ? `${i + 1}` : ""}
                  </span>
                  <span>{s.label}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </Card>
  );
}

function SimBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[var(--surface-muted)]">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            pct >= 90 ? "bg-[var(--danger)]" : pct >= 75 ? "bg-amber-500" : "bg-[var(--primary)]"
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-10 text-right font-mono text-[11px] text-[var(--text-secondary)]">{pct}%</span>
    </div>
  );
}

export function AnalysisDetail() {
  const { id } = useParams<{ id: string }>();
  const analysisId = id!;
  const { analysis, loading, refresh } = useAnalysisProgress(analysisId);
  const [clusters, setClusters] = useState<ClusterDetail[]>([]);
  const [transcripts, setTranscripts] = useState<TranscriptPreview[]>([]);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [expandedVideo, setExpandedVideo] = useState<string | null>(null);
  const [tab, setTab] = useState<"clusters" | "transcripts">("clusters");

  const loadResults = useCallback(async () => {
    if (analysis?.status !== "completed") return;
    try {
      const [c, tr] = await Promise.all([getClusters(analysisId), getTranscripts(analysisId)]);
      setClusters(c); setTranscripts(tr);
    } catch {
      // Results can be unavailable for a moment right after completion.
    }
  }, [analysisId, analysis?.status]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadResults();
  }, [loadResults]);

  const handleCsvChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setCsvFile(file);
    try {
      await uploadMetadata(analysisId, file);
      await refresh();
      await loadResults();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Upload gagal");
    }
  };

  const handleCancel = async () => {
    if (!confirm("Batalkan analisis yang sedang berjalan?")) return;
    setCancelling(true);
    try {
      await cancelAnalysis(analysisId);
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Gagal membatalkan");
    } finally {
      setCancelling(false);
    }
  };

  if (loading) {
    return (
      <div className="page-frame flex h-[60vh] items-center justify-center animate-fade-up">
        <svg className="animate-spin w-8 h-8 text-[var(--primary)]" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="page-frame flex h-[60vh] items-center justify-center animate-fade-up">
        <div className="text-center space-y-4">
          <p className="mx-auto flex h-12 w-12 items-center justify-center rounded-md border border-[var(--border-strong)] bg-[var(--surface-muted)] text-2xl font-black text-[var(--primary)]">!</p>
          <p className="text-sm text-[var(--text-secondary)]">Analisis tidak ditemukan</p>
          <Link to="/" className="inline-flex rounded-md px-4 py-2 text-sm font-black action-secondary">Dasbor</Link>
        </div>
      </div>
    );
  }

  const isRunning = analysis.status === "running";
  const isCompleted = analysis.status === "completed";
  const isFailed = analysis.status === "failed";

  return (
    <div className="page-frame space-y-6">
      <div className="flex flex-col items-start justify-between gap-4 animate-fade-up md:flex-row">
        <div>
          <div className="flex items-center gap-2.5">
            <Link to="/" className="mr-1 rounded-md px-2 py-1 text-sm font-black text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-muted)] hover:text-[var(--text)]">Kembali</Link>
            <StatusBadge status={analysis.status} />
          </div>
          <p className="page-kicker mt-4">detail analisis</p>
          <h1 className="section-title mt-2 text-[var(--text)]">#{analysisId.slice(0, 6)}</h1>
          <p className="mt-2 max-w-md truncate text-xs text-[var(--text-secondary)]">{analysis.channel_url}</p>
        </div>
        {isCompleted && (
          <div className="flex gap-2 animate-fade-up stagger-2">
            <label className="action-secondary relative flex cursor-pointer items-center gap-1.5 rounded-md px-3 py-2 text-xs font-black">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" x2="12" y1="3" y2="15" /></svg>
              {csvFile?.name || "Upload CSV"}
              <input type="file" accept=".csv" onChange={handleCsvChange} className="absolute inset-0 opacity-0 cursor-pointer" />
            </label>
            <a href={apiUrl(`/analyses/${analysisId}/download`)} download className="action-primary flex items-center gap-1.5 rounded-md px-3 py-2 text-xs font-black">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" x2="12" y1="15" y2="3" /></svg>
              Excel
            </a>
          </div>
        )}
      </div>

      {isRunning && (
        <div className="space-y-3">
          <ProgressRing progress={analysis.progress} message={analysis.progress_message} />
          <button onClick={handleCancel} disabled={cancelling} className="flex items-center gap-1.5 rounded-md px-3 py-2 text-xs font-black text-[var(--danger)] border border-[var(--danger)] hover:bg-[var(--danger-light)] transition-colors disabled:opacity-50">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2" /><line x1="9" x2="15" y1="9" y2="15" /><line x1="15" x2="9" y1="9" y2="15" /></svg>
            {cancelling ? "Membatalkan..." : "Batalkan Analisis"}
          </button>
        </div>
      )}

      {isFailed && (
        <Card className="p-5 border-[#f1b9bd] animate-fade-up">
          <div className="flex items-start gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[var(--danger-light)] font-black text-[var(--danger)]">x</div>
            <div>
              <p className="text-sm font-black text-[var(--danger)]">Analisis gagal</p>
              <p className="mt-0.5 text-xs text-[var(--text-secondary)]">{analysis.progress_message}</p>
              <Link to="/analyses/new" className="mt-3 inline-flex rounded-md px-3 py-1.5 text-xs font-black action-secondary">Coba Lagi</Link>
            </div>
          </div>
        </Card>
      )}

      <div className="grid grid-cols-2 gap-3 animate-fade-up stagger-2 lg:grid-cols-4">
        <Card className="p-4 text-center transition-all hover:-translate-y-0.5 hover:shadow-[var(--shadow-hover)]">
          <p className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] font-black">Video</p>
          <p className="mt-1 text-2xl font-black tabular-nums">{analysis.total_videos.toLocaleString("id-ID")}</p>
        </Card>
        <Card className="p-4 text-center transition-all hover:-translate-y-0.5 hover:shadow-[var(--shadow-hover)]">
          <p className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] font-black">Cluster</p>
          <p className="mt-1 text-2xl font-black tabular-nums">{analysis.total_clusters}</p>
        </Card>
        <Card className="p-4 text-center transition-all hover:-translate-y-0.5 hover:shadow-[var(--shadow-hover)]">
          <p className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] font-black">Duplikat</p>
          <p className="mt-1 text-2xl font-black tabular-nums text-[var(--danger)]">{analysis.total_duplicates}</p>
        </Card>
        <Card className="p-4 text-center transition-all hover:-translate-y-0.5 hover:shadow-[var(--shadow-hover)]">
          <p className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] font-black">Ambang</p>
          <p className="mt-1 text-2xl font-black tabular-nums">{analysis.threshold?.toFixed(2)}</p>
        </Card>
      </div>

      {isCompleted && (
        <div className="animate-fade-up stagger-3">
          <div className="mb-4 flex w-fit gap-1 rounded-md border border-[var(--border-strong)] bg-[var(--surface-muted)] p-1">
            <button onClick={() => setTab("clusters")} className={`rounded px-4 py-1.5 text-xs font-black transition-all ${tab === "clusters" ? "bg-[var(--surface)] text-[var(--text)] shadow-sm" : "text-[var(--text-secondary)] hover:text-[var(--text)]"}`}>
              Cluster ({clusters.length})
            </button>
            <button onClick={() => setTab("transcripts")} className={`rounded px-4 py-1.5 text-xs font-black transition-all ${tab === "transcripts" ? "bg-[var(--surface)] text-[var(--text)] shadow-sm" : "text-[var(--text-secondary)] hover:text-[var(--text)]"}`}>
              Transkrip ({transcripts.length})
            </button>
          </div>

          {tab === "clusters" && (
            <div className="space-y-4">
              {clusters.length === 0 ? (
                <Card className="p-16 text-center">
                  <p className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-md border border-[#b4ddcc] bg-[var(--success-light)] text-2xl font-black text-[var(--success)]">✓</p>
                  <p className="text-sm font-black text-[var(--success)]">Tidak ada duplikat</p>
                  <p className="mt-1 text-xs text-[var(--text-secondary)]">
                    Semua {analysis.total_videos} video unik (ambang {analysis.threshold?.toFixed(2)})
                  </p>
                </Card>
              ) : clusters.map((cluster, ci) => (
                <Card key={cluster.group_id} className={`overflow-hidden animate-fade-up stagger-${Math.min(ci + 4, 9)}`}>
                  <div className="flex flex-col gap-3 border-b border-[var(--border-strong)] bg-[var(--surface-muted)] px-5 py-3 md:flex-row md:items-center md:justify-between">
                    <div className="flex items-center gap-2">
                      <span className="flex h-7 w-7 items-center justify-center rounded-md bg-[var(--surface)] text-[10px] font-black text-[var(--primary)]">{cluster.group_id}</span>
                      <span className="text-sm font-black text-[var(--text)]">Grup {cluster.group_id}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-[10px] font-black uppercase tracking-wider text-[var(--text-secondary)]">{cluster.cluster_size} video</span>
                      <SimBar value={cluster.avg_similarity} />
                    </div>
                  </div>
                  <div className="table-shell">
                    <table className="data-table w-full text-sm">
                      <thead>
                        <tr className="border-b border-[var(--border-strong)] text-[10px] font-black uppercase tracking-wider text-[var(--text-secondary)]">
                          <th className="px-5 py-2.5 text-left">Status</th>
                          <th className="px-4 py-2.5 text-left">Video</th>
                          <th className="px-4 py-2.5 text-right">Tayangan</th>
                          <th className="px-4 py-2.5 text-right">Kemiripan</th>
                        </tr>
                      </thead>
                      <tbody>
                        {cluster.videos.map((v) => (
                          <Fragment key={v.video_id}>
                            <tr className={`border-b border-[var(--border)] transition-colors ${
                              v.status === "PRIMARY" ? "" : "bg-[var(--danger-light)]"
                            }`}>
                              <td className="px-5 py-2.5 align-top">
                                <Badge variant={v.status === "PRIMARY" ? "success" : "danger"}>
                                  {v.status === "PRIMARY" ? "Utama" : "Duplikat"}
                                </Badge>
                              </td>
                              <td className="px-4 py-2.5">
                                <div className="flex items-center gap-3">
                                  <button type="button" onClick={() => setExpandedVideo(expandedVideo === v.video_id ? null : v.video_id)} className="relative shrink-0 group cursor-pointer rounded overflow-hidden">
                                    <img src={`https://img.youtube.com/vi/${v.video_id}/mqdefault.jpg`} alt={v.judul} className="w-24 h-[54px] object-cover" loading="lazy" />
                                    <span className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity">
                                      <svg width="20" height="20" viewBox="0 0 24 24" fill="white"><polygon points="5 3 19 12 5 21 5 3" /></svg>
                                    </span>
                                  </button>
                                  <div className="min-w-0">
                                    <p className="truncate max-w-[240px] text-sm font-bold text-[var(--text)]">
                                      {v.judul !== "N/A" ? v.judul : <span className="italic text-[var(--text-secondary)]">&mdash;</span>}
                                    </p>
                                    <a href={`https://www.youtube.com/watch?v=${v.video_id}`} target="_blank" rel="noopener noreferrer" className="mt-0.5 block font-mono text-[10px] text-[var(--primary)] hover:underline">{v.video_id}</a>
                                  </div>
                                </div>
                              </td>
                              <td className="px-4 py-2.5 text-right tabular-nums align-top">
                                {v.penayangan > 0 ? v.penayangan.toLocaleString("id-ID") : <span className="text-[var(--text-secondary)]">-</span>}
                              </td>
                              <td className="px-4 py-2.5 align-top">
                                <SimBar value={v.similarity_to_primary} />
                              </td>
                            </tr>
                            {expandedVideo === v.video_id && (
                              <tr>
                                <td colSpan={4} className="px-5 py-3 bg-[var(--surface-muted)]">
                                  <iframe width="480" height="270" src={`https://www.youtube.com/embed/${v.video_id}`} title={v.judul} allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen className="rounded-md" />
                                </td>
                              </tr>
                            )}
                          </Fragment>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              ))}
            </div>
          )}

          {tab === "transcripts" && (
            <Card className="overflow-hidden">
              <div className="table-shell">
                <table className="data-table w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--border-strong)] text-[10px] font-black uppercase tracking-wider text-[var(--text-secondary)]">
                      <th className="px-5 py-2.5 text-left">ID Video</th>
                      <th className="px-4 py-2.5 text-left">Pratinjau</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transcripts.map((tr) => (
                      <tr key={tr.video_id} className="border-b border-[var(--border)] transition-colors">
                        <td className="px-5 py-2.5 font-mono text-[11px] font-bold">
                          <a href={`https://www.youtube.com/watch?v=${tr.video_id}`} target="_blank" rel="noopener noreferrer" className="text-[var(--primary)] underline decoration-[var(--primary)]/30 hover:decoration-[var(--primary)]">{tr.video_id}</a>
                        </td>
                        <td className="max-w-[520px] px-4 py-2.5 text-xs leading-relaxed text-[var(--text-secondary)]">{tr.preview}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
