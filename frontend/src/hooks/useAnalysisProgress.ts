import { useState, useEffect, useCallback } from "react";
import { apiUrl, getAnalysis, type AnalysisDetail } from "../lib/api";

export function useAnalysisProgress(id: string) {
  const [analysis, setAnalysis] = useState<AnalysisDetail | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await getAnalysis(id);
      setAnalysis(data);
      setLoading(false);
      return data;
    } catch {
      setLoading(false);
      return null;
    }
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    let eventSource: EventSource | null = null;

    const connectSSE = () => {
      if (cancelled) return;
      eventSource?.close();
      eventSource = new EventSource(apiUrl(`/analyses/${id}/stream`));
      eventSource.addEventListener("progress", (e) => {
        if (cancelled) return;
        try {
          const d = JSON.parse(e.data);
          setAnalysis((prev) => prev ? { ...prev, progress: d.progress, progress_message: d.progress_message, status: d.status } : prev);
        } catch {
          // Ignore malformed SSE payloads and wait for the next event.
        }
      });
      eventSource.addEventListener("done", () => { eventSource?.close(); eventSource = null; refresh(); });
      eventSource.addEventListener("error", () => { eventSource?.close(); eventSource = null; if (!cancelled) setTimeout(connectSSE, 5000); });
    };

    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh().then((data) => {
      if (!cancelled && data?.status === "running") connectSSE();
    });

    return () => {
      cancelled = true;
      eventSource?.close();
    };
  }, [id, refresh]);

  return { analysis, loading, refresh };
}
