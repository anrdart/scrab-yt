import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "../components/Card";
import { createAnalysis } from "../lib/api";

export function NewAnalysis() {
  const navigate = useNavigate();
  const [url, setUrl] = useState("");
  const [threshold, setThreshold] = useState(75);
  const [stemming, setStemming] = useState(false);
  const [excludeSeries, setExcludeSeries] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    setSubmitting(true);
    try {
      const r = await createAnalysis({ channel_url: url.trim(), threshold: threshold / 100, use_stemming: stemming, exclude_series: excludeSeries });
      navigate(`/analyses/${r.id}`);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Gagal memulai analisis");
    } finally {
      setSubmitting(false);
    }
  };

  const pctLabel = threshold <= 55 ? "Loose" : threshold <= 70 ? "Normal" : threshold <= 85 ? "Strict" : "Very Strict";
  const pctColor = threshold <= 55 ? "text-[var(--warning)]" : threshold <= 70 ? "text-[var(--text)]" : threshold <= 85 ? "text-[var(--success)]" : "text-[var(--danger)]";

  return (
    <div className="page-frame max-w-2xl space-y-6">
      <div className="animate-fade-up">
        <p className="page-kicker">analysis setup</p>
        <h1 className="section-title mt-2 text-[var(--text)]">New Scan</h1>
        <p className="mt-2 text-sm text-[var(--text-secondary)]">Masukkan URL channel YouTube untuk deteksi duplikat konten</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 animate-fade-up stagger-1">
        <Card className="p-5">
          <label className="mb-2 block text-sm font-black text-[var(--text)]">Channel URL</label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.youtube.com/@NamaChannel/videos"
            required
            className="input-control h-12 w-full rounded-md px-4 text-sm placeholder:text-[var(--text-soft)]"
          />
          <p className="mt-2 break-all text-xs text-[var(--text-secondary)]">
            Example: https://www.youtube.com/@Gerakanwakafsumur/videos
          </p>
        </Card>

        <Card className="p-5 space-y-5 animate-fade-up stagger-2">
          <div>
            <div className="mb-4 flex items-baseline justify-between gap-4">
              <label className="text-sm font-black text-[var(--text)]">Similarity Threshold</label>
              <div className="flex items-baseline gap-2">
                <span className={`text-xl font-black tabular-nums ${pctColor}`}>{(threshold / 100).toFixed(2)}</span>
                <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                  threshold <= 55 ? "bg-[var(--warning-light)] text-[var(--warning)]" :
                  threshold <= 70 ? "bg-[var(--surface-muted)] text-[var(--text)]" :
                  threshold <= 85 ? "bg-[var(--success-light)] text-[var(--success)]" :
                  "bg-[var(--danger-light)] text-[var(--danger)]"
                }`}>
                  {pctLabel}
                </span>
              </div>
            </div>
            <input
              type="range"
              min={40} max={95} step={5}
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="range-control h-2 w-full cursor-pointer appearance-none rounded-full bg-[var(--surface-muted)]"
            />
            <div className="mt-2 flex justify-between gap-4">
              <span className="text-[11px] text-[var(--text-secondary)]">0.40 — more candidates</span>
              <span className="text-[11px] text-[var(--text-secondary)]">0.95 — near-identical</span>
            </div>
          </div>

          <hr className="border-[var(--border-strong)]" />

          <Toggle checked={excludeSeries} onChange={setExcludeSeries} label="Exclude video series" description="Skip episode series (Day-1, Day-2, etc)" />
          <Toggle checked={stemming} onChange={setStemming} label="Indonesian stemming" description="More accurate, slower processing" />
        </Card>

        <button
          type="submit"
          disabled={submitting}
          className="action-primary flex h-12 w-full items-center justify-center gap-2 rounded-md text-sm font-black disabled:pointer-events-none disabled:opacity-50 animate-fade-up stagger-3"
        >
          {submitting ? (
            <>
              <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
              Starting...
            </>
          ) : "Start Scan"}
        </button>
      </form>
    </div>
  );
}

function Toggle({ checked, onChange, label, description }: {
  checked: boolean; onChange: (v: boolean) => void; label: string; description: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-md border border-[var(--border)] bg-[#fffaf0] p-3">
      <div>
        <p className="text-sm font-bold text-[var(--text)]">{label}</p>
        <p className="mt-0.5 text-xs text-[var(--text-secondary)]">{description}</p>
      </div>
      <button
        type="button"
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border border-[var(--border-strong)] transition-colors duration-200 ${
          checked ? "bg-[var(--primary)]" : "bg-[var(--surface-muted)]"
        }`}
      >
        <span className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-200 ${checked ? "translate-x-5" : "translate-x-0"}`} />
      </button>
    </div>
  );
}
